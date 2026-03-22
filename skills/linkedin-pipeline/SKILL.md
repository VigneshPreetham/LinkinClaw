---
name: linkedin-pipeline
description: "Full LinkedIn job application pipeline: parse resume → crawl → score → apply → track. Use when: the agent receives a cron trigger or is asked to run the full job application cycle."
---

# LinkedIn Pipeline

The orchestrator that runs the full application cycle.

## Usage

```bash
python skills/linkedin-pipeline/scripts/run_pipeline.py --config config.yaml
```

## Pipeline Steps

1. **Parse resume** → `parsed_resume.json` (skips if already parsed and resume unchanged)
2. **Crawl LinkedIn** → find new matching jobs
3. **Score jobs** → AI relevance scoring via OpenClaw agent
4. **Deduplicate** → skip already-applied jobs
5. **Apply** → Easy Apply for top N, flag big tech, note external apps
6. **Track** → log everything to `data/applications.csv`
7. **Report** → print summary

## Cron Integration

This pipeline is designed to be triggered by an OpenClaw cron job. The cron calls:

```
openclaw agent --agent linkedin --message "Run the LinkedIn job application pipeline. Execute the full cycle: parse resume, crawl jobs, score, apply to top 5, and report results."
```

The agent then uses this skill to run the pipeline.

## Error Handling

Each step has independent error handling. If crawling fails, the pipeline stops. If a single application fails, it logs the error and continues to the next job.
