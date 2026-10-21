"""Case- and punctuation-tolerant JD heading detection."""

import re
from app.nlp.job_cleaner import clean_job_text

ALIASES = {
    "title": ("job title", "position", "role"),
    "summary": ("about the role", "about this role", "overview", "summary", "job description", "about us", "the opportunity"),
    "responsibilities": ("responsibilities", "key responsibilities", "what you'll do", "what you will do", "duties"),
    "required": ("requirements", "required qualifications", "required skills", "must have", "mandatory", "essential", "basic qualifications", "what you'll bring", "what you will bring"),
    "preferred": ("preferred qualifications", "preferred skills", "nice to have", "bonus", "a plus", "desirable"),
    "skills": ("skills", "technical skills", "technology stack", "technologies"),
    "education": ("education", "educational requirements", "academic qualifications"),
    "experience": ("experience", "work experience"),
    "certifications": ("certifications", "certificates"),
    "benefits": ("benefits", "perks", "what we offer", "compensation and benefits"),
    "location": ("location", "work location"),
    "employment_type": ("employment type", "job type"),
    "compensation": ("compensation", "salary", "pay"),
}

def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

def _section_for(line: str) -> str | None:
    key = _key(line.strip().rstrip(":"))
    for section, aliases in ALIASES.items():
        if key in {_key(a) for a in aliases}:
            return section
    return None

def detect_job_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {name: [] for name in ALIASES}
    current = "opening"
    sections[current] = []
    for raw in clean_job_text(text).splitlines():
        line = raw.strip()
        if not line: continue
        # Inline metadata headings (e.g. Location: Toronto) remain content.
        section = _section_for(line)
        if section:
            current = section
            continue
        sections.setdefault(current, []).append(line)
    return sections
