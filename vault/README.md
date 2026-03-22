# 🔐 Vault

This directory stores your **private credentials**. Only `secrets.example.yaml` is committed to git.

## Setup

```bash
cp secrets.example.yaml secrets.yaml
```

Then edit `secrets.yaml` with your real credentials.

## Security

- `secrets.yaml` is **gitignored** — it never leaves your machine
- Do not rename it or move it outside this directory
- The bot reads from `vault/secrets.yaml` at runtime
- If you accidentally commit secrets, rotate your LinkedIn password immediately

## What's stored here

| File | Committed? | Purpose |
|------|-----------|---------|
| `secrets.example.yaml` | ✅ Yes | Template showing required fields |
| `secrets.yaml` | ❌ No | Your actual credentials |
