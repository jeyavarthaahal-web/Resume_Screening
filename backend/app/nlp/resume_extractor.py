"""Deterministic, explainable resume extraction for the Task 4 MVP."""

from collections import defaultdict
from datetime import datetime
import re
from typing import Iterable

from email_validator import EmailNotValidError, validate_email

from app.schemas.resume import (
    AchievementItem,
    CertificationItem,
    DetectedSections,
    EducationItem,
    ExperienceItem,
    LanguageItem,
    ProjectItem,
    ResumeProfile,
    Skills,
)

SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    'summary': ('summary', 'professional summary', 'profile', 'professional profile', 'objective', 'career objective', 'about me'),
    'education': ('education', 'academic background', 'education and qualifications', 'qualifications', 'academic qualifications'),
    'experience': ('experience', 'work experience', 'professional experience', 'employment', 'employment history', 'work history'),
    'skills': ('skills', 'technical skills', 'core competencies', 'competencies', 'areas of expertise'),
    'projects': ('projects', 'selected projects', 'personal projects', 'academic projects'),
    'certifications': ('certifications', 'certificates', 'licenses and certifications', 'courses'),
    'achievements': ('achievements', 'awards', 'honors', 'honours', 'publications', 'accomplishments'),
    'languages': ('languages', 'language proficiency', 'spoken languages'),
    'interests': ('interests', 'activities', 'volunteering', 'volunteer experience'),
}
_HEADING_LOOKUP = {alias: section for section, aliases in SECTION_ALIASES.items() for alias in aliases}
_MONTH = r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
_DATE = rf'(?:{_MONTH}\.?\s+\d{{4}}|\d{{1,2}}[/-]\d{{4}}|(?:19|20)\d{{2}}|present|current|now)'
_DATE_RANGE = re.compile(rf'(?P<start>{_DATE})\s*(?:-|–|—|to|through)\s*(?P<end>{_DATE})', re.IGNORECASE)
_SINGLE_DATE = re.compile(rf'(?<!\w){_DATE}(?!\w)', re.IGNORECASE)
_EMAIL = re.compile(r'(?<![\w.+-])[\w.!#$%&\'*+/=?^`{|}~-]+@[A-Z0-9-]+(?:\.[A-Z0-9-]+)+', re.IGNORECASE)
_PHONE = re.compile(r'(?<!\w)(?:\+\s*)?\d[\d\s()./-]{5,}\d(?!\w)')
_URL = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)

SKILL_ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    'programming_languages': {
        'Python': ('python',), 'Java': ('java',), 'JavaScript': ('javascript', 'js'), 'TypeScript': ('typescript',),
        'C++': ('c++',), 'C#': ('c#',), 'C': ('c',), 'Go': ('golang', 'go'), 'Rust': ('rust',), 'Kotlin': ('kotlin',),
        'Swift': ('swift',), 'PHP': ('php',), 'Ruby': ('ruby',), 'R': ('r',), 'Scala': ('scala',), 'Dart': ('dart',),
        'SQL': ('sql',), 'HTML': ('html',), 'CSS': ('css',), 'Bash': ('bash', 'shell scripting'), 'PowerShell': ('powershell',), 'MATLAB': ('matlab',),
    },
    'frameworks': {
        'React': ('react', 'react.js', 'reactjs'), 'Next.js': ('next.js', 'nextjs'), 'Angular': ('angular',),
        'Vue.js': ('vue.js', 'vuejs'), 'Node.js': ('node.js', 'nodejs'), 'Express': ('express.js', 'express'),
        'FastAPI': ('fastapi',), 'Django': ('django',), 'Flask': ('flask',), 'Spring': ('spring boot', 'spring'),
        'ASP.NET': ('asp.net',), '.NET': ('.net', 'dotnet'), 'TensorFlow': ('tensorflow',), 'PyTorch': ('pytorch',),
        'Scikit-learn': ('scikit-learn', 'sklearn'), 'Pandas': ('pandas',), 'NumPy': ('numpy',),
        'Machine Learning': ('machine learning', 'ml'), 'Natural Language Processing': ('natural language processing', 'nlp'),
    },
    'databases': {
        'PostgreSQL': ('postgresql', 'postgres'), 'MySQL': ('mysql',), 'SQLite': ('sqlite',), 'MongoDB': ('mongodb',),
        'Redis': ('redis',), 'Microsoft SQL Server': ('sql server', 'mssql'), 'Oracle Database': ('oracle database', 'oracle db'),
        'DynamoDB': ('dynamodb',), 'Supabase': ('supabase',), 'Firebase': ('firebase',),
    },
    'cloud': {
        'AWS': ('aws', 'amazon web services'), 'Microsoft Azure': ('microsoft azure', 'azure'),
        'Google Cloud': ('google cloud', 'gcp'), 'Cloudflare': ('cloudflare',),
    },
    'tools': {
        'Git': ('git',), 'GitHub': ('github',), 'GitLab': ('gitlab',), 'Docker': ('docker',), 'Kubernetes': ('kubernetes', 'k8s'),
        'Jenkins': ('jenkins',), 'Terraform': ('terraform',), 'Linux': ('linux',), 'Jira': ('jira',), 'Figma': ('figma',),
        'Power BI': ('power bi',), 'Tableau': ('tableau',), 'Apache Spark': ('apache spark', 'spark'),
        'Apache Kafka': ('apache kafka', 'kafka'), 'Microsoft Excel': ('microsoft excel', 'excel'),
    },
}
SOFT_SKILLS = ('communication', 'leadership', 'teamwork', 'collaboration', 'problem solving', 'adaptability', 'critical thinking', 'time management', 'project management', 'mentoring', 'presentation', 'stakeholder management')
HUMAN_LANGUAGES = ('English', 'Tamil', 'Hindi', 'Spanish', 'French', 'German', 'Mandarin', 'Chinese', 'Japanese', 'Korean', 'Arabic', 'Portuguese', 'Italian', 'Bengali', 'Telugu', 'Malayalam', 'Kannada', 'Marathi', 'Urdu', 'Russian', 'Dutch', 'Turkish', 'Punjabi', 'Sinhala', 'Nepali')
_DEGREE_TERMS = ('bachelor', 'b.tech', 'btech', 'b.e.', 'b.e ', 'b.sc', 'bsc', 'b.a.', 'ba ', 'master', 'm.tech', 'mtech', 'm.e.', 'm.sc', 'msc', 'm.a.', 'mba', 'ph.d', 'phd', 'doctorate', 'associate', 'diploma', 'high school', 'secondary school')
_INSTITUTION_TERMS = ('university', 'college', 'institute', 'school', 'academy')
_ACHIEVEMENT_WORDS = ('award', 'won ', 'winner', 'hackathon', 'ranked', 'rank ', 'scholarship', 'published', 'publication', 'finalist', 'first place', 'second place', 'recognition', 'honor', 'honour', 'achievement')


def _normalized_heading(line: str) -> str:
    value = re.sub(r'^\s*[•▪◦*-]+\s*', '', line.strip()).rstrip(':').strip().casefold()
    value = re.sub(r'\s*\((?:continued|cont\.?|page \d+)\)\s*$', '', value)
    value = value.replace('&', ' and ')
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()


def detect_sections(cleaned_text: str) -> dict[str, str]:
    """Return section body text keyed by canonical section name, independent of order."""
    lines = cleaned_text.splitlines()
    headings: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        normalized = _normalized_heading(line)
        section = _HEADING_LOOKUP.get(normalized)
        if section:
            headings.append((index, section, line.strip().rstrip(':')))
    sections: dict[str, list[str]] = defaultdict(list)
    for position, (line_index, section, _label) in enumerate(headings):
        end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        body = '\n'.join(lines[line_index + 1:end]).strip()
        if body:
            sections[section].append(body)
    return {key: '\n\n'.join(values) for key, values in sections.items()}


def _lines(section_text: str | None) -> list[str]:
    return [line.strip(' \t•▪◦*-') for line in (section_text or '').splitlines() if line.strip(' \t•▪◦*-')]


def _valid_email(text: str) -> str | None:
    match = _EMAIL.search(text)
    if not match:
        return None
    candidate = match.group(0).rstrip('.,;:')
    try:
        return validate_email(candidate, check_deliverability=False).normalized
    except EmailNotValidError:
        return None


def _extract_phone(text: str) -> str | None:
    for match in _PHONE.finditer(text):
        candidate = match.group(0).strip().rstrip('.,;:')
        if re.fullmatch(r'(?:19|20)\d{2}\s*[-–—/]\s*(?:19|20)\d{2}', candidate):
            continue
        digits = re.sub(r'\D', '', candidate)
        if 7 <= len(digits) <= 15:
            return re.sub(r'\s+', ' ', candidate)
    return None


def _extract_name(text: str) -> str | None:
    excluded = {'resume', 'curriculum vitae', 'cv', 'software engineer', 'data scientist', 'developer', 'engineer', 'student', 'profile'}
    for line in text.splitlines()[:12]:
        candidate = line.strip(' •\t')
        if not candidate or len(candidate) > 70 or '@' in candidate or _PHONE.search(candidate) or _URL.search(candidate):
            continue
        if _normalized_heading(candidate) in _HEADING_LOOKUP:
            continue
        if re.search(r'\d|[,;:|]', candidate):
            continue
        words = candidate.split()
        if not 2 <= len(words) <= 5 or candidate.casefold() in excluded:
            continue
        if all(word[0].isalpha() and all(char.isalpha() or char in "'’‑-" for char in word) for word in words):
            return ' '.join(word.title() if word.islower() else word for word in words)
    return None


def _extract_location(text: str) -> str | None:
    lines = text.splitlines()[:12]
    for line in lines:
        labeled = re.match(r'(?i)\s*(?:location|based in|address)\s*[:|-]\s*(.{2,100})$', line)
        if labeled:
            return labeled.group(1).strip()
    for line in lines:
        candidate = line.strip()
        if _URL.search(candidate) or _SINGLE_DATE.search(candidate):
            continue
        candidate = _EMAIL.sub('', candidate)
        candidate = _PHONE.sub('', candidate).strip(' |,;:-')
        if ',' in candidate and len(candidate) <= 80 and len(candidate.split()) <= 8:
            return candidate
    return None


def _date_range(line: str) -> tuple[str | None, str | None]:
    match = _DATE_RANGE.search(line)
    if match:
        return match.group('start').strip(), match.group('end').strip()
    tokens = list(_SINGLE_DATE.finditer(line))
    if len(tokens) >= 2:
        return tokens[0].group(0).strip(), tokens[1].group(0).strip()
    return None, None


def _record_chunks(text: str) -> list[list[str]]:
    lines = _lines(text)
    if not lines:
        return []
    paragraph_blocks = [[line for line in _lines(block)] for block in re.split(r'\n\s*\n', text) if _lines(block)]
    if not any(_date_range(line)[0] for block in paragraph_blocks for line in block):
        return paragraph_blocks
    chunks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        current.append(line)
        start, end = _date_range(line)
        if start and end:
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)
    return chunks


def _split_title_company(line: str) -> tuple[str | None, str | None]:
    parts = [part.strip(' -–—|,') for part in re.split(r'\s+(?:\|| at |—|–)\s*', line, maxsplit=2, flags=re.IGNORECASE) if part.strip(' -–—|,')]
    if len(parts) >= 2:
        return parts[0], parts[1]
    at_match = re.match(r'(.+?)\s+at\s+(.+)', line, re.IGNORECASE)
    if at_match:
        return at_match.group(1).strip(), at_match.group(2).strip()
    return (line.strip(), None) if line.strip() else (None, None)


def _parse_experience(section: str | None) -> list[ExperienceItem]:
    items: list[ExperienceItem] = []
    has_dated_ranges = any(_date_range(line)[0] for line in _lines(section or ''))
    for chunk in _record_chunks(section or ''):
        start = end = None
        date_index = None
        for index, line in enumerate(chunk):
            start, end = _date_range(line)
            if start and end:
                date_index = index
                break
        if date_index is None:
            if items and has_dated_ranges:
                trailing = ' '.join(chunk).strip()
                if trailing:
                    existing = items[-1].description
                    items[-1].description = f'{existing} {trailing}'.strip() if existing else trailing
            elif chunk:
                header = chunk[0]
                title, company = _split_title_company(header)
                details = ' '.join(chunk[1:]).strip() or None
                location = next((line for line in chunk[1:] if ',' in line), None)
                if location and details:
                    details = details.replace(location, '').strip() or None
                items.append(ExperienceItem(job_title=title, company=company, location=location, description=details))
            continue
        header_candidates = chunk[:date_index] or chunk[date_index + 1:]
        if not header_candidates:
            header_candidates = [_DATE_RANGE.sub('', chunk[date_index]).strip(' -–—|,')]
        header = next((line for line in header_candidates if not _SINGLE_DATE.search(line)), '')
        title, company = _split_title_company(header)
        location = next((line for line in chunk if ',' in line and not _SINGLE_DATE.search(line) and not _EMAIL.search(line)), None)
        description_lines = [line for i, line in enumerate(chunk) if i not in {date_index} and line != header and line != location]
        description = ' '.join(description_lines).strip() or None
        items.append(ExperienceItem(
            job_title=title,
            company=company,
            location=location,
            start_date=start,
            end_date=end,
            description=description,
        ))
    return items


def _parse_education(section: str | None) -> list[EducationItem]:
    items: list[EducationItem] = []
    for chunk in _record_chunks(section or ''):
        joined = ' '.join(chunk)
        start, end = None, None
        date_line = None
        for line in chunk:
            start, end = _date_range(line)
            if start and end:
                date_line = line
                break
        if not date_line:
            dates = list(_SINGLE_DATE.finditer(joined))
            if dates:
                start = dates[0].group(0)
                end = dates[1].group(0) if len(dates) > 1 else None
        content = [line for line in chunk if line != date_line and not _SINGLE_DATE.fullmatch(line)]
        degree_line = next((line for line in content if any(term in line.casefold() for term in _DEGREE_TERMS)), None)
        institution = next((line for line in content if any(term in line.casefold() for term in _INSTITUTION_TERMS)), None)
        field = None
        if degree_line:
            field_match = re.search(r'(?i)(?:in|of)\s+(.+)', degree_line)
            if field_match:
                field = field_match.group(1).strip(' ,.-')
        location = next((line for line in content if ',' in line and line != institution and line != degree_line), None)
        items.append(EducationItem(
            degree=degree_line,
            field_of_study=field,
            institution=institution,
            location=location,
            start_date=start,
            end_date=end,
        ))
    return items


def _month_index(value: str, is_end: bool) -> tuple[int, bool] | None:
    normalized = value.strip().casefold().rstrip('.')
    now = datetime.now()
    if normalized in {'present', 'current', 'now'}:
        return now.year * 12 + now.month, False
    month_match = re.fullmatch(rf'({_MONTH})\s+((?:19|20)\d{{2}})', normalized, re.IGNORECASE)
    if month_match:
        month_names = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
        month_prefix = month_match.group(1)[:3].lower()
        return int(month_match.group(2)) * 12 + month_names.index(month_prefix) + 1, False
    year_month = re.fullmatch(r'((?:19|20)\d{2})[-/](\d{1,2})', normalized)
    if year_month and 1 <= int(year_month.group(2)) <= 12:
        return int(year_month.group(1)) * 12 + int(year_month.group(2)), False
    month_year = re.fullmatch(r'(\d{1,2})[-/]((?:19|20)\d{2})', normalized)
    if month_year and 1 <= int(month_year.group(1)) <= 12:
        return int(month_year.group(2)) * 12 + int(month_year.group(1)), False
    year = re.fullmatch(r'(?:19|20)\d{2}', normalized)
    if year:
        return int(normalized) * 12 + (1 if not is_end else 1), True
    return None


def calculate_years_experience(experiences: Iterable[ExperienceItem]) -> float | None:
    """Approximate union of dated work intervals, avoiding overlap double-counting."""
    intervals: list[tuple[int, int, bool]] = []
    for experience in experiences:
        if not experience.start_date or not experience.end_date:
            continue
        start = _month_index(experience.start_date, False)
        end = _month_index(experience.end_date, True)
        if not start or not end or end[0] < start[0]:
            continue
        if start[1] and end[1]:
            # Year-only dates are imprecise; count the calendar-year difference, with
            # a small half-year estimate for an entry beginning and ending in one year.
            months = end[0] // 12 - start[0] // 12
            if months == 0:
                months = 6
            intervals.append((start[0], start[0] + months * 12, True))
        else:
            intervals.append((start[0], end[0], False))
    if not intervals:
        return None
    intervals.sort()
    merged: list[list[int]] = []
    for start, end, _year_precision in intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    months_total = sum(max(0, end - start) for start, end in merged)
    return round(months_total / 12, 1)


def _skill_pattern(alias: str) -> re.Pattern[str]:
    if alias.casefold() == 'c':
        return re.compile(r'(?<![\w])c(?![\w+#])', re.IGNORECASE)
    escaped = re.escape(alias)
    return re.compile(rf'(?<![\w]){escaped}(?![\w])', re.IGNORECASE)


def _extract_skills(text: str) -> Skills:
    categories: dict[str, list[str]] = {key: [] for key in SKILL_ALIASES}
    for category, skills in SKILL_ALIASES.items():
        for canonical, aliases in skills.items():
            if any(_skill_pattern(alias).search(text) for alias in aliases):
                categories[category].append(canonical)
    technical = list(dict.fromkeys(skill for values in categories.values() for skill in values))
    soft = [name.title() for name in SOFT_SKILLS if _skill_pattern(name).search(text)]
    return Skills(technical=technical, soft=soft, **categories)


def _extract_projects(section: str | None) -> list[ProjectItem]:
    projects: list[ProjectItem] = []
    chunks = _record_chunks(section or '')
    if section and not any(_DATE_RANGE.search(line) for line in _lines(section)):
        blocks = [[line for line in _lines(block)] for block in re.split(r'\n\s*\n', section) if _lines(block)]
        chunks = blocks or chunks
    for chunk in chunks:
        lines = [line for line in chunk if not _DATE_RANGE.search(line)]
        if not lines:
            continue
        title_line = lines[0]
        url = next((match.group(0).rstrip('.,') for line in lines for match in [_URL.search(line)] if match), None)
        technologies = _extract_skills(' '.join(lines)).technical
        role_match = re.match(r'(?i)role\s*[:|-]\s*(.+)', title_line)
        title = title_line.split(' - ', 1)[0].strip()
        description_lines = lines[1:]
        projects.append(ProjectItem(
            project_name=title or None,
            description=' '.join(description_lines).strip() or None,
            technologies=technologies,
            role=role_match.group(1).strip() if role_match else None,
            url=url,
        ))
    return projects


def _extract_certifications(section: str | None) -> list[CertificationItem]:
    certifications: list[CertificationItem] = []
    for line in _lines(section or ''):
        if _DATE_RANGE.search(line):
            continue
        parts = re.split(r'\s+(?:-|–|—|by)\s+', line, maxsplit=1, flags=re.IGNORECASE)
        credential = re.search(r'(?i)(?:credential\s*(?:id|#)?|certificate\s*(?:id|#)?)\s*[:#]\s*([\w-]+)', line)
        date = next((match.group(0) for match in _SINGLE_DATE.finditer(line)), None)
        issuer = parts[1].strip()[:200] if len(parts) > 1 else None
        if issuer and date:
            issuer = re.sub(re.escape(date), '', issuer, flags=re.IGNORECASE).strip(' -–—,') or None
        certifications.append(CertificationItem(
            certification_name=parts[0].strip()[:200],
            issuer=issuer,
            date=date,
            credential_id=credential.group(1) if credential else None,
        ))
    return certifications


def _extract_achievements(section: str | None) -> list[AchievementItem]:
    achievements: list[AchievementItem] = []
    for line in _lines(section or ''):
        if any(keyword in line.casefold() for keyword in _ACHIEVEMENT_WORDS):
            achievements.append(AchievementItem(title=line[:240]))
    return achievements


def _extract_languages(section: str | None) -> list[LanguageItem]:
    languages: dict[str, LanguageItem] = {}
    if not section:
        return []
    for line in _lines(section):
        for language in HUMAN_LANGUAGES:
            match = _skill_pattern(language).search(line)
            if not match:
                continue
            tail = line[match.end():].strip(' :,-–—()')
            proficiency_match = re.search(r'(?i)\b(native|fluent|professional|conversational|intermediate|beginner|basic|advanced|proficient)\b', tail)
            languages[language.casefold()] = LanguageItem(name=language, proficiency=proficiency_match.group(1).title() if proficiency_match else None)
    return list(languages.values())


def extract_resume_profile(cleaned_text: str) -> tuple[ResumeProfile, dict[str, str]]:
    sections = detect_sections(cleaned_text)
    email = _valid_email(cleaned_text)
    phone = _extract_phone(cleaned_text)
    experiences = _parse_experience(sections.get('experience'))
    education = _parse_education(sections.get('education'))
    skill_text = sections.get('skills') or cleaned_text
    profile = ResumeProfile(
        full_name=_extract_name(cleaned_text),
        email=email,
        phone=phone,
        location=_extract_location(cleaned_text),
        summary='\n'.join(_lines(sections.get('summary'))).strip() or None,
        years_experience=calculate_years_experience(experiences),
        education=education,
        experience=experiences,
        skills=_extract_skills(skill_text),
        projects=_extract_projects(sections.get('projects')),
        certifications=_extract_certifications(sections.get('certifications')),
        achievements=_extract_achievements(sections.get('achievements')),
        languages=_extract_languages(sections.get('languages')),
        sections=DetectedSections(
            summary='summary' in sections,
            education='education' in sections,
            experience='experience' in sections,
            skills='skills' in sections,
            projects='projects' in sections,
            certifications='certifications' in sections,
            achievements='achievements' in sections,
            languages='languages' in sections,
            other=[key for key in sections if key not in {'summary', 'education', 'experience', 'skills', 'projects', 'certifications', 'achievements', 'languages'}],
        ),
    )
    return profile, sections
