"""Upload validation with bounded memory, format checks, and safe filenames."""

from dataclasses import dataclass
from pathlib import PurePosixPath
import re
import unicodedata
from io import BytesIO
from zipfile import BadZipFile, ZipFile

MAX_RESUME_BYTES = 10 * 1024 * 1024
DOCX_MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
DOCX_MAX_ENTRIES = 2_000
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class UploadValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedResume:
    file_name: str
    file_type: str
    file_size: int
    extension: str


def sanitize_filename(filename: str | None) -> str:
    raw = unicodedata.normalize("NFKC", (filename or "").replace("\\", "/"))
    basename = PurePosixPath(raw).name
    basename = "".join(char for char in basename if unicodedata.category(char)[0] != "C")
    basename = re.sub(r"[^\w.() -]", "_", basename, flags=re.UNICODE).strip(" .")
    basename = re.sub(r"\s+", " ", basename)
    if not basename or basename in {".", ".."}:
        basename = "resume"
    if len(basename) > 180:
        suffix = PurePosixPath(basename).suffix[:10]
        basename = basename[: 180 - len(suffix)].rstrip(" .") + suffix
    return basename


def validate_resume_upload(filename: str | None, file_bytes: bytes) -> ValidatedResume:
    safe_name = sanitize_filename(filename)
    extension = PurePosixPath(safe_name).suffix.lower()
    if extension not in {".pdf", ".docx"}:
        raise UploadValidationError("Unsupported file type. Upload a PDF or DOCX resume.")
    if not file_bytes:
        raise UploadValidationError("The selected file is empty.")
    if len(file_bytes) > MAX_RESUME_BYTES:
        raise UploadValidationError("The file is too large. The maximum resume size is 10 MB.")

    if extension == ".pdf":
        if not file_bytes.startswith(b"%PDF-"):
            raise UploadValidationError("The file content does not look like a valid PDF.")
        return ValidatedResume(safe_name, "application/pdf", len(file_bytes), extension)

    if not file_bytes.startswith(b"PK\x03\x04"):
        raise UploadValidationError("The file content does not look like a valid DOCX document.")
    try:
        with ZipFile(BytesIO(file_bytes)) as archive:
            entries = archive.infolist()
            if len(entries) > DOCX_MAX_ENTRIES:
                raise UploadValidationError("This DOCX contains too many internal files to process safely.")
            total_size = sum(entry.file_size for entry in entries)
            if total_size > DOCX_MAX_UNCOMPRESSED_BYTES:
                raise UploadValidationError("This DOCX expands beyond the safe processing limit.")
            names = {entry.filename for entry in entries}
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise UploadValidationError("The file is not a valid DOCX document.")
            for entry in entries:
                if entry.file_size > 0 and entry.compress_size == 0:
                    raise UploadValidationError("This DOCX has an invalid compressed entry.")
                if entry.compress_size > 0 and entry.file_size / entry.compress_size > 250:
                    raise UploadValidationError("This DOCX uses an unsafe compression ratio.")
    except UploadValidationError:
        raise
    except (BadZipFile, OSError, ValueError):
        raise UploadValidationError("The DOCX archive is corrupt or unreadable.") from None
    return ValidatedResume(safe_name, DOCX_MIME, len(file_bytes), extension)
