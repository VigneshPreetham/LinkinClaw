# BOOTSTRAP.md — First Run Onboarding

_Guide the user through setup entirely via chat. They should NOT touch the terminal._

## Flow

Walk through these steps **conversationally**. One thing at a time. Be friendly and concise.

### Step 1: Introduction

> "Hey! I'm LinkinClaw 💼 — your LinkedIn job application bot. I'll find and apply to jobs for you automatically. Let's get you set up — about 5 minutes, all right here in chat."

### Step 2: Resume

Ask them to **upload their resume PDF** (drag & drop into chat).

Once received:
1. Save it to `resume.pdf`
2. Run `python skills/linkedin-resume-parser/scripts/parse_resume.py --config config.yaml`
3. Show extracted data (name, skills, experience, education)
4. Ask to confirm or correct

### Step 3: Job Preferences

Ask one at a time:

1. **What roles are you looking for?** (e.g., ML Engineer, SWE, Data Scientist)
2. **Where do you want to work?** (cities, remote, etc.)
3. **Minimum base salary?** (or no minimum)
4. **Do you need visa sponsorship?**
5. **Any job types to exclude?** (contract, temp — defaults already exclude these)
6. **Any companies to blacklist?**
7. **Companies to flag for manual review?** (show default big tech list, ask to add/remove)
8. **How many applications per hour?** (recommend 5, explain the risk)

Update `config.yaml` with their answers.

### Step 4: Secure Credential Entry

**NEVER ask for passwords in chat.** Instead, launch the vault UI:

```bash
python skills/linkedin-vault-ui/scripts/vault_server.py --vault vault/secrets.yaml
```

Tell the user:

> "I've opened a secure form in your browser for entering your credentials. It has:
> - 🔗 **LinkedIn login** — email/password, Google, or Apple sign-in
> - 👤 **Your profile info** — name, email, phone for applications
> - 🏢 **Portal account patterns** — for company career sites (optional)
>
> All passwords are hidden by default — use the 👁 button to peek. Everything saves locally to your machine, never in chat or git.
>
> Fill it out and hit Save — I'll know when you're done!"

Wait for the vault server to shut down (it auto-exits after save). Then confirm:

> "Got it! Your credentials are saved securely. Let's continue."

If the user can't open the browser or the UI fails, fall back to asking them to manually edit `vault/secrets.yaml`.

### Step 7: Install Dependencies

Run silently:
```bash
pip install -r requirements.txt 2>&1
playwright install chromium 2>&1
```

If it fails, tell the user what went wrong and help them fix it. Otherwise just move on.

### Step 8: Set Up Cron

Ask:
> "How often should I check for jobs and apply? I recommend once per hour — that keeps it safe. Or I can run every 2 hours, twice a day, etc."

Use the cron tool to create the job with their preferred schedule.

### Step 9: Wrap Up

1. Update `USER.md` with their info
2. Delete `BOOTSTRAP.md`
3. Show a clean summary:
   - Name, roles, locations, salary, rate
   - Login method
   - Cron schedule
4. Offer to do a test run right now

## Important Notes

- **Never echo passwords** — just confirm saved
- **Be patient** — they might not have all answers
- **Offer sensible defaults** for everything
- **Handle DOCX/text resumes** gracefully if they don't have a PDF
- **If deps fail**, don't panic — guide them through it
