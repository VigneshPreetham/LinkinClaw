#!/usr/bin/env python3
"""
Resume PDF parser — extracts structured data from a PDF resume.
Uses pdftotext (poppler) for extraction, then structures via regex/heuristics.
"""

import argparse
import json
import logging
import re
import subprocess
import sys
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def extract_text(pdf_path: str) -> str:
    """Extract text from PDF using pdftotext."""
    result = subprocess.run(
        ["pdftotext", pdf_path, "-"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


def parse_contact(text: str) -> dict:
    """Extract contact information."""
    contact = {"name": "", "email": "", "phone": "", "website": "", "linkedin": "", "github": "", "scholar": ""}

    # Name — first non-empty line that looks like a name (2-4 capitalized words)
    for line in text.split("\n")[:10]:
        line = line.strip()
        if re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+", line) and len(line.split()) <= 5:
            contact["name"] = line
            break

    # Email
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    if email_match:
        contact["email"] = email_match.group()

    # Phone
    phone_match = re.search(r"\+?1?\s*\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", text)
    if phone_match:
        contact["phone"] = phone_match.group()

    # Website/portfolio
    web_match = re.search(r"([\w-]+\.github\.io[\w/.-]*)", text)
    if web_match:
        contact["website"] = web_match.group()

    # GitHub
    gh_match = re.search(r"github\.com/([\w-]+)", text)
    if gh_match:
        contact["github"] = f"github.com/{gh_match.group(1)}"

    # Google Scholar
    if "Google Scholar" in text or "scholar.google" in text:
        contact["scholar"] = "Google Scholar profile linked"

    return contact


def parse_sections(text: str) -> dict[str, str]:
    """Split text into named sections."""
    section_headers = [
        "EDUCATION", "EXPERIENCE", "TECHNICAL SKILLS", "SKILLS",
        "SELECT PUBLICATIONS", "PUBLICATIONS", "PROJECTS",
    ]
    sections = {}
    current = "header"
    current_text = []

    for line in text.split("\n"):
        stripped = line.strip().upper()
        matched = False
        for header in section_headers:
            if stripped == header or stripped.startswith(header):
                if current_text:
                    sections[current] = "\n".join(current_text)
                current = header.split()[0] if " " in header else header
                current_text = []
                matched = True
                break
        if not matched:
            current_text.append(line)

    if current_text:
        sections[current] = "\n".join(current_text)

    return sections


def parse_education(section: str) -> list[dict]:
    """Parse education entries."""
    entries = []
    lines = [l.strip() for l in section.split("\n") if l.strip()]

    i = 0
    while i < len(lines):
        # Look for university names
        if any(kw in lines[i] for kw in ["University", "Institute", "College"]):
            entry = {"school": lines[i], "degree": "", "gpa": "", "dates": "", "coursework": ""}

            # Look for dates nearby
            for j in range(max(0, i - 2), min(len(lines), i + 4)):
                date_match = re.search(r"(\d{4}\s*[–-]\s*(?:\d{4}|Present))", lines[j])
                if date_match:
                    entry["dates"] = date_match.group(1)

            # Look for degree/GPA in nearby lines
            for j in range(i, min(len(lines), i + 4)):
                if any(kw in lines[j] for kw in ["MS ", "BS ", "Bachelor", "Master", "Ph.D", "GPA"]):
                    entry["degree"] = lines[j]
                    gpa_match = re.search(r"GPA:\s*([\d.]+/[\d.]+)", lines[j])
                    if gpa_match:
                        entry["gpa"] = gpa_match.group(1)
                if "Coursework" in lines[j]:
                    entry["coursework"] = lines[j].split(":", 1)[-1].strip()

            entries.append(entry)
        i += 1

    return entries


def parse_experience(section: str) -> list[dict]:
    """Parse experience entries."""
    entries = []
    lines = section.split("\n")

    current_entry = None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Date pattern on its own line or at end
        date_match = re.search(
            r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}\s*[–-]\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}|Present))",
            stripped,
        )

        # Company name heuristic: line with known companies or capitalized words, no bullet
        is_bullet = stripped.startswith("•") or stripped.startswith("-")

        if date_match and not is_bullet:
            # This line has a date — could be company or role line
            if current_entry and not current_entry.get("dates"):
                current_entry["dates"] = date_match.group(1)
            continue

        # Location pattern
        loc_match = re.search(r"([\w\s]+,\s*(?:CA|WA|NY|TX|India|US|UK)[\w\s,]*)", stripped)

        if not is_bullet and len(stripped) > 3 and not stripped.startswith("("):
            # Could be company or role
            if current_entry is None or (current_entry.get("company") and current_entry.get("role")):
                # Start new entry
                if current_entry:
                    entries.append(current_entry)
                current_entry = {"company": stripped, "role": "", "dates": "", "location": "", "bullets": []}
                if date_match:
                    current_entry["dates"] = date_match.group(1)
            elif not current_entry.get("role"):
                current_entry["role"] = stripped
                if loc_match:
                    current_entry["location"] = loc_match.group(1).strip()
                if date_match:
                    current_entry["dates"] = date_match.group(1)
        elif is_bullet and current_entry:
            bullet_text = stripped.lstrip("•-").strip()
            if bullet_text:
                current_entry["bullets"].append(bullet_text)

    if current_entry:
        entries.append(current_entry)

    return entries


def parse_skills(section: str) -> list[str]:
    """Parse technical skills."""
    skills = []
    text = section.replace("\n", " ")

    # Common patterns: "Languages: X, Y, Z" or "Tools: A, B, C"
    for match in re.finditer(r"(?:Languages|Expertise|Tools and Frameworks|Tools|Frameworks|Skills):\s*([^\n]+)", text):
        items = [s.strip() for s in match.group(1).split(",")]
        skills.extend(items)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for s in skills:
        s_lower = s.lower()
        if s_lower not in seen and s:
            seen.add(s_lower)
            unique.append(s)

    return unique


def parse_publications(section: str) -> list[dict]:
    """Parse publications."""
    pubs = []
    lines = [l.strip() for l in section.split("\n") if l.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]
        # Publication title heuristic: longer line, not a venue
        if len(line) > 30 and not line.startswith("[") and not line.startswith("•"):
            pub = {"title": line, "venue": "", "year": "", "role": ""}

            # Check next lines for venue/role info
            for j in range(i + 1, min(len(lines), i + 4)):
                next_line = lines[j]
                if any(kw in next_line for kw in ["ICML", "ICLR", "NeurIPS", "CVPR", "Arxiv", "Springer", "Journal", "Workshop", "EACL"]):
                    pub["venue"] = next_line
                    year_match = re.search(r"20\d{2}", next_line)
                    if year_match:
                        pub["year"] = year_match.group()
                if any(kw in next_line.lower() for kw in ["first author", "second author", "co-first"]):
                    pub["role"] = next_line

            pubs.append(pub)
        i += 1

    return pubs


def parse_resume(pdf_path: str) -> dict:
    """Full resume parsing pipeline."""
    logger.info("Extracting text from %s", pdf_path)
    raw_text = extract_text(pdf_path)

    logger.info("Parsing contact info...")
    contact = parse_contact(raw_text)

    logger.info("Splitting into sections...")
    sections = parse_sections(raw_text)

    logger.info("Parsing education...")
    education = parse_education(sections.get("EDUCATION", ""))

    logger.info("Parsing experience...")
    experience = parse_experience(sections.get("EXPERIENCE", ""))

    logger.info("Parsing skills...")
    skills = parse_skills(sections.get("TECHNICAL", sections.get("SKILLS", "")))

    logger.info("Parsing publications...")
    publications = parse_publications(sections.get("SELECT", sections.get("PUBLICATIONS", "")))

    return {
        "contact": contact,
        "skills": skills,
        "experience": experience,
        "education": education,
        "publications": publications,
        "raw_text": raw_text,
    }


def main():
    parser = argparse.ArgumentParser(description="Parse resume PDF")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    pdf_path = config["paths"]["resume_pdf"]
    output_path = config["paths"]["parsed_resume"]

    if not Path(pdf_path).exists():
        logger.error("Resume not found: %s", pdf_path)
        sys.exit(1)

    parsed = parse_resume(pdf_path)

    with open(output_path, "w") as f:
        json.dump(parsed, f, indent=2)

    logger.info("Parsed resume saved to %s", output_path)
    logger.info("Contact: %s", parsed["contact"]["name"])
    logger.info("Skills: %d found", len(parsed["skills"]))
    logger.info("Experience: %d entries", len(parsed["experience"]))
    logger.info("Education: %d entries", len(parsed["education"]))
    logger.info("Publications: %d found", len(parsed["publications"]))


if __name__ == "__main__":
    main()
