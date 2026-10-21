"""Job document parsing reuses the bounded Task 4 PDF and DOCX parsers."""
from app.parsers.base import ParsedDocument
from app.parsers.docx_parser import DOCXResumeParser
from app.parsers.pdf_parser import PDFResumeParser

class JobDocumentParser:
    def parse(self, extension: str, file_bytes: bytes) -> ParsedDocument:
        if extension == ".pdf": return PDFResumeParser().parse(file_bytes)
        if extension == ".docx": return DOCXResumeParser().parse(file_bytes)
        raise ValueError("Upload a PDF or DOCX job description.")
