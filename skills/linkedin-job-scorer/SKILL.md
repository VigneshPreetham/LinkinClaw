---
name: linkedin-job-scorer
description: "Score job listings for relevance against a parsed resume using keyword matching and OpenClaw agent AI scoring. Use when: the agent needs to rank/filter crawled jobs by relevance before applying."
---

# LinkedIn Job Scorer

Score crawled jobs for relevance against the parsed resume. Uses keyword matching as a baseline, with AI semantic scoring via the OpenClaw agent's model.

## Usage

```bash
python skills/linkedin-job-scorer/scripts/score_jobs.py --config config.yaml --jobs data/crawled_jobs.json
```

Or pipe from crawler:

```bash
python .../crawl_jobs.py --config config.yaml | python .../score_jobs.py --config config.yaml --jobs -
```

## Scoring Method

### Keyword Matching (always runs, 0-100)
- Skill match: up to 40 points
- Title relevance: up to 25 points
- Experience level: up to 15 points
- Location match: up to 10 points
- Research keywords: up to 10 points

### AI Semantic Scoring (via OpenClaw agent)
Instead of direct API calls, scoring uses `openclaw agent` CLI to leverage the gateway's model routing. This means:
- No separate API keys needed
- Uses whatever model is configured for the linkedin agent
- Billing goes through the existing OpenClaw setup

The script calls:
```bash
openclaw agent --agent linkedin --message "<scoring prompt>" --json --local
```

Falls back to keyword matching if AI scoring fails.

## Output

Writes scored jobs as JSON to stdout, sorted by relevance score (descending).

```json
[
  {
    "job": { ... },
    "relevance_score": 85,
    "reasoning": "AI: Strong match...",
    "is_big_tech": false,
    "is_contract": false
  }
]
```

## Filters Applied
- Contract/temporary roles → skipped entirely
- Jobs below `min_relevance_score` (config) → excluded
- Big tech companies → flagged (still scored, but marked)
