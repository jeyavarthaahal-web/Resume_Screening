"""Text extraction for non-encrypted, text-based PDF resumes (no OCR)."""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.parsers.base import ParsedDocument, ResumeParserError

MAX_PDF_PAGES = 250
MAX_EXTRACTED_CHARS = 1_000_000


class PDFResumeParser:
    def parse(self, file_bytes: bytes) -> ParsedDocument:
        try:
            reader = PdfReader(BytesIO(file_bytes), strict=False)
            if reader.is_encrypted:
                raise ResumeParserError("This PDF is password-protected. Remove the password and upload it again.")
            page_count = len(reader.pages)
            if page_count > MAX_PDF_PAGES:
                raise ResumeParserError(f"This PDF has more than {MAX_PDF_PAGES} pages. Upload a shorter resume.")
            page_text: list[str] = []
            for page in reader.pages:
                try:
                    page_text.append(page.extract_text() or "")
                except Exception:
                    # A malformed page should not discard readable text from other pages.
                    page_text.append("")
            text = "\n\f\n".join(page_text)
            if len(text) > MAX_EXTRACTED_CHARS:
                raise ResumeParserError("The extracted PDF text is too large to process safely.")
            if not text.strip():
                raise ResumeParserError("Unable to extract text from this PDF. An image-only PDF is not supported yet.")
            return ParsedDocument(
                text=text,
                page_count=page_count,
                metadata={"title": reader.metadata.title if reader.metadata else None},
            )
        except ResumeParserError:
            raise
        except (PdfReadError, OSError, ValueError, KeyError) as error:
            raise ResumeParserError("This PDF could not be read. Make sure it is a valid, unencrypted PDF.") from error
        except Exception as error:
            raise ResumeParserError("Text could not be extracted from this PDF.") from error
