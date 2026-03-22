---
name: linkedin-resume-parser
description: "Parse a PDF resume into structured JSON (contact, skills, experience, education, publications). Use when: the agent needs to extract structured data from a resume PDF for job matching and application autofill."
---

# Resume Parser

Parse `Resume_Debapriya.pdf` (or configured resume path) into `parsed_resume.json`.

## Usage

Run the parser script:

```bash
python skills/linkedin-resume-parser/scripts/parse_resume.py --config config.yaml
```

## Output

Creates `parsed_resume.json` with structure:

```json
{
  "contact": { "name": "", "email": "", "phone": "", "website": "" },
  "skills": ["Python", "PyTorch", ...],
  "experience": [{ "company": "", "role": "", "dates": "", "bullets": [] }],
  "education": [{ "school": "", "degree": "", "gpa": "", "dates": "" }],
  "publications": [{ "title": "", "venue": "", "year": "", "role": "" }],
  "raw_text": "..."
}
```

## When to Run

- On first run (no `parsed_resume.json` exists)
- When resume PDF is updated
- The main pipeline calls this as step 1
