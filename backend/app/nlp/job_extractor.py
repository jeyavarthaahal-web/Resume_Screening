"""Local, deterministic job description extraction. Unlabelled skill mentions default to preferred."""

import re
from typing import Any
from app.nlp.job_cleaner import clean_job_text
from app.nlp.job_section_detector import detect_job_sections

SKILLS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "Python": ("programming_language", "programming_languages", ("python",)),
    "Java": ("programming_language", "programming_languages", ("java",)),
    "JavaScript": ("programming_language", "programming_languages", ("javascript", "js")),
    "TypeScript": ("programming_language", "programming_languages", ("typescript", "ts")),
    "C++": ("programming_language", "programming_languages", ("c++",)), "C#": ("programming_language", "programming_languages", ("c#",)),
    "SQL": ("database", "databases", ("sql",)), "PostgreSQL": ("database", "databases", ("postgresql", "postgres")),
    "MySQL": ("database", "databases", ("mysql",)), "MongoDB": ("database", "databases", ("mongodb",)), "Redis": ("database", "databases", ("redis",)),
    "Machine Learning": ("technical", "technical_skills", ("machine learning", "ml")), "Natural Language Processing": ("technical", "technical_skills", ("natural language processing", "nlp")),
    "Deep Learning": ("technical", "technical_skills", ("deep learning",)), "Scikit-learn": ("framework", "frameworks", ("scikit-learn", "sklearn")),
    "TensorFlow": ("framework", "frameworks", ("tensorflow", "tf")), "PyTorch": ("framework", "frameworks", ("pytorch",)),
    "React": ("framework", "frameworks", ("react", "reactjs")), "Node.js": ("framework", "frameworks", ("node.js", "nodejs")),
    "Django": ("framework", "frameworks", ("django",)), "FastAPI": ("framework", "frameworks", ("fastapi",)), "Kubernetes": ("tool", "tools", ("kubernetes", "k8s")),
    "Docker": ("tool", "tools", ("docker",)), "Git": ("tool", "tools", ("git",)), "AWS": ("cloud_platform", "cloud_platforms", ("aws", "amazon web services")),
    "Azure": ("cloud_platform", "cloud_platforms", ("azure",)), "Google Cloud": ("cloud_platform", "cloud_platforms", ("google cloud", "gcp")),
    "Communication": ("soft_skill", "soft_skills", ("communication",)), "Leadership": ("soft_skill", "soft_skills", ("leadership",)),
    "Problem-solving": ("soft_skill", "soft_skills", ("problem-solving", "problem solving")), "Collaboration": ("soft_skill", "soft_skills", ("collaboration", "teamwork")),
}
CERTS = ("AWS Certified", "Azure certification", "Google Cloud certification", "PMP", "CISSP", "CPA")
CERT_PATTERNS = {"AWS Certified": r"aws\s+(?:certified|certification)", "Azure certification": r"azure\s+certification", "Google Cloud certification": r"google cloud\s+certification", "PMP": r"\bpmp\b", "CISSP": r"\bcissp\b", "CPA": r"\bcpa\b"}
BENEFITS = ("health insurance", "paid leave", "flexible work", "learning budget", "retirement benefits", "transportation", "dental insurance", "401(k)")

def _find_skills(text: str, importance: str) -> list[dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for canonical, (category, _bucket, aliases) in SKILLS.items():
        for alias in aliases:
            pattern = r"(?<![\w])" + re.escape(alias) + r"(?![\w])"
            match = re.search(pattern, text, re.I)
            if match:
                found[canonical] = {"name": canonical, "original_name": match.group(0), "category": category, "importance": importance}
                break
    return list(found.values())

def _experience(text: str) -> tuple[float | None, float | None]:
    low = high = None
    for m in re.finditer(r"(?:(?:at least|minimum(?: of)?|minimum)\s*)?(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", text, re.I):
        low, high = float(m.group(1)), float(m.group(2)); break
    if low is None:
        for m in re.finditer(r"(?:(?:at least|minimum(?: of)?|minimum)\s*)?(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)", text, re.I):
            low = float(m.group(1)); break
    if low is None:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s+(?:of\s+)?experience", text, re.I)
        if m: low = float(m.group(1))
    if low is None:
        for line in text.splitlines():
            if re.search(r"\bpreferred\b", line, re.I) and not re.search(r"\b(required|minimum|at least|must have)\b", line, re.I):
                continue
            m = re.search(r"\b(?:at least|minimum(?: of)?)\s+(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b", line, re.I)
            if m:
                low = float(m.group(1)); break
    if low is None and re.search(r"\b(?:entry[- ]level|freshers?|fresh graduates?|graduate role)\b", text, re.I): low = 0.0
    return low, high

def _education(text: str) -> dict[str, Any] | None:
    lower = text.casefold()
    degrees = [degree for degree, patterns in {"Bachelor's degree": ("bachelor", "b.tech", "b.e.", "b.sc"), "Master's degree": ("master", "m.tech", "mba"), "PhD": ("ph.d", "phd", "doctorate")}.items() if any(p in lower for p in patterns)]
    fields = [field for field in ("Computer Science", "Artificial Intelligence", "Data Science", "Information Technology") if field.casefold() in lower]
    if not degrees and not fields: return None
    level = "Doctorate" if "PhD" in degrees else "Master" if "Master's degree" in degrees else "Bachelor" if degrees else None
    return {"degree_level": level, "degrees": degrees, "fields": fields}

def extract_job_profile(text: str) -> dict[str, Any]:
    cleaned = clean_job_text(text)
    sections = detect_job_sections(cleaned)
    all_text = "\n".join(cleaned.splitlines())
    req_text = "\n".join(sections.get("required", []))
    pref_text = "\n".join(sections.get("preferred", []))
    skills_text = "\n".join(sections.get("skills", []))
    # Exact section context wins; sentence cues are applied to unlabelled prose.
    required = _find_skills(req_text, "required")
    preferred = _find_skills(pref_text, "preferred")
    present = {s["name"] for s in required + preferred}
    for item in _find_skills(skills_text, "preferred"):
        if item["name"] not in present: preferred.append(item); present.add(item["name"])
    for sentence in re.split(r"[\n.;]", all_text):
        cue = "required" if re.search(r"\b(required|must have|mandatory|essential|you must have)\b", sentence, re.I) else "preferred" if re.search(r"\b(preferred|nice to have|bonus|desirable|a plus)\b", sentence, re.I) else None
        if cue:
            for item in _find_skills(sentence, cue):
                if item["name"] not in present:
                    (required if cue == "required" else preferred).append(item); present.add(item["name"])
    opening = " ".join(sections.get("opening", []))
    title_line = next((x for x in sections.get("title", []) if x.strip()), None)
    title_line = title_line or next((x for x in sections.get("opening", []) if len(x) < 120 and not re.match(r"^(about|overview|we are)\b", x, re.I)), None)
    title_match = re.search(r"(?:job title|position|role)\s*:\s*([^\n|]+)", cleaned, re.I)
    title = (title_match.group(1).strip() if title_match else title_line)
    dept = re.search(r"(?:department|team)\s*:\s*([^\n|]+)", cleaned, re.I)
    loc = re.search(r"(?:location|based in)\s*:\s*([^\n|]+)", cleaned, re.I)
    location = loc.group(1).strip() if loc else None
    mode = "Remote" if re.search(r"\b(remote|work from home)\b", cleaned, re.I) else "Hybrid" if re.search(r"\bhybrid\b", cleaned, re.I) else "On-site" if re.search(r"\b(on.site|onsite)\b", cleaned, re.I) else None
    emp_pairs = (("full_time", r"full[ -]time"), ("part_time", r"part[ -]time"), ("internship", r"intern(ship)?"), ("contract", r"contract(or)?"), ("temporary", r"temporary"))
    employment = next((value for value, pat in emp_pairs if re.search(r"\b"+pat+r"\b", cleaned, re.I)), None)
    opening_summary = [line for line in sections.get("opening", []) if line != title_line and not re.match(r"^(?:department|team|location|based in|employment type|job type)\s*:", line, re.I)]
    summary_parts = sections.get("summary", []) or opening_summary
    summary = " ".join(summary_parts)[:1200] or None
    responsibilities = [re.sub(r"^(?:[-*•▪‣]|\d+[.)])\s*", "", x).strip() for x in sections.get("responsibilities", []) if x.strip()]
    if not responsibilities:
        responsibilities = [re.sub(r"^(?:[-*•▪‣]|\d+[.)])\s*", "", x).strip() for x in sections.get("opening", []) if re.match(r"^(?:[-*•▪‣]|\d+[.)])", x)]
    min_exp, max_exp = _experience(cleaned)
    education = _education(" ".join(sections.get("education", []) + sections.get("required", []))) or _education(cleaned)
    cert_text = "\n".join(sections.get("certifications", []) + sections.get("required", []) + sections.get("preferred", []))
    certifications = [{"name": cert, "importance": "required" if re.search(CERT_PATTERNS[cert], req_text, re.I) else "preferred"} for cert in CERTS if re.search(CERT_PATTERNS[cert], cert_text, re.I)]
    benefits_text = " ".join(sections.get("benefits", []))
    benefit_labels = {"health insurance": "Health insurance", "paid leave": "Paid leave", "flexible work": "Flexible work", "learning budget": "Learning budget", "retirement benefits": "Retirement benefits", "transportation": "Transportation", "dental insurance": "Dental insurance", "401(k)": "401(k)"}
    benefits = [benefit_labels[b] for b in BENEFITS if re.search(re.escape(b), benefits_text, re.I)]
    grouped: dict[str, list[str]] = {key: [] for key in ("technical_skills", "soft_skills", "tools", "frameworks", "programming_languages", "databases", "cloud_platforms")}
    for item in required + preferred:
        bucket = SKILLS[item["name"]][1]
        if item["name"] not in grouped[bucket]: grouped[bucket].append(item["name"])
    return {"job_title": title, "department": dept.group(1).strip() if dept else None, "location": location, "employment_type": employment, "work_mode": mode, "summary": summary,
        "responsibilities": responsibilities, "required_skills": required, "preferred_skills": preferred, **grouped,
        "minimum_experience": min_exp, "maximum_experience": max_exp, "education_requirement": education,
        "certifications": certifications, "benefits": benefits, "raw_description": text, "cleaned_description": cleaned,
        "classification_note": "Skills in explicit required/preferred sections or sentences follow that label. Skills in an unlabeled skills list default to preferred to avoid overstating a requirement."}
