"""Common parser types for supported resume formats."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ParsedDocument:
    text: str
    page_count: int | None = None
    metadata: dict[str, str | int | float | None] = field(default_factory=dict)


class ResumeParser(Protocol):
    def parse(self, file_bytes: bytes) -> ParsedDocument:
        """Extract readable text and lightweight document metadata."""


class ResumeParserError(ValueError):
    """Safe, user-presentable parsing error."""
