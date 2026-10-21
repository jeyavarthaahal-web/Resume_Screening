"""Conservative text normalization that keeps line structure and technical punctuation."""

from collections import Counter
import re
import unicodedata


_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACE_RUN = re.compile(r"[ \t\u00a0\u2000-\u200a\u202f\u205f\u3000]+")
_DECORATION = re.compile(r"^[\W_]{4,}$", re.UNICODE)


def clean_resume_text(raw_text: str) -> str:
    text = unicodedata.normalize('NFKC', raw_text or '')
    text = text.replace('\u00ad', '').replace('\u200b', '').replace('\ufeff', '')
    text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\f', '\n')
    text = _CONTROL_CHARS.sub('', text)
    text = text.replace('\u2022', '•').replace('\u25cf', '•')

    lines: list[str] = []
    for raw_line in text.split('\n'):
        line = _SPACE_RUN.sub(' ', raw_line).strip()
        line = re.sub(r"^[•▪◦‣·]+\s*", '', line)
        line = re.sub(r"\s*[|]{2,}\s*", ' | ', line)
        if not line or _DECORATION.fullmatch(line):
            lines.append('')
            continue
        lines.append(line)

    # Repeated short lines occurring at least three times are likely page headers/footers.
    counts = Counter(line.casefold() for line in lines if line and len(line) <= 120)
    filtered = [line for line in lines if not (line and len(line) <= 120 and counts[line.casefold()] >= 3)]

    # Repair common PDF line-wrap artifacts without flattening section structure:
    # remove split-word hyphens and join only lowercase mid-sentence continuations.
    repaired: list[str] = []
    for line in filtered:
        if line:
            if repaired and repaired[-1] and re.search(r'[A-Za-z]-$', repaired[-1]) and line[:1].islower():
                repaired[-1] = repaired[-1][:-1] + line
            elif repaired and repaired[-1] and len(repaired[-1]) >= 45 and line[:1].islower() and repaired[-1][-1] not in '.!?;:':
                repaired[-1] = f'{repaired[-1]} {line}'
            else:
                repaired.append(line)
        elif repaired and repaired[-1] != '':
            repaired.append('')
    return '\n'.join(repaired).strip()
