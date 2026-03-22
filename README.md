# 🔗 LinkinClaw

**An OpenClaw-powered LinkedIn job application bot.** Automatically finds, scores, and applies to jobs on LinkedIn based on your resume and preferences.

> Built on [OpenClaw](https://github.com/openclaw/openclaw) — your AI runs as an autonomous agent with its own workspace, skills, and cron schedule.

---

## ✨ Features

- **Resume Parsing** — Extracts skills, experience, education from your PDF resume
- **Smart Job Crawling** — Searches LinkedIn for matching roles + crawls recruiter posts
- **AI Relevance Scoring** — Scores jobs against your resume using OpenClaw's model routing (no extra API keys)
- **Auto Easy Apply** — Fills and submits LinkedIn Easy Apply forms via Playwright
- **Big Tech Flagging** — Flags FAANG/big tech jobs for manual application instead of auto-applying
- **Application Tracking** — Logs everything to CSV with status tracking
- **Rate Limiting** — Conservative defaults to protect your LinkedIn account
- **Cron Automation** — Runs hourly via OpenClaw's built-in cron system

---

## 📋 Prerequisites

- [OpenClaw](https://github.com/openclaw/openclaw) installed and configured
- Python 3.10+
- A LinkedIn account (Premium recommended for better crawling)
- An Anthropic or OpenAI API key configured in OpenClaw

---

## 🚀 Setup

### 1. Install OpenClaw

If you don't have OpenClaw yet:

```bash
# See https://docs.openclaw.ai/install for full instructions
curl -fsSL https://get.openclaw.ai | bash
openclaw setup
```

### 2. Clone this repo

```bash
git clone https://github.com/YOUR_USERNAME/LinkinClaw.git
cd LinkinClaw
```

### 3. Create the LinkedIn agent in OpenClaw

```bash
openclaw agents add linkedin --workspace "$(pwd)/workspace"
```

This registers a new `linkedin` agent with OpenClaw, using the workspace in this repo.

### 4. Copy the workspace files

```bash
cp -r workspace-template/* workspace/
```

Or if you cloned directly into the workspace:

```bash
openclaw agents add linkedin --workspace "$(pwd)"
```

### 5. Install Python dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 6. Configure your vault (credentials)

```bash
cp vault/secrets.example.yaml vault/secrets.yaml
```

Edit `vault/secrets.yaml` with your LinkedIn credentials:

```yaml
linkedin:
  email: "your-real-email@example.com"
  password: "your-real-password"
```

> ⚠️ **`vault/secrets.yaml` is gitignored.** Your credentials never leave your machine.

### 7. Configure job preferences

Edit `config.yaml` to set your:

- Target roles
- Preferred locations
- Minimum salary
- Sponsorship requirements
- Company blacklist/big tech list
- Rate limits

### 8. Add your resume

```bash
cp /path/to/your/resume.pdf resume.pdf
```

### 9. Test it

```bash
# Parse your resume first
cd workspace && python skills/linkedin-resume-parser/scripts/parse_resume.py --config config.yaml

# Verify the parsed output
cat parsed_resume.json | python -m json.tool

# Run the full pipeline
openclaw agent --agent linkedin --message "Run the LinkedIn job application pipeline" --local
```

### 10. Set up the hourly cron

From any OpenClaw session, run:

```
/cron add linkedin-apply --schedule "0 * * * *" --agent linkedin --message "Run the LinkedIn job application pipeline. Execute the full cycle: parse resume, crawl jobs, score, apply to top 5, and report results."
```

Or via CLI:

```bash
openclaw cron add --name "linkedin-apply" \
  --schedule "0 * * * *" \
  --agent linkedin \
  --message "Run the LinkedIn job application pipeline."
```

---

## 📁 Project Structure

```
LinkinClaw/
├── README.md                 # You're reading it
├── requirements.txt          # Python dependencies
├── config.yaml               # Job preferences (safe to commit)
├── vault/
│   ├── secrets.example.yaml  # Template for credentials
│   ├── secrets.yaml          # YOUR credentials (gitignored!)
│   └── README.md             # Vault documentation
├── skills/
│   ├── linkedin-resume-parser/
│   │   ├── SKILL.md
│   │   └── scripts/parse_resume.py
│   ├── linkedin-job-crawler/
│   │   ├── SKILL.md
│   │   └── scripts/crawl_jobs.py
│   ├── linkedin-job-scorer/
│   │   ├── SKILL.md
│   │   └── scripts/score_jobs.py
│   ├── linkedin-applicant/
│   │   ├── SKILL.md
│   │   └── scripts/apply_jobs.py
│   ├── linkedin-tracker/
│   │   ├── SKILL.md
│   │   └── scripts/tracker.py
│   └── linkedin-pipeline/
│       ├── SKILL.md
│       └── scripts/run_pipeline.py
├── SOUL.md                   # Agent personality
├── AGENTS.md                 # Agent instructions
├── IDENTITY.md               # Agent identity
├── USER.md                   # User info template
├── TOOLS.md                  # Tool reference
├── HEARTBEAT.md              # Heartbeat config
└── data/                     # Runtime data (gitignored)
    ├── applications.csv
    ├── jobs_cache.json
    └── pipeline.log
```

---

## 🔐 Vault System

LinkinClaw uses a simple vault for sensitive data:

- `vault/secrets.yaml` — Your LinkedIn credentials + any API keys
- `vault/secrets.example.yaml` — Template showing what's needed
- The vault directory is **gitignored** (except the example file)

The bot reads credentials from the vault at runtime. Your secrets never touch git.

### What goes in the vault:

| Key | Description | Required |
|-----|-------------|----------|
| `linkedin.email` | Your LinkedIn email | ✅ |
| `linkedin.password` | Your LinkedIn password | ✅ |
| `user_profile.name` | Full name for applications | ✅ |
| `user_profile.email` | Email for applications | ✅ |
| `user_profile.phone` | Phone for applications | ✅ |

---

## ⚙️ Configuration Reference

See `config.yaml` for all options. Key settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `job_preferences.target_roles` | — | Job titles to search for |
| `job_preferences.locations` | — | Preferred locations |
| `job_preferences.min_base_salary` | 0 | Minimum base salary |
| `application.max_applications_per_hour` | 5 | Rate limit |
| `application.top_n_per_run` | 5 | Jobs to apply to per run |
| `application.min_relevance_score` | 50 | Minimum AI score (0-100) |
| `big_tech_companies` | [list] | Flag for manual review |

---

## 📊 Tracking Applications

```bash
# View stats
python skills/linkedin-tracker/scripts/tracker.py --config config.yaml stats

# View flagged big tech jobs
python skills/linkedin-tracker/scripts/tracker.py --config config.yaml flagged

# Update a status (e.g., got an interview)
python skills/linkedin-tracker/scripts/tracker.py --config config.yaml update \
  --url "https://linkedin.com/jobs/view/123" --status interview
```

### Status Values

| Status | Meaning |
|--------|---------|
| `applied` | ✅ Successfully applied via Easy Apply |
| `flagged_for_manual` | 🏢 Big tech — needs manual application |
| `external_application_needed` | 🔗 No Easy Apply, external site required |
| `interview` | 🎯 Got an interview |
| `rejected` | ❌ Rejected |
| `offer` | 🎉 Received an offer |

---

## ⚠️ Important Notes

### LinkedIn Rate Limits & Account Safety

- Default: **5 applications/hour**, 30-60s delays between actions
- Max **500 page views/day**
- Session breaks every 20 searches
- Human-like typing and scrolling delays
- **There is always some risk with automation.** LinkedIn may flag your account. Use at your own discretion.

### What This Bot Does NOT Do

- ❌ Auto-apply to big tech (flags them for you)
- ❌ Generate cover letters (skipped by default)
- ❌ Apply to contract/temporary roles
- ❌ Store your credentials in git

---

## 🤝 Contributing

PRs welcome! Please keep the OpenClaw skill structure intact.

---

## 📜 License

MIT — Use responsibly. Don't spam recruiters. 💼
