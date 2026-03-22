#!/usr/bin/env python3
"""
Job relevance scorer — scores jobs against the parsed resume.
Uses keyword matching + OpenClaw agent for AI semantic scoring.
"""

import argparse
import json
import logging
import re
import subprocess
import sys
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_resume(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def is_big_tech(company: str, big_tech_list: list[str]) -> bool:
    company_lower = company.lower().strip()
    for bt in big_tech_list:
        if bt.lower() in company_lower or company_lower in bt.lower():
            return True
    return False


def is_contract(job: dict, exclude_types: list[str]) -> bool:
    text = f"{job.get('title', '')} {job.get('description', '')} {job.get('employment_type', '')}".lower()
    return any(excl.lower() in text for excl in exclude_types)


def keyword_score(job: dict, resume: dict, config: dict) -> tuple[int, str]:
    """Score based on keyword/skill matching. Returns (score, reasoning)."""
    job_text = f"{job.get('title', '')} {job.get('description', '')} {job.get('location', '')}".lower()
    resume_skills = [s.lower() for s in resume.get("skills", [])]

    # Skill match (up to 40 points)
    matched_skills = [s for s in resume_skills if s in job_text]
    skill_ratio = len(matched_skills) / max(len(resume_skills), 1)
    skill_score = min(int(skill_ratio * 60), 40)

    # Title relevance (up to 25 points)
    target_roles = [r.lower() for r in config["job_preferences"]["target_roles"]]
    title_lower = job.get("title", "").lower()
    title_score = 0
    for role in target_roles:
        role_words = role.split()
        match_count = sum(1 for w in role_words if w in title_lower)
        ratio = match_count / len(role_words)
        title_score = max(title_score, int(ratio * 25))

    # Experience level (up to 15 points)
    exp_score = 15
    if any(kw in title_lower for kw in ["director", "vp ", "vice president", "chief", "head of", "principal"]):
        exp_score = 5
    elif any(kw in title_lower for kw in ["intern", "junior", "entry level", "co-op"]):
        exp_score = 8

    # Location match (up to 10 points)
    loc_score = 0
    job_location = job.get("location", "").lower()
    target_locations = [l.lower() for l in config["job_preferences"]["locations"]]
    if any(loc in job_location for loc in target_locations):
        loc_score = 10
    elif "remote" in job_location:
        loc_score = 8

    # Research keywords (up to 10 points)
    research_kws = [
        "research", "publication", "paper", "icml", "neurips", "cvpr",
        "iclr", "deep learning", "computer vision", "multimodal",
        "machine learning", "neural network", "transformer",
    ]
    research_matches = sum(1 for kw in research_kws if kw in job_text)
    research_score = min(research_matches * 2, 10)

    total = min(skill_score + title_score + exp_score + loc_score + research_score, 100)

    reasoning = (
        f"Keywords: skills={skill_score}/40 (matched: {', '.join(matched_skills[:8])}), "
        f"title={title_score}/25, exp={exp_score}/15, "
        f"loc={loc_score}/10, research={research_score}/10 → {total}/100"
    )
    return total, reasoning


def ai_score(job: dict, resume: dict) -> tuple[int, str] | None:
    """Score using OpenClaw agent for semantic analysis. Returns (score, reasoning) or None on failure."""
    resume_summary = (
        f"Name: {resume.get('contact', {}).get('name', 'N/A')}\n"
        f"Skills: {', '.join(resume.get('skills', []))}\n"
        f"Experience: {json.dumps(resume.get('experience', []), default=str)[:1500]}\n"
        f"Publications: {len(resume.get('publications', []))} papers\n"
    )

    job_summary = (
        f"Title: {job.get('title', 'N/A')}\n"
        f"Company: {job.get('company', 'N/A')}\n"
        f"Location: {job.get('location', 'N/A')}\n"
        f"Description: {job.get('description', 'N/A')[:2000]}\n"
    )

    prompt = (
        "Score this job's relevance to the candidate (0-100). Consider: skill match, "
        "experience alignment, research background, role title fit.\n\n"
        f"CANDIDATE:\n{resume_summary}\n"
        f"JOB:\n{job_summary}\n\n"
        'Respond ONLY with JSON: {"score": <0-100>, "reasoning": "<brief>"}'
    )

    try:
        result = subprocess.run(
            ["openclaw", "agent", "--agent", "linkedin", "--message", prompt, "--json", "--local"],
            capture_output=True, text=True, timeout=60,
        )

        if result.returncode != 0:
            logger.warning("OpenClaw agent call failed: %s", result.stderr[:200])
            return None

        # Parse the agent response
        output = result.stdout
        # Try to find JSON in the output
        try:
            data = json.loads(output)
            # OpenClaw agent --json wraps the response
            reply_text = data.get("reply", data.get("message", data.get("content", output)))
        except json.JSONDecodeError:
            reply_text = output

        # Extract score JSON from the reply
        json_match = re.search(r'\{[^}]*"score"\s*:\s*\d+[^}]*\}', str(reply_text))
        if json_match:
            score_data = json.loads(json_match.group())
            score = max(0, min(100, int(score_data["score"])))
            reasoning = f"AI: {score_data.get('reasoning', 'No reasoning')}"
            return score, reasoning

        logger.warning("Could not parse AI score from response")
        return None

    except subprocess.TimeoutExpired:
        logger.warning("OpenClaw agent scoring timed out")
        return None
    except Exception as e:
        logger.warning("AI scoring error: %s", e)
        return None


def score_jobs(jobs: list[dict], config_path: str) -> list[dict]:
    """Score all jobs, filter, and sort by relevance."""
    config = load_config(config_path)
    resume_path = config["paths"]["parsed_resume"]

    if not Path(resume_path).exists():
        logger.error("Parsed resume not found at %s. Run resume parser first.", resume_path)
        return []

    resume = load_resume(resume_path)
    big_tech_list = config.get("big_tech_companies", [])
    exclude_types = config["job_preferences"].get("job_type_exclude", [])
    min_score = config["application"].get("min_relevance_score", 50)

    scored = []

    for job in jobs:
        # Skip contract roles
        if is_contract(job, exclude_types):
            logger.info("Skipping contract: %s at %s", job.get("title"), job.get("company"))
            continue

        big_tech = is_big_tech(job.get("company", ""), big_tech_list)

        # Try AI scoring first, fall back to keywords
        ai_result = ai_score(job, resume)
        if ai_result:
            score, reasoning = ai_result
        else:
            score, reasoning = keyword_score(job, resume, config)

        if score < min_score:
            logger.info("Below threshold (%d < %d): %s at %s", score, min_score, job.get("title"), job.get("company"))
            continue

        scored.append({
            "job": job,
            "relevance_score": score,
            "reasoning": reasoning,
            "is_big_tech": big_tech,
            "is_contract": False,
        })

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    logger.info("Scored %d jobs (after filters). Top: %d, Bottom: %d",
                len(scored),
                scored[0]["relevance_score"] if scored else 0,
                scored[-1]["relevance_score"] if scored else 0)

    return scored


def main():
    parser = argparse.ArgumentParser(description="Score jobs for relevance")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--jobs", required=True, help="Path to crawled jobs JSON (or - for stdin)")
    args = parser.parse_args()

    if args.jobs == "-":
        jobs = json.load(sys.stdin)
    else:
        with open(args.jobs) as f:
            jobs = json.load(f)

    results = score_jobs(jobs, args.config)
    json.dump(results, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
