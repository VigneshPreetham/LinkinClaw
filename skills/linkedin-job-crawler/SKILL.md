---
name: linkedin-job-crawler
description: "Crawl LinkedIn for job postings matching target roles and locations using Playwright browser automation. Also crawls recruiter/hiring manager posts. Use when: the agent needs to find new job listings from LinkedIn."
---

# LinkedIn Job Crawler

Crawl LinkedIn for jobs matching configured preferences using Playwright.

## Usage

```bash
python skills/linkedin-job-crawler/scripts/crawl_jobs.py --config config.yaml
```

## What It Does

1. Launches Chromium via Playwright (headless=false for anti-detection)
2. Logs into LinkedIn (or reuses saved cookies)
3. Searches for each target role × location combination
4. Extracts job details: title, company, location, salary, Easy Apply status, URL, posting date
5. Optionally crawls recruiter posts for "hiring" keywords
6. Deduplicates against `data/jobs_cache.json`
7. Outputs new jobs as JSON to stdout

## Output

Writes new jobs to stdout (JSON array) and updates `data/jobs_cache.json`.

Each job object:

```json
{
  "job_id": "3812345678",
  "title": "ML Engineer",
  "company": "Acme Corp",
  "location": "San Francisco, CA",
  "salary_range": "$180K - $250K",
  "easy_apply": true,
  "url": "https://www.linkedin.com/jobs/view/3812345678",
  "posted_date": "2 days ago",
  "description": "...",
  "employment_type": "Full-time"
}
```

## Rate Limiting

All delays are configurable in `config.yaml` under `rate_limiting`:
- Page loads: 3-7s delay
- Between actions: 30-60s
- Between searches: 10-20s
- Human-like typing: 0.05-0.15s per keystroke
- Max 500 page views/day
- Session breaks every 20 searches

## Anti-Detection

- Real Chromium (not headless by default)
- Randomized delays
- Human-like scrolling and typing
- Cookie persistence to reduce logins
- Standard user-agent string
