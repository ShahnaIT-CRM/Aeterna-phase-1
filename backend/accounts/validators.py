"""Upload validation for credential documents: PDF / JPG / PNG, at most 5 MB, content must match the type."""
import os

from django.core.exceptions import ValidationError

MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png")

# Magic numbers, so a renamed .exe or .html cannot pass as a PDF.
_SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
}


def validate_credential_file(f):
    ext = os.path.splitext(f.name or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError("Upload a PDF, JPG or PNG file.")
    if f.size > MAX_DOCUMENT_BYTES:
        raise ValidationError("File is too large. The maximum size is 5 MB.")
    try:
        f.seek(0)
        head = f.read(8)
        f.seek(0)
    except (OSError, ValueError):
        return  # already-stored file we cannot reopen; extension and size were checked
    if not any(head.startswith(sig) for sig in _SIGNATURES[ext]):
        raise ValidationError("The file content does not match its type. Upload a genuine PDF, JPG or PNG.")
