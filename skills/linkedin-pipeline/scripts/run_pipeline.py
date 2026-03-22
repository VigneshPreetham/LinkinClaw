#!/usr/bin/env python3
"""
Full LinkedIn job application pipeline orchestrator.
Runs: parse → crawl → score → apply → track → report
"""

import argparse
import asyncio
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Add project root to path for vault import
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from lib.vault import load_config_with_vault

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/pipeline.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)

# Add skills scripts to path
SKILLS_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SKILLS_DIR / "linkedin-resume-parser" / "scripts"))
sys.path.insert(0, str(SKILLS_DIR / "linkedin-job-crawler" / "scripts"))
sys.path.insert(0, str(SKILLS_DIR / "linkedin-job-scorer" / "scripts"))
sys.path.insert(0, str(SKILLS_DIR / "linkedin-applicant" / "scripts"))
sys.path.insert(0, str(SKILLS_DIR / "linkedin-tracker" / "scripts"))


def load_config(path: str) -> dict:
    return load_config_with_vault(path)


async def run_pipeline(config_path: str) -> dict:
    """Execute the full pipeline. Returns a summary dict."""
    config = load_config(config_path)
    summary = {
        "timestamp": datetime.now().isoformat(),
        "steps": {},
        "success": False,
    }

    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)

    # ─── Step 1: Parse Resume ───
    logger.info("=" * 60)
    logger.info("STEP 1: Parsing Resume")
    logger.info("=" * 60)

    parsed_path = config["paths"]["parsed_resume"]
    resume_path = config["paths"]["resume_pdf"]

    try:
        from parse_resume import parse_resume
        parsed = parse_resume(resume_path)
        with open(parsed_path, "w") as f:
            json.dump(parsed, f, indent=2)

        summary["steps"]["parse"] = {
            "status": "ok",
            "name": parsed["contact"].get("name", "Unknown"),
            "skills": len(parsed.get("skills", [])),
            "experience": len(parsed.get("experience", [])),
        }
        logger.info("Resume parsed: %s (%d skills, %d experience entries)",
                     parsed["contact"].get("name"), len(parsed.get("skills", [])),
                     len(parsed.get("experience", [])))
    except Exception as e:
        logger.error("Resume parsing failed: %s", e, exc_info=True)
        summary["steps"]["parse"] = {"status": "error", "error": str(e)}
        return summary

    # ─── Step 2: Crawl Jobs ───
    logger.info("=" * 60)
    logger.info("STEP 2: Crawling LinkedIn")
    logger.info("=" * 60)

    try:
        from crawl_jobs import crawl_jobs
        jobs = await crawl_jobs(config_path)
        summary["steps"]["crawl"] = {"status": "ok", "jobs_found": len(jobs)}
        logger.info("Found %d new jobs", len(jobs))
    except Exception as e:
        logger.error("Crawl failed: %s", e, exc_info=True)
        summary["steps"]["crawl"] = {"status": "error", "error": str(e)}
        return summary

    if not jobs:
        logger.info("No new jobs found. Pipeline complete.")
        summary["steps"]["crawl"]["note"] = "No new jobs"
        summary["success"] = True
        return summary

    # ─── Step 3: Score Jobs ───
    logger.info("=" * 60)
    logger.info("STEP 3: Scoring Jobs")
    logger.info("=" * 60)

    try:
        from score_jobs import score_jobs
        scored = score_jobs(jobs, config_path)
        summary["steps"]["score"] = {
            "status": "ok",
            "scored": len(scored),
            "top_score": scored[0]["relevance_score"] if scored else 0,
        }
        logger.info("Scored %d jobs", len(scored))
        for s in scored[:5]:
            logger.info("  [%d] %s at %s %s",
                        s["relevance_score"], s["job"]["title"],
                        s["job"]["company"],
                        "(BIG TECH)" if s["is_big_tech"] else "")
    except Exception as e:
        logger.error("Scoring failed: %s", e, exc_info=True)
        summary["steps"]["score"] = {"status": "error", "error": str(e)}
        return summary

    if not scored:
        logger.info("No qualifying jobs after scoring. Pipeline complete.")
        summary["success"] = True
        return summary

    # ─── Step 4: Deduplicate ───
    from tracker import is_applied
    before = len(scored)
    scored = [s for s in scored if not is_applied(config_path, s["job"].get("url", ""))]
    logger.info("Deduplication: %d → %d jobs", before, len(scored))

    if not scored:
        logger.info("All jobs already applied to. Pipeline complete.")
        summary["success"] = True
        return summary

    # ─── Step 5: Apply ───
    logger.info("=" * 60)
    logger.info("STEP 4: Applying to Jobs")
    logger.info("=" * 60)

    try:
        from apply_jobs import apply_to_jobs
        results = await apply_to_jobs(scored, config_path)
        applied = sum(1 for r in results if r["status"] == "applied")
        flagged = sum(1 for r in results if r["status"] == "flagged_for_manual")
        external = sum(1 for r in results if r["status"] == "external_application_needed")
        errors = sum(1 for r in results if r["status"] == "error")

        summary["steps"]["apply"] = {
            "status": "ok",
            "applied": applied,
            "flagged": flagged,
            "external": external,
            "errors": errors,
        }
    except Exception as e:
        logger.error("Application phase failed: %s", e, exc_info=True)
        summary["steps"]["apply"] = {"status": "error", "error": str(e)}
        return summary

    # ─── Step 6: Track ───
    logger.info("=" * 60)
    logger.info("STEP 5: Logging Results")
    logger.info("=" * 60)

    try:
        from tracker import log_results, get_stats
        log_results(config_path, results)
        stats = get_stats(config_path)
        logger.info("\n%s", stats)
        summary["steps"]["track"] = {"status": "ok"}
    except Exception as e:
        logger.error("Tracking failed: %s", e, exc_info=True)
        summary["steps"]["track"] = {"status": "error", "error": str(e)}

    # ─── Summary ───
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("  Applied: %d | Flagged: %d | External: %d | Errors: %d",
                applied, flagged, external, errors)
    logger.info("=" * 60)

    summary["success"] = True
    return summary


def main():
    parser = argparse.ArgumentParser(description="LinkedIn Job Bot Pipeline")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    Path("data").mkdir(exist_ok=True)

    summary = asyncio.run(run_pipeline(args.config))
    print(json.dumps(summary, indent=2))

    # Write daily memory log
    today = datetime.now().strftime("%Y-%m-%d")
    memory_dir = Path("memory")
    memory_dir.mkdir(exist_ok=True)
    memory_file = memory_dir / f"{today}.md"

    with open(memory_file, "a") as f:
        f.write(f"\n## Pipeline Run — {datetime.now().strftime('%H:%M')}\n")
        for step, info in summary["steps"].items():
            f.write(f"- {step}: {info.get('status', '?')}")
            if "error" in info:
                f.write(f" — {info['error']}")
            f.write("\n")
        if "apply" in summary["steps"]:
            a = summary["steps"]["apply"]
            f.write(f"- Results: {a.get('applied', 0)} applied, {a.get('flagged', 0)} flagged, "
                    f"{a.get('external', 0)} external, {a.get('errors', 0)} errors\n")


if __name__ == "__main__":
    main()
