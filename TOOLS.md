# TOOLS.md — LinkinClaw

## Pipeline Command

Full pipeline (from workspace root):
```bash
python skills/linkedin-pipeline/scripts/run_pipeline.py --config config.yaml
```

Individual steps:
```bash
python skills/linkedin-resume-parser/scripts/parse_resume.py --config config.yaml
python skills/linkedin-job-crawler/scripts/crawl_jobs.py --config config.yaml > data/crawled_jobs.json
python skills/linkedin-job-scorer/scripts/score_jobs.py --config config.yaml --jobs data/crawled_jobs.json > data/scored_jobs.json
python skills/linkedin-applicant/scripts/apply_jobs.py --config config.yaml --scored data/scored_jobs.json > data/results.json
python skills/linkedin-tracker/scripts/tracker.py --config config.yaml log --results data/results.json
python skills/linkedin-tracker/scripts/tracker.py --config config.yaml stats
```

## Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```
