#!/usr/bin/env python3
"""
LinkedIn job crawler using Playwright.
Searches for jobs matching configured roles/locations, extracts details,
and deduplicates against a local cache.
"""

import argparse
import asyncio
import json
import logging
import random
import sys
from pathlib import Path

import yaml
from playwright.async_api import async_playwright, Page, BrowserContext

# Add project root to path for vault import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from lib.vault import load_config_with_vault

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def random_delay(range_tuple: list[float], label: str = ""):
    """Sleep for a random duration within the given range."""
    delay = random.uniform(range_tuple[0], range_tuple[1])
    if label:
        logger.debug("Delay %.1fs (%s)", delay, label)
    await asyncio.sleep(delay)


async def human_type(page: Page, selector: str, text: str, delay_range: list[float]):
    """Type text with human-like delays between keystrokes."""
    await page.click(selector)
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(delay_range[0], delay_range[1]))


async def login_to_linkedin(page: Page, context: BrowserContext, config: dict) -> bool:
    """Log into LinkedIn, using saved cookies if available."""
    cookie_file = config["linkedin"]["cookie_file"]

    # Try loading saved cookies
    if Path(cookie_file).exists():
        try:
            with open(cookie_file) as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            await random_delay(config["rate_limiting"]["page_load_delay"], "post-cookie-load")

            if "/feed" in page.url:
                logger.info("Logged in via saved cookies")
                return True
            logger.info("Saved cookies expired, logging in fresh")
        except Exception as e:
            logger.warning("Cookie load failed: %s", e)

    # Fresh login
    try:
        login_method = config["linkedin"].get("login_method", "credentials")
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        await random_delay(config["rate_limiting"]["page_load_delay"], "login-page")

        if login_method == "google_oauth":
            logger.info("Logging in via Google OAuth")
            google_btn = await page.query_selector(
                "button[data-litms-control-urn*='google'], "
                "a[href*='google'], "
                "button:has-text('Sign in with Google'), "
                "a:has-text('Sign in with Google')"
            )
            if google_btn:
                await google_btn.click()
                await page.wait_for_load_state("domcontentloaded")
                await random_delay(config["rate_limiting"]["page_load_delay"], "google-oauth-page")

                google_creds = config["linkedin"].get("google_oauth", {})
                # Enter Google email
                email_input = await page.query_selector("input[type='email']")
                if email_input:
                    await human_type(page, "input[type='email']", google_creds.get("email", ""), config["rate_limiting"]["typing_delay"])
                    await page.click("#identifierNext, button:has-text('Next')")
                    await page.wait_for_load_state("domcontentloaded")
                    await random_delay([2, 4], "google-email-next")

                # Enter Google password
                password_input = await page.query_selector("input[type='password']")
                if password_input:
                    await human_type(page, "input[type='password']", google_creds.get("password", ""), config["rate_limiting"]["typing_delay"])
                    await page.click("#passwordNext, button:has-text('Next')")
                    await page.wait_for_load_state("domcontentloaded")
                    await random_delay(config["rate_limiting"]["page_load_delay"], "google-password-next")
            else:
                logger.warning("Google OAuth button not found, falling back to credentials")
                login_method = "credentials"

        elif login_method == "apple_oauth":
            logger.info("Logging in via Apple OAuth")
            apple_btn = await page.query_selector(
                "button:has-text('Sign in with Apple'), "
                "a:has-text('Sign in with Apple'), "
                "button[data-litms-control-urn*='apple']"
            )
            if apple_btn:
                await apple_btn.click()
                await page.wait_for_load_state("domcontentloaded")
                await random_delay(config["rate_limiting"]["page_load_delay"], "apple-oauth-page")

                apple_creds = config["linkedin"].get("apple_oauth", {})
                # Enter Apple ID
                email_input = await page.query_selector("input[type='text'], input#account_name_text_field")
                if email_input:
                    await human_type(page, "input[type='text'], input#account_name_text_field", apple_creds.get("email", ""), config["rate_limiting"]["typing_delay"])
                    await page.click("button#sign-in, button:has-text('Continue')")
                    await page.wait_for_load_state("domcontentloaded")
                    await random_delay([2, 4], "apple-email-next")

                # Enter Apple password
                password_input = await page.query_selector("input[type='password']")
                if password_input:
                    await human_type(page, "input[type='password']", apple_creds.get("password", ""), config["rate_limiting"]["typing_delay"])
                    await page.click("button#sign-in, button:has-text('Sign In')")
                    await page.wait_for_load_state("domcontentloaded")
                    await random_delay(config["rate_limiting"]["page_load_delay"], "apple-password-next")
            else:
                logger.warning("Apple OAuth button not found, falling back to credentials")
                login_method = "credentials"

        if login_method == "credentials":
            logger.info("Logging in via email/password")
            await human_type(page, "#username", config["linkedin"]["email"], config["rate_limiting"]["typing_delay"])
            await random_delay([0.5, 1.5], "between-fields")
            await human_type(page, "#password", config["linkedin"]["password"], config["rate_limiting"]["typing_delay"])
            await random_delay([0.5, 1.0], "before-submit")

            await page.click('button[type="submit"]')

        await page.wait_for_load_state("domcontentloaded")
        await random_delay(config["rate_limiting"]["page_load_delay"], "post-login")

        # Check for security challenge
        if "checkpoint" in page.url or "challenge" in page.url:
            logger.warning("LinkedIn security challenge detected. Manual intervention needed.")
            logger.warning("Current URL: %s", page.url)
            # Wait up to 2 minutes for manual resolution
            for _ in range(24):
                await asyncio.sleep(5)
                if "/feed" in page.url:
                    break
            else:
                logger.error("Security challenge not resolved within timeout")
                return False

        if "/feed" in page.url or "linkedin.com" in page.url:
            # Save cookies
            cookies = await context.cookies()
            Path(cookie_file).parent.mkdir(parents=True, exist_ok=True)
            with open(cookie_file, "w") as f:
                json.dump(cookies, f)
            logger.info("Login successful, cookies saved")
            return True

        logger.error("Login failed. Current URL: %s", page.url)
        return False

    except Exception as e:
        logger.error("Login error: %s", e)
        return False


async def search_jobs(page: Page, config: dict, role: str, location: str) -> list[dict]:
    """Search LinkedIn for jobs matching role and location."""
    jobs = []
    rate = config["rate_limiting"]
    posted_within = config["job_preferences"].get("posted_within_days", 7)

    # Map days to LinkedIn filter parameter
    time_filter = ""
    if posted_within <= 1:
        time_filter = "&f_TPR=r86400"
    elif posted_within <= 7:
        time_filter = "&f_TPR=r604800"
    elif posted_within <= 30:
        time_filter = "&f_TPR=r2592000"

    # Build search URL
    search_url = (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={role.replace(' ', '%20')}"
        f"&location={location.replace(' ', '%20')}"
        f"&f_WT=2"  # Remote + On-site
        f"{time_filter}"
        f"&sortBy=DD"  # Sort by date
    )

    logger.info("Searching: %s in %s", role, location)
    await page.goto(search_url, wait_until="domcontentloaded")
    await random_delay(rate["page_load_delay"], "search-results")

    max_pages = rate.get("max_pages_per_search", 10)

    for page_num in range(max_pages):
        logger.info("Processing search page %d", page_num + 1)

        # Scroll to load lazy content
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await random_delay(rate["scroll_delay"], "scroll")

        # Extract job cards
        job_cards = await page.query_selector_all(".job-card-container, .jobs-search-results__list-item")

        if not job_cards:
            logger.info("No job cards found on page %d", page_num + 1)
            break

        for card in job_cards:
            try:
                job = await extract_job_from_card(card, page, rate)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.warning("Error extracting job card: %s", e)
                continue

        # Try next page
        next_btn = await page.query_selector('button[aria-label="Next"]')
        if next_btn and await next_btn.is_enabled():
            await next_btn.click()
            await random_delay(rate["search_delay"], "next-page")
        else:
            break

    return jobs


async def extract_job_from_card(card, page: Page, rate: dict) -> dict | None:
    """Extract job details from a search result card."""
    try:
        # Get basic info from card
        title_el = await card.query_selector(".job-card-list__title, .job-card-container__link")
        company_el = await card.query_selector(".job-card-container__primary-description, .artdeco-entity-lockup__subtitle")
        location_el = await card.query_selector(".job-card-container__metadata-item, .artdeco-entity-lockup__caption")

        if not title_el:
            return None

        title = (await title_el.inner_text()).strip()
        company = (await company_el.inner_text()).strip() if company_el else "Unknown"
        location = (await location_el.inner_text()).strip() if location_el else "Unknown"

        # Get job URL and ID
        link_el = await card.query_selector("a[href*='/jobs/view/']")
        url = ""
        job_id = ""
        if link_el:
            href = await link_el.get_attribute("href")
            if href:
                url = href.split("?")[0]
                if "/jobs/view/" in url:
                    job_id = url.split("/jobs/view/")[-1].rstrip("/")

        if not job_id:
            return None

        # Click into the job to get details
        await title_el.click()
        await random_delay(rate["action_delay"], "job-detail")

        # Extract additional details from the detail panel
        description = ""
        salary_range = ""
        easy_apply = False
        employment_type = ""
        posted_date = ""

        try:
            # Check for Easy Apply button
            easy_apply_btn = await page.query_selector(".jobs-apply-button, button.jobs-apply-button--top-card")
            if easy_apply_btn:
                btn_text = await easy_apply_btn.inner_text()
                easy_apply = "easy apply" in btn_text.lower()

            # Get description
            desc_el = await page.query_selector(".jobs-description__content, .jobs-box__html-content")
            if desc_el:
                description = (await desc_el.inner_text()).strip()[:3000]

            # Get salary if shown
            salary_el = await page.query_selector(".job-details-jobs-unified-top-card__job-insight--highlight, .compensation__salary")
            if salary_el:
                salary_range = (await salary_el.inner_text()).strip()

            # Get employment type
            type_el = await page.query_selector(".job-details-jobs-unified-top-card__job-insight")
            if type_el:
                type_text = await type_el.inner_text()
                if any(t in type_text.lower() for t in ["full-time", "part-time", "contract", "temporary", "internship"]):
                    employment_type = type_text.strip()

            # Get posted date
            time_el = await page.query_selector(".jobs-unified-top-card__posted-date, time")
            if time_el:
                posted_date = (await time_el.inner_text()).strip()

        except Exception as e:
            logger.debug("Error getting job details: %s", e)

        return {
            "job_id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "salary_range": salary_range,
            "easy_apply": easy_apply,
            "url": f"https://www.linkedin.com/jobs/view/{job_id}",
            "posted_date": posted_date,
            "description": description,
            "employment_type": employment_type,
        }

    except Exception as e:
        logger.debug("Card extraction error: %s", e)
        return None


async def crawl_recruiter_posts(page: Page, config: dict) -> list[dict]:
    """Crawl LinkedIn posts from recruiters/hiring managers."""
    if not config.get("recruiter_crawling", {}).get("enabled", False):
        return []

    jobs_from_posts = []
    keywords = config["recruiter_crawling"]["keywords"]
    rate = config["rate_limiting"]
    max_posts = config["recruiter_crawling"].get("max_posts_per_session", 50)

    for keyword in keywords[:5]:  # Limit keyword searches
        search_url = f"https://www.linkedin.com/search/results/content/?keywords={keyword.replace(' ', '%20')}&sortBy=%22date_posted%22"
        await page.goto(search_url, wait_until="domcontentloaded")
        await random_delay(rate["search_delay"], "recruiter-search")

        # Scroll to load posts
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await random_delay(rate["scroll_delay"], "scroll-posts")

        posts = await page.query_selector_all(".feed-shared-update-v2")
        for post in posts[:max_posts]:
            try:
                text_el = await post.query_selector(".feed-shared-text")
                if text_el:
                    text = (await text_el.inner_text()).strip()
                    # Look for job-like content
                    if any(kw in text.lower() for kw in ["hiring", "apply", "role", "position", "engineer"]):
                        # Extract any linked jobs
                        links = await post.query_selector_all("a[href*='/jobs/view/']")
                        for link in links:
                            href = await link.get_attribute("href")
                            if href and "/jobs/view/" in href:
                                job_id = href.split("/jobs/view/")[-1].split("?")[0].rstrip("/")
                                jobs_from_posts.append({
                                    "job_id": job_id,
                                    "url": f"https://www.linkedin.com/jobs/view/{job_id}",
                                    "source": "recruiter_post",
                                    "post_snippet": text[:500],
                                })
            except Exception as e:
                logger.debug("Error parsing recruiter post: %s", e)

        await random_delay(rate["search_delay"], "between-keyword-searches")

    logger.info("Found %d potential jobs from recruiter posts", len(jobs_from_posts))
    return jobs_from_posts


def load_cache(cache_path: str) -> set[str]:
    """Load seen job IDs from cache."""
    if Path(cache_path).exists():
        with open(cache_path) as f:
            data = json.load(f)
        return set(data.get("seen_ids", []))
    return set()


def save_cache(cache_path: str, seen_ids: set[str]):
    """Save seen job IDs to cache."""
    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump({"seen_ids": list(seen_ids)}, f)


async def crawl_jobs(config_path: str) -> list[dict]:
    """Main crawl pipeline."""
    config = load_config_with_vault(config_path)

    cache_path = config["paths"]["jobs_cache"]
    seen_ids = load_cache(cache_path)
    all_jobs = []

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
            logger.error("Failed to log into LinkedIn")
            await browser.close()
            return []

        # Search for each role × location
        roles = config["job_preferences"]["target_roles"]
        locations = config["job_preferences"]["locations"]
        searches_done = 0
        max_searches = config["rate_limiting"].get("max_searches_per_session", 20)

        for role in roles:
            for location in locations:
                if searches_done >= max_searches:
                    logger.info("Hit max searches per session (%d), stopping", max_searches)
                    break

                jobs = await search_jobs(page, config, role, location)
                for job in jobs:
                    if job["job_id"] not in seen_ids:
                        all_jobs.append(job)
                        seen_ids.add(job["job_id"])

                searches_done += 1
                await random_delay(config["rate_limiting"]["search_delay"], "between-searches")

            if searches_done >= max_searches:
                break

        # Crawl recruiter posts
        recruiter_jobs = await crawl_recruiter_posts(page, config)
        for rj in recruiter_jobs:
            if rj["job_id"] not in seen_ids:
                # We only have partial info from posts — mark for detail fetch
                all_jobs.append(rj)
                seen_ids.add(rj["job_id"])

        await browser.close()

    # Save updated cache
    save_cache(cache_path, seen_ids)
    logger.info("Crawl complete. %d new jobs found.", len(all_jobs))

    return all_jobs


def main():
    parser = argparse.ArgumentParser(description="Crawl LinkedIn for jobs")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    jobs = asyncio.run(crawl_jobs(args.config))
    # Output to stdout for pipeline consumption
    json.dump(jobs, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
