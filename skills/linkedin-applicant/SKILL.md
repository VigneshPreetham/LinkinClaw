---
name: linkedin-applicant
description: "Apply to jobs on LinkedIn via Easy Apply using Playwright. Flags big tech companies for manual review. Use when: the agent has scored jobs and needs to submit applications."
---

# LinkedIn Applicant

Automate LinkedIn Easy Apply and flag big tech for manual review.

## Usage

```bash
python skills/linkedin-applicant/scripts/apply_jobs.py --config config.yaml --scored data/scored_jobs.json
```

## What It Does

For each scored job (sorted by relevance):

1. **Big tech company?** → Log as `flagged_for_manual` in CSV, skip
2. **Easy Apply available?** → Automate the application form via Playwright
3. **External application?** → Log as `external_application_needed`
4. **Rate limit reached?** → Stop for this run

## Easy Apply Automation

Handles multi-step Easy Apply forms:
- Fills contact info (name, email, phone) from config
- Uploads resume PDF
- Answers sponsorship question
- Answers common dropdowns/radio buttons
- Clicks through "Next" / "Review" / "Submit"

## Safety

- Max 5 applications per hour (configurable)
- Random 30-60s delays between applications
- Max 25 applications per day
- Stops on errors rather than retrying blindly
- Screenshots on failure for debugging (`data/screenshots/`)
