#!/usr/bin/env python3
"""
Application tracker — manages the applications.csv log.
"""

import argparse
import csv
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CSV_HEADERS = [
    "date", "company", "role", "location", "url",
    "status", "method", "relevance_score", "reasoning", "notes",
]


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def ensure_csv(csv_path: str):
    """Create CSV with headers if it doesn't exist."""
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)


def log_results(config_path: str, results: list[dict]):
    """Log application results to CSV."""
    config = load_config(config_path)
    csv_path = config["paths"]["applications_csv"]
    ensure_csv(csv_path)

    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        for r in results:
            job = r.get("job", {})
            writer.writerow([
                r.get("timestamp", datetime.now().isoformat()),
                job.get("company", "Unknown"),
                job.get("title", "Unknown"),
                job.get("location", "Unknown"),
                job.get("url", ""),
                r.get("status", "unknown"),
                "easy_apply" if r.get("status") == "applied" else r.get("status", ""),
                r.get("score", 0),
                r.get("reasoning", ""),
                r.get("notes", ""),
            ])

    logger.info("Logged %d results to %s", len(results), csv_path)


def get_stats(config_path: str) -> str:
    """Generate stats report from CSV."""
    config = load_config(config_path)
    csv_path = config["paths"]["applications_csv"]

    if not Path(csv_path).exists():
        return "No applications logged yet."

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return "No applications logged yet."

    status_counts = {}
    companies = set()
    for row in rows:
        status = row.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        companies.add(row.get("company", ""))

    total = len(rows)
    report = [
        f"📊 Application Stats ({total} total, {len(companies)} companies)",
        "─" * 50,
    ]

    for status, count in sorted(status_counts.items()):
        pct = count / total * 100
        emoji = {
            "applied": "✅", "flagged_for_manual": "🏢", "external_application_needed": "🔗",
            "interview": "🎯", "rejected": "❌", "offer": "🎉", "error": "⚠️",
        }.get(status, "•")
        report.append(f"  {emoji} {status}: {count} ({pct:.0f}%)")

    # Recent applications (last 5)
    report.append("")
    report.append("Recent applications:")
    for row in rows[-5:]:
        report.append(f"  • {row.get('role', '?')} at {row.get('company', '?')} [{row.get('status', '?')}]")

    return "\n".join(report)


def update_status(config_path: str, url: str, new_status: str, notes: str = "") -> bool:
    """Update the status of an application by URL."""
    config = load_config(config_path)
    csv_path = config["paths"]["applications_csv"]

    if not Path(csv_path).exists():
        return False

    rows = []
    updated = False
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("url") == url:
                row["status"] = new_status
                if notes:
                    row["notes"] = notes
                updated = True
            rows.append(row)

    if updated:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            writer.writerows(rows)

    return updated


def get_flagged(config_path: str) -> list[dict]:
    """Get jobs flagged for manual application."""
    config = load_config(config_path)
    csv_path = config["paths"]["applications_csv"]

    if not Path(csv_path).exists():
        return []

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        return [row for row in reader if row.get("status") == "flagged_for_manual"]


def is_applied(config_path: str, url: str) -> bool:
    """Check if a URL has already been applied to."""
    config = load_config(config_path)
    csv_path = config["paths"]["applications_csv"]

    if not Path(csv_path).exists():
        return False

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        return any(row.get("url") == url for row in reader)


def main():
    parser = argparse.ArgumentParser(description="Application tracker")
    parser.add_argument("--config", default="config.yaml")
    sub = parser.add_subparsers(dest="command")

    # Log
    log_parser = sub.add_parser("log", help="Log application results")
    log_parser.add_argument("--results", required=True, help="Path to results JSON (or - for stdin)")

    # Stats
    sub.add_parser("stats", help="Show application statistics")

    # Update
    upd_parser = sub.add_parser("update", help="Update application status")
    upd_parser.add_argument("--url", required=True)
    upd_parser.add_argument("--status", required=True,
                            choices=["applied", "flagged_for_manual", "external_application_needed",
                                     "interview", "rejected", "offer"])
    upd_parser.add_argument("--notes", default="")

    # Flagged
    sub.add_parser("flagged", help="Show flagged jobs")

    # Check
    chk_parser = sub.add_parser("check", help="Check if URL already applied")
    chk_parser.add_argument("--url", required=True)

    args = parser.parse_args()

    if args.command == "log":
        if args.results == "-":
            results = json.load(sys.stdin)
        else:
            with open(args.results) as f:
                results = json.load(f)
        log_results(args.config, results)

    elif args.command == "stats":
        print(get_stats(args.config))

    elif args.command == "update":
        if update_status(args.config, args.url, args.status, args.notes):
            print(f"Updated: {args.url} → {args.status}")
        else:
            print(f"Not found: {args.url}")

    elif args.command == "flagged":
        flagged = get_flagged(args.config)
        if not flagged:
            print("No flagged applications.")
        else:
            print(f"\n🏢 Flagged for manual application ({len(flagged)} total):\n")
            for row in flagged:
                print(f"  {row.get('role', '?')} at {row.get('company', '?')}")
                print(f"    URL: {row.get('url', '?')}")
                print(f"    Score: {row.get('relevance_score', '?')}")
                print()

    elif args.command == "check":
        exists = is_applied(args.config, args.url)
        print("Already applied" if exists else "Not applied")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
