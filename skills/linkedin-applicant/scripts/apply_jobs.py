#!/usr/bin/env python3
"""
LinkedIn job applicant — applies to jobs via Easy Apply or flags for manual review.
"""

import argparse
import asyncio
import json
import logging
import random
import sys
from datetime import datetime
from pathlib import Path

import yaml
from playwright.async_api import async_playwright, Page, BrowserContext

# Add project root to path for vault import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from lib.vault import load_config_with_vault

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Import login from crawler
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "linkedin-job-crawler" / "scripts"))
from crawl_jobs import login_to_linkedin, random_delay


async def fill_easy_apply(page: Page, config: dict) -> bool:
    """Fill out a LinkedIn Easy Apply form. Returns True on success."""
    profile = config["user_profile"]
    resume_path = config["paths"]["resume_pdf"]

    max_steps = 10  # Safety: don't loop forever on multi-step forms

    for step in range(max_steps):
        logger.info("Easy Apply step %d", step + 1)
        await asyncio.sleep(random.uniform(1, 2))

        # Check for success
        success_el = await page.query_selector(".artdeco-inline-feedback--success, .jpac-modal-header")
        if success_el:
            text = await success_el.inner_text()
            if "application" in text.lower() and ("sent" in text.lower() or "submitted" in text.lower()):
                logger.info("Application submitted successfully!")
                return True

        # Fill contact fields if present
        for field_id, value in [
            ("input[name*='firstName'], input[id*='firstName']", profile.get("name", "").split()[0] if profile.get("name") else ""),
            ("input[name*='lastName'], input[id*='lastName']", profile.get("name", "").split()[-1] if profile.get("name") else ""),
            ("input[name*='email'], input[id*='email']", profile.get("email", "")),
            ("input[name*='phone'], input[id*='phoneNumber'], input[id*='phone']", profile.get("phone", "")),
        ]:
            try:
                el = await page.query_selector(field_id)
                if el:
                    current_val = await el.input_value()
                    if not current_val and value:
                        await el.fill(value)
                        logger.debug("Filled field: %s", field_id)
            except Exception:
                pass

        # Handle resume upload
        try:
            upload = await page.query_selector("input[type='file']")
            if upload:
                if Path(resume_path).exists():
                    await upload.set_input_files(resume_path)
                    logger.info("Uploaded resume")
                    await asyncio.sleep(1)
        except Exception as e:
            logger.debug("Resume upload: %s", e)

        # Handle sponsorship question
        try:
            sponsorship_labels = await page.query_selector_all("label, span.t-14")
            for label in sponsorship_labels:
                text = await label.inner_text()
                text_lower = text.lower()
                if "sponsor" in text_lower or "visa" in text_lower or "authorization" in text_lower:
                    # Look for the associated radio/select
                    parent = await label.evaluate_handle("el => el.closest('.jobs-easy-apply-form-section__grouping') || el.parentElement")
                    if parent:
                        yes_option = await parent.query_selector("input[value='Yes'], option[value='Yes']")
                        if yes_option:
                            await yes_option.click()
                            logger.info("Answered sponsorship question: Yes")
        except Exception as e:
            logger.debug("Sponsorship handling: %s", e)

        # Handle common select dropdowns
        try:
            selects = await page.query_selector_all("select")
            for select in selects:
                label_el = await select.evaluate_handle("el => el.closest('.fb-dash-form-element')?.querySelector('label') || el.previousElementSibling")
                if label_el:
                    try:
                        label_text = await label_el.inner_text()
                    except Exception:
                        label_text = ""
                    label_lower = label_text.lower()

                    if "experience" in label_lower or "years" in label_lower:
                        await select.select_option(index=2)  # Usually "2-5 years" or similar
                    elif "education" in label_lower or "degree" in label_lower:
                        await select.select_option(label="Master's Degree")
        except Exception as e:
            logger.debug("Dropdown handling: %s", e)

        # Click Next, Review, or Submit
        submitted = False
        for btn_text in ["Submit application", "Submit", "Review", "Next"]:
            try:
                btn = await page.query_selector(f"button:has-text('{btn_text}')")
                if btn and await btn.is_visible() and await btn.is_enabled():
                    await btn.click()
                    logger.info("Clicked: %s", btn_text)
                    await asyncio.sleep(random.uniform(1.5, 3))
                    if "submit" in btn_text.lower():
                        submitted = True
                    break
            except Exception:
                pass

        if submitted:
            # Check for confirmation
            await asyncio.sleep(2)
            return True

        # Check for dismiss/close (means we're done)
        dismiss = await page.query_selector("button[aria-label='Dismiss'], button:has-text('Done')")
        if dismiss and await dismiss.is_visible():
            await dismiss.click()
            return True

    logger.warning("Hit max steps without completing application")
    return False


async def apply_to_jobs(scored_jobs: list[dict], config_path: str) -> list[dict]:
    """Apply to scored jobs. Returns application results."""
    config = load_config_with_vault(config_path)

    app_config = config["application"]
    max_per_hour = app_config.get("max_applications_per_hour", 5)
    delay_range = app_config.get("delay_between_actions", [30, 60])
    top_n = app_config.get("top_n_per_run", 5)

    # Only process top N
    to_process = scored_jobs[:top_n]
    results = []
    applied_count = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        # Login
        if not await login_to_linkedin(page, context, config):
            logger.error("Failed to log into LinkedIn for applying")
            await browser.close()
            return results

        for scored in to_process:
            job = scored["job"]
            company = job.get("company", "Unknown")
            title = job.get("title", "Unknown")
            url = job.get("url", "")

            logger.info("Processing: %s at %s (score: %d)", title, company, scored["relevance_score"])

            # Check if big tech → flag
            if scored.get("is_big_tech", False):
                logger.info("BIG TECH — flagging for manual application: %s", company)
                results.append({
                    "job": job,
                    "status": "flagged_for_manual",
                    "score": scored["relevance_score"],
                    "reasoning": scored["reasoning"],
                    "notes": f"Big tech company: {company}. Apply manually.",
                    "timestamp": datetime.now().isoformat(),
                })
                continue

            # Check rate limit
            if applied_count >= max_per_hour:
                logger.info("Rate limit reached (%d/%d). Stopping.", applied_count, max_per_hour)
                break

            # Navigate to job
            try:
                await page.goto(url, wait_until="domcontentloaded")
                await random_delay(config["rate_limiting"]["page_load_delay"], "job-page")
            except Exception as e:
                logger.error("Failed to load job page: %s", e)
                results.append({
                    "job": job, "status": "error", "score": scored["relevance_score"],
                    "reasoning": scored["reasoning"], "notes": f"Page load error: {e}",
                    "timestamp": datetime.now().isoformat(),
                })
                continue

            # Check for Easy Apply
            easy_apply_btn = await page.query_selector(
                "button.jobs-apply-button:has-text('Easy Apply'), "
                "button:has-text('Easy Apply')"
            )

            if easy_apply_btn and await easy_apply_btn.is_visible():
                logger.info("Easy Apply available — applying...")
                await easy_apply_btn.click()
                await asyncio.sleep(random.uniform(1, 2))

                success = await fill_easy_apply(page, config)
                status = "applied" if success else "error"

                if success:
                    applied_count += 1
                    logger.info("✅ Applied to %s at %s (%d/%d)", title, company, applied_count, max_per_hour)
                else:
                    # Screenshot for debugging
                    ss_dir = Path("data/screenshots")
                    ss_dir.mkdir(parents=True, exist_ok=True)
                    ss_path = ss_dir / f"error_{job.get('job_id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await page.screenshot(path=str(ss_path))
                    logger.warning("❌ Failed to apply. Screenshot: %s", ss_path)

                results.append({
                    "job": job, "status": status, "score": scored["relevance_score"],
                    "reasoning": scored["reasoning"],
                    "notes": "Easy Apply" if success else "Easy Apply failed",
                    "timestamp": datetime.now().isoformat(),
                })
            else:
                # No Easy Apply — check if we have portal account patterns
                portal_config = config.get("portal_accounts", {})
                email_pattern = portal_config.get("email_pattern", "")

                if email_pattern and not scored.get("is_big_tech", False):
                    # Generate portal credentials for this company
                    from lib.vault import generate_portal_email, generate_portal_password
                    portal_email = generate_portal_email(email_pattern, company)
                    portal_password = generate_portal_password(
                        portal_config.get("password_pattern", ""), company
                    )
                    logger.info("External application — portal creds generated for %s (%s)", company, portal_email)
                    results.append({
                        "job": job, "status": "external_application_needed",
                        "score": scored["relevance_score"], "reasoning": scored["reasoning"],
                        "notes": f"External portal. Account: {portal_email}. Needs manual or automated portal apply.",
                        "portal_email": portal_email,
                        "portal_password": portal_password,
                        "timestamp": datetime.now().isoformat(),
                    })
                else:
                    logger.info("No Easy Apply — marking as external: %s at %s", title, company)
                    results.append({
                        "job": job, "status": "external_application_needed",
                        "score": scored["relevance_score"], "reasoning": scored["reasoning"],
                        "notes": "No Easy Apply option. External application required.",
                        "timestamp": datetime.now().isoformat(),
                    })

            # Delay between applications
            if applied_count < max_per_hour:
                await random_delay(delay_range, "between-applications")

        await browser.close()

    logger.info("Application round complete. Applied: %d, Flagged: %d, External: %d, Errors: %d",
                sum(1 for r in results if r["status"] == "applied"),
                sum(1 for r in results if r["status"] == "flagged_for_manual"),
                sum(1 for r in results if r["status"] == "external_application_needed"),
                sum(1 for r in results if r["status"] == "error"))

    return results


def main():
    parser = argparse.ArgumentParser(description="Apply to scored LinkedIn jobs")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--scored", required=True, help="Path to scored jobs JSON (or - for stdin)")
    args = parser.parse_args()

    if args.scored == "-":
        scored = json.load(sys.stdin)
    else:
        with open(args.scored) as f:
            scored = json.load(f)

    results = asyncio.run(apply_to_jobs(scored, args.config))
    json.dump(results, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
