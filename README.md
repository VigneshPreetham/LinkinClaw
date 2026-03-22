# 🔗 LinkinClaw

**An OpenClaw-powered LinkedIn job application bot.** Finds, scores, and applies to jobs on LinkedIn — automatically.

Set up in 2 minutes. Everything happens through chat.

---

## 🚀 Setup

### 1. Install OpenClaw (skip if you already have it)

```bash
curl -fsSL https://get.openclaw.ai | bash && openclaw setup
```

### 2. Install LinkinClaw

Copy-paste this single command:

```bash
git clone https://github.com/VigneshPreetham/LinkinClaw.git ~/.openclaw/workspace-linkedin && openclaw agents add linkedin --workspace ~/.openclaw/workspace-linkedin && openclaw gateway restart
```

### 3. Open chat and talk to your bot

Open the OpenClaw web UI or run `openclaw tui`. Switch to the **linkedin** agent.

**The bot handles everything from here:**
- 📄 Upload your resume (drag & drop)
- 🎯 Tell it what jobs you want
- 🔑 Give it your LinkedIn login (stored locally, never in git)
- 🚀 It starts applying automatically

**No more terminal needed.**

---

## 💬 After Setup

Chat with the bot anytime to:
- Check application stats
- See flagged big tech jobs
- Trigger a run immediately
- Change preferences
- Pause or resume

---

## 🔐 Privacy

Your LinkedIn credentials are stored **only on your machine** in a gitignored vault file. They never touch GitHub.

---

## ⚠️ Disclaimer

LinkedIn may flag accounts using automation. Default settings are conservative (5 apps/hour with human-like delays), but use at your own risk.

---

MIT License — Use responsibly. 💼
