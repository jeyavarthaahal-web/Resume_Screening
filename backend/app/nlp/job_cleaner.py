"""Conservative cleaning for pasted or document-extracted job descriptions."""

import re
import unicodedata


def clean_job_text(raw_text: str) -> str:
    text = unicodedata.normalize("NFKC", raw_text or "")
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    text = "".join(ch if ch in "\n\r\t" or unicodedata.category(ch)[0] != "C" else " " for ch in text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    # Join wrapped prose lines, but preserve headings, bullets, and paragraph boundaries.
    out: list[str] = []
    for line in lines:
        if not line:
            if out and out[-1] != "": out.append("")
            continue
        is_bullet = bool(re.match(r"^(?:[-*•▪‣]|\d+[.)])\s+", line))
        if out and out[-1] and not is_bullet and not _looks_like_heading(line) and not _looks_like_heading(out[-1]):
            # Handle a common PDF wrap in the technical name Node.js.
            separator = "" if re.search(r"\bNode\.$", out[-1], re.I) and line.casefold().startswith("js") else " "
            out[-1] += separator + line
        else:
            out.append(line)
    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove duplicated standalone headers/footers without deleting repeated body terms.
    seen: set[str] = set()
    result: list[str] = []
    for line in text.splitlines():
        key = re.sub(r"\W+", " ", line.casefold()).strip()
        if key and len(line) < 100 and key in seen and not line.startswith(("-", "•", "*")):
            continue
        if key and len(line) < 100: seen.add(key)
        result.append(line)
    return "\n".join(result).strip()


def _looks_like_heading(line: str) -> bool:
    raw = line.strip()
    clean = raw.rstrip(":")
    return len(clean) < 120 and (raw.endswith(":") or clean.isupper() or bool(re.match(r"^(about|overview|summary|(?:key\s+)?responsibilities|requirements|qualifications|skills|education|experience|benefits|location|compensation|job title|department|employment type|position)\b", clean, re.I)))
