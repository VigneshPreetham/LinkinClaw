---
name: linkedin-vault-ui
description: "Launch a local web UI for securely entering LinkedIn credentials and portal account patterns with masked password fields. Use when: the user needs to enter passwords or sensitive credentials during onboarding. Never ask for passwords in chat — always use this UI instead."
---

# Vault UI

A local web page for secure credential entry. Passwords are masked with show/hide toggles. Data writes directly to `vault/secrets.yaml`.

## Usage

```bash
python skills/linkedin-vault-ui/scripts/vault_server.py --vault vault/secrets.yaml
```

This:
1. Starts a local server on `127.0.0.1` (random port)
2. Opens the browser automatically
3. Shows a form with masked password fields for:
   - LinkedIn login (email/password, Google OAuth, or Apple OAuth)
   - Application profile (name, email, phone, etc.)
   - Portal account patterns (email + password templates)
4. On save, writes to `vault/secrets.yaml` and shuts down

## When to Use

**Always use this instead of asking for passwords in chat.** During bootstrap onboarding:

1. Collect non-sensitive info in chat (roles, locations, salary, etc.)
2. When it's time for credentials, launch this UI:
   ```bash
   python skills/linkedin-vault-ui/scripts/vault_server.py --vault vault/secrets.yaml
   ```
3. Tell the user: "I've opened a secure form in your browser — enter your credentials there. I'll know when you're done."
4. The server auto-shuts down after save, confirming the vault is written.

## Security

- Runs on `127.0.0.1` only (localhost, not exposed to network)
- Auto-shuts down after save (no lingering server)
- Passwords are masked by default with show/hide toggle
- No credentials pass through chat history
