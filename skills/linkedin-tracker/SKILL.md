---
name: linkedin-tracker
description: "Track job application status in CSV. Log applications, update statuses, and generate reports. Use when: the agent needs to record applications, check history, or report stats."
---

# LinkedIn Application Tracker

Manage the application log at `data/applications.csv`.

## Usage

```bash
# Log results from an application run
python skills/linkedin-tracker/scripts/tracker.py --config config.yaml log --results data/results.json

# Show stats
python skills/linkedin-tracker/scripts/tracker.py --config config.yaml stats

# Update a status
python skills/linkedin-tracker/scripts/tracker.py --config config.yaml update --url "https://..." --status interview

# Show flagged (big tech) jobs
python skills/linkedin-tracker/scripts/tracker.py --config config.yaml flagged

# Check if a URL was already applied to
python skills/linkedin-tracker/scripts/tracker.py --config config.yaml check --url "https://..."
```

## CSV Columns

`date, company, role, location, url, status, method, relevance_score, reasoning, notes`

## Status Values

- `applied` — Successfully applied via Easy Apply
- `flagged_for_manual` — Big tech, needs manual application
- `external_application_needed` — Requires external application
- `interview` — Got an interview (manual update)
- `rejected` — Rejected (manual update)
- `offer` — Received offer (manual update)
- `error` — Application failed
