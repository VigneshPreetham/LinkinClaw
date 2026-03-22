# 🔗 LinkinClaw

**An OpenClaw-powered LinkedIn job application bot.** Automatically finds, scores, and applies to jobs on LinkedIn — set up entirely through chat.

> Built on [OpenClaw](https://github.com/openclaw/openclaw). Your AI agent runs autonomously with its own workspace, skills, and cron schedule.

---

## ✨ Features

- **Conversational Setup** — No terminal needed after install. The bot walks you through everything via chat.
- **Resume Parsing** — Upload your PDF and the bot extracts skills, experience, education
- **Smart Job Crawling** — Searches LinkedIn for matching roles + crawls recruiter posts
- **AI Relevance Scoring** — Scores jobs against your resume using OpenClaw's model routing
- **Auto Easy Apply** — Fills and submits LinkedIn Easy Apply forms via Playwright
- **Big Tech Flagging** — Flags FAANG/big tech jobs for manual application
- **Application Tracking** — Logs everything to CSV with status tracking
- **Hourly Cron** — Runs automatically on a schedule you choose
- **Secure Vault** — LinkedIn credentials stored locally, never committed to git

---

## 🚀 Getting Started (One-Time Terminal Setup)

You only need the terminal **once** to install. After that, everything happens through the OpenClaw web UI chat.

### 1. Install OpenClaw (if you don't have it)

```bash
curl -fsSL https://get.openclaw.ai | bash
openclaw setup
```

See [OpenClaw docs](https://docs.openclaw.ai/install) for full instructions.

### 2. Clone LinkinClaw

```bash
git clone https://github.com/VigneshPreetham/LinkinClaw.git
cd LinkinClaw
```

### 3. Register the agent

```bash
openclaw agents add linkedin --workspace "$(pwd)"
openclaw gateway restart
```

### 4. Open the web UI and chat!

```bash
openclaw tui
```

Or open the OpenClaw web UI in your browser. Start chatting with the **linkedin** agent — it will walk you through:

1. 📄 Upload your resume (drag & drop)
2. 🎯 Set your job preferences (roles, locations, salary, etc.)
3. 🔑 Provide your LinkedIn credentials (stored securely in local vault)
4. ⏰ Choose your application frequency
5. 🚀 Start applying!

**That's it. No more terminal.**

---

## 📁 Project Structure

```
LinkinClaw/
├── README.md                 # You're reading it
├── BOOTSTRAP.md              # First-run onboarding flow (auto-deleted after setup)
├── SOUL.md                   # Agent personality & rules
├── AGENTS.md                 # Agent instructions
├── IDENTITY.md               # Agent identity
├── USER.md                   # Your info (populated during setup)
├── TOOLS.md                  # Command reference
├── HEARTBEAT.md              # Heartbeat config
├── config.yaml               # Job preferences (populated during setup)
├── requirements.txt          # Python dependencies
├── lib/
│   └── vault.py              # Vault loader (merges secrets into config)
├── vault/
│   ├── secrets.example.yaml  # Template for credentials
│   ├── secrets.yaml          # YOUR credentials (gitignored!)
│   └── README.md             # Vault documentation
├── skills/
│   ├── linkedin-resume-parser/    # PDF → structured JSON
│   ├── linkedin-job-crawler/      # Playwright LinkedIn scraping
│   ├── linkedin-job-scorer/       # AI relevance scoring
│   ├── linkedin-applicant/        # Easy Apply automation
│   ├── linkedin-tracker/          # CSV logging & status
│   └── linkedin-pipeline/        # Full orchestrator
└── data/                     # Runtime data (gitignored)
    ├── applications.csv
    ├── jobs_cache.json
    └── pipeline.log
```

---

## 🔐 Vault System

Your LinkedIn credentials are stored in `vault/secrets.yaml` — a local file that is **gitignored** and never leaves your machine.

During chat setup, the bot creates this file for you. You can also edit it manually:

```yaml
linkedin:
  email: "your-email@example.com"
  password: "your-password"
user_profile:
  name: "Your Name"
  email: "your-email@example.com"
  phone: "+1(555)123-4567"
  sponsorship_answer: "No"
```

---

## 💬 Chat Commands (After Setup)

Once running, you can chat with the linkedin agent anytime:

- **"Show my application stats"** — See how many jobs you've applied to
- **"Show flagged jobs"** — See big tech jobs waiting for manual application
- **"Run the pipeline now"** — Trigger an immediate application run
- **"Update my preferences"** — Change roles, locations, salary, etc.
- **"Pause applications"** — Disable the cron temporarily
- **"Resume applications"** — Re-enable the cron

---

## ⚠️ Important Notes

### LinkedIn Account Safety

- Default: **5 applications/hour** with human-like delays
- Conservative rate limiting to minimize detection risk
- **There is always some risk with automation.** LinkedIn may flag your account. Use at your own discretion.

### What This Bot Does NOT Do

- ❌ Auto-apply to big tech (flags them for you)
- ❌ Generate cover letters (skipped by default)
- ❌ Apply to contract/temporary roles
- ❌ Store your credentials in git

---

## 🤝 Contributing

PRs welcome! Keep the OpenClaw skill structure intact.

---

## 📜 License

MIT — Use responsibly. Don't spam recruiters. 💼
