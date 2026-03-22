#!/usr/bin/env python3
"""
Local vault UI server — serves a credential input page with masked password fields.
Writes directly to vault/secrets.yaml. Runs on localhost only, shuts down after save.
"""

import argparse
import json
import os
import signal
import sys
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import yaml

VAULT_PATH = ""
PORT = 0


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LinkinClaw — Secure Setup</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f0f0f;
    color: #e0e0e0;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 40px 20px;
  }
  .container {
    max-width: 560px;
    width: 100%;
  }
  h1 {
    font-size: 28px;
    margin-bottom: 8px;
    color: #fff;
  }
  .subtitle {
    color: #888;
    margin-bottom: 32px;
    font-size: 14px;
  }
  .section {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
  }
  .section h2 {
    font-size: 16px;
    color: #fff;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .field {
    margin-bottom: 16px;
  }
  .field:last-child {
    margin-bottom: 0;
  }
  label {
    display: block;
    font-size: 13px;
    color: #aaa;
    margin-bottom: 6px;
  }
  .input-wrap {
    position: relative;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  input, select {
    width: 100%;
    padding: 10px 14px;
    background: #0f0f0f;
    border: 1px solid #333;
    border-radius: 8px;
    color: #fff;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
  }
  input:focus, select:focus {
    border-color: #4a9eff;
  }
  .toggle-pw {
    flex-shrink: 0;
    width: 38px;
    height: 38px;
    background: #252525;
    border: 1px solid #333;
    border-radius: 8px;
    color: #666;
    cursor: pointer;
    font-size: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s, color 0.2s;
    order: -1;
  }
  .toggle-pw:hover {
    background: #333;
    color: #aaa;
  }
  .toggle-pw.active {
    background: #2a3a2a;
    color: #4ade80;
    border-color: #4ade80;
  }
  select {
    appearance: none;
    cursor: pointer;
  }
  .hint {
    font-size: 12px;
    color: #666;
    margin-top: 4px;
  }
  .divider {
    border: none;
    border-top: 1px solid #2a2a2a;
    margin: 16px 0;
  }
  .btn {
    width: 100%;
    padding: 14px;
    background: #4a9eff;
    color: #fff;
    border: none;
    border-radius: 10px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  }
  .btn:hover {
    background: #3a8eef;
  }
  .btn:disabled {
    background: #333;
    color: #666;
    cursor: not-allowed;
  }
  .success {
    display: none;
    text-align: center;
    padding: 40px;
  }
  .success h2 {
    color: #4ade80;
    font-size: 24px;
    margin-bottom: 12px;
  }
  .success p {
    color: #888;
  }
  .lock-icon {
    font-size: 14px;
    color: #4ade80;
  }
  .oauth-fields {
    display: none;
  }
  .pattern-example {
    font-family: monospace;
    font-size: 12px;
    color: #4a9eff;
    background: #1a1a2e;
    padding: 2px 6px;
    border-radius: 4px;
  }
</style>
</head>
<body>
<div class="container">
  <h1>💼 LinkinClaw Setup</h1>
  <p class="subtitle"><span class="lock-icon">🔒</span> All data is saved locally. Nothing is sent to any server.</p>

  <form id="form">
    <!-- LinkedIn Login -->
    <div class="section">
      <h2>🔗 LinkedIn Login</h2>
      <div class="field">
        <label>Login Method</label>
        <select id="login_method" onchange="toggleOAuth()">
          <option value="credentials">Email + Password</option>
          <option value="google_oauth">Sign in with Google</option>
          <option value="apple_oauth">Sign in with Apple</option>
        </select>
      </div>

      <div id="cred-fields">
        <div class="field">
          <label>LinkedIn Email</label>
          <input type="email" id="li_email" placeholder="you@example.com">
        </div>
        <div class="field">
          <label>LinkedIn Password</label>
          <div class="input-wrap">
            <input type="password" id="li_password" placeholder="••••••••">
            <button type="button" class="toggle-pw" title="Show password" onclick="togglePw('li_password', this)">👁</button>
          </div>
        </div>
      </div>

      <div id="google-fields" class="oauth-fields">
        <div class="field">
          <label>Google Email</label>
          <input type="email" id="google_email" placeholder="you@gmail.com">
        </div>
        <div class="field">
          <label>Google Password</label>
          <div class="input-wrap">
            <input type="password" id="google_password" placeholder="••••••••">
            <button type="button" class="toggle-pw" title="Show password" onclick="togglePw('google_password', this)">👁</button>
          </div>
        </div>
      </div>

      <div id="apple-fields" class="oauth-fields">
        <div class="field">
          <label>Apple ID Email</label>
          <input type="email" id="apple_email" placeholder="you@icloud.com">
        </div>
        <div class="field">
          <label>Apple ID Password</label>
          <div class="input-wrap">
            <input type="password" id="apple_password" placeholder="••••••••">
            <button type="button" class="toggle-pw" title="Show password" onclick="togglePw('apple_password', this)">👁</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Profile Info -->
    <div class="section">
      <h2>👤 Application Profile</h2>
      <div class="field">
        <label>Full Name</label>
        <input type="text" id="profile_name" placeholder="Jane Doe">
      </div>
      <div class="field">
        <label>Email (for applications)</label>
        <input type="email" id="profile_email" placeholder="you@example.com">
      </div>
      <div class="field">
        <label>Phone</label>
        <input type="tel" id="profile_phone" placeholder="+1(555)123-4567">
      </div>
      <div class="field">
        <label>LinkedIn URL (optional)</label>
        <input type="url" id="profile_linkedin" placeholder="https://linkedin.com/in/yourprofile">
      </div>
      <div class="field">
        <label>Portfolio / Website (optional)</label>
        <input type="url" id="profile_website" placeholder="https://yoursite.com">
      </div>
      <div class="field">
        <label>Do you need visa sponsorship?</label>
        <select id="sponsorship">
          <option value="No">No</option>
          <option value="Yes, I will require sponsorship now or in the future">Yes</option>
        </select>
      </div>
    </div>

    <!-- Portal Accounts -->
    <div class="section">
      <h2>🏢 External Job Portals</h2>
      <p style="font-size: 13px; color: #888; margin-bottom: 16px;">
        For jobs that require applying on the company's career site. Leave blank to skip (those jobs will be flagged for manual review).
      </p>
      <div class="field">
        <label>Email (same for all portals)</label>
        <input type="email" id="portal_email" placeholder="you@example.com">
        <p class="hint">Your regular email — used for all career site accounts.</p>
      </div>
      <div class="field">
        <label>Password Pattern</label>
        <div class="input-wrap">
          <input type="password" id="portal_password" placeholder="MySecure_{company}_2026!">
          <button type="button" class="toggle-pw" title="Show password" onclick="togglePw('portal_password', this)">👁</button>
        </div>
        <p class="hint">Use <span class="pattern-example">{company}</span> for per-company passwords, or a fixed password for all.</p>
      </div>
    </div>

    <button type="submit" class="btn" id="save-btn">🔒 Save to Vault</button>
  </form>

  <div class="success" id="success">
    <h2>✅ Saved!</h2>
    <p>Your credentials are stored securely in <code>vault/secrets.yaml</code>.</p>
    <p style="margin-top: 12px; color: #666;">You can close this tab and go back to chat.</p>
  </div>
</div>

<script>
function togglePw(id, btn) {
  const input = document.getElementById(id);
  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = '🙈';
    btn.classList.add('active');
    btn.title = 'Hide password';
  } else {
    input.type = 'password';
    btn.textContent = '👁';
    btn.classList.remove('active');
    btn.title = 'Show password';
  }
}

function toggleOAuth() {
  const method = document.getElementById('login_method').value;
  document.getElementById('cred-fields').style.display = method === 'credentials' ? 'block' : 'none';
  document.getElementById('google-fields').style.display = method === 'google_oauth' ? 'block' : 'none';
  document.getElementById('apple-fields').style.display = method === 'apple_oauth' ? 'block' : 'none';
}

document.getElementById('form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('save-btn');
  btn.disabled = true;
  btn.textContent = 'Saving...';

  const method = document.getElementById('login_method').value;

  const data = {
    linkedin: {
      login_method: method,
      email: document.getElementById('li_email').value,
      password: document.getElementById('li_password').value,
      google_oauth: {
        email: document.getElementById('google_email').value,
        password: document.getElementById('google_password').value,
      },
      apple_oauth: {
        email: document.getElementById('apple_email').value,
        password: document.getElementById('apple_password').value,
      },
    },
    user_profile: {
      name: document.getElementById('profile_name').value,
      email: document.getElementById('profile_email').value,
      phone: document.getElementById('profile_phone').value,
      linkedin_url: document.getElementById('profile_linkedin').value,
      website: document.getElementById('profile_website').value,
      sponsorship_answer: document.getElementById('sponsorship').value,
    },
    portal_accounts: {
      email: document.getElementById('portal_email').value,
      password_pattern: document.getElementById('portal_password').value,
      prefer_linkedin_apply: true,
    },
  };

  try {
    const res = await fetch('/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (res.ok) {
      document.getElementById('form').style.display = 'none';
      document.getElementById('success').style.display = 'block';
    } else {
      alert('Failed to save. Check the terminal for errors.');
      btn.disabled = false;
      btn.textContent = '🔒 Save to Vault';
    }
  } catch (err) {
    alert('Connection error: ' + err.message);
    btn.disabled = false;
    btn.textContent = '🔒 Save to Vault';
  }
});
</script>
</body>
</html>"""


class VaultHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode())

    def do_POST(self):
        if self.path == "/save":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                # Write to vault
                vault_dir = Path(VAULT_PATH).parent
                vault_dir.mkdir(parents=True, exist_ok=True)
                with open(VAULT_PATH, "w") as f:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode())

                print(f"\n✅ Vault saved to {VAULT_PATH}")
                # Shutdown after save
                threading.Thread(target=self.server.shutdown, daemon=True).start()

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress request logs


def main():
    global VAULT_PATH, PORT

    parser = argparse.ArgumentParser(description="LinkinClaw Vault UI")
    parser.add_argument("--vault", default="vault/secrets.yaml", help="Path to vault file")
    parser.add_argument("--port", type=int, default=0, help="Port (0 = auto)")
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    VAULT_PATH = str(Path(args.vault).resolve())

    server = HTTPServer(("127.0.0.1", args.port), VaultHandler)
    PORT = server.server_address[1]
    url = f"http://127.0.0.1:{PORT}"

    print(f"🔒 LinkinClaw Vault UI running at {url}")
    print(f"   Saving to: {VAULT_PATH}")
    print(f"   (Server shuts down automatically after save)\n")

    if not args.no_open:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("\n🔒 Vault server stopped.")


if __name__ == "__main__":
    main()
