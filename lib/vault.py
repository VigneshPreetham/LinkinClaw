"""
Vault — loads secrets from vault/secrets.yaml and merges with config.yaml.
Credentials never live in config.yaml.
"""

import sys
from pathlib import Path

import yaml


def load_config_with_vault(config_path: str = "config.yaml") -> dict:
    """
    Load config.yaml and merge in vault/secrets.yaml.
    Returns a single config dict with credentials populated.
    """
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Resolve vault path (relative to config file's directory)
    config_dir = Path(config_path).resolve().parent
    vault_path = config_dir / config.get("paths", {}).get("vault", "vault/secrets.yaml")

    if not vault_path.exists():
        print(f"⚠️  Vault not found at {vault_path}", file=sys.stderr)
        print(f"   Run: cp vault/secrets.example.yaml vault/secrets.yaml", file=sys.stderr)
        print(f"   Then fill in your credentials.", file=sys.stderr)
        sys.exit(1)

    with open(vault_path) as f:
        secrets = yaml.safe_load(f) or {}

    # Merge linkedin credentials
    if "linkedin" not in config:
        config["linkedin"] = {}
    if "linkedin" in secrets:
        config["linkedin"]["email"] = secrets["linkedin"].get("email", "")
        config["linkedin"]["password"] = secrets["linkedin"].get("password", "")

    # Merge user profile
    if "user_profile" not in config:
        config["user_profile"] = {}
    if "user_profile" in secrets:
        for key in ["name", "email", "phone", "linkedin_url", "website", "sponsorship_answer"]:
            if key in secrets["user_profile"]:
                config["user_profile"][key] = secrets["user_profile"][key]

    return config
