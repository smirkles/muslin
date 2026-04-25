"""Photo validation logic — no FastAPI imports.

Validates file size and MIME type via magic-byte sniff.
"""

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Magic byte signatures
_JPEG_MAGIC = bytes([0xFF, 0xD8, 0xFF])
_PNG_MAGIC = bytes([0x89, 0x50, 0x4E, 0x47])

# Allowed extensions mapped to their magic bytes
_ALLOWED: dict[str, bytes] = {
    ".jpg": _JPEG_MAGIC,
    ".jpeg": _JPEG_MAGIC,
    ".png": _PNG_MAGIC,
}


class PhotoValidationError(Exception):
    """Base class for photo validation errors."""


class PhotoTooLargeError(PhotoValidationError):
    """Raised when a photo exceeds the maximum allowed size."""


class PhotoInvalidTypeError(PhotoValidationError):
    """Raised when a photo is not a JPEG or PNG, or has mismatched magic bytes."""


def validate_photo(file_bytes: bytes, filename: str) -> None:
    """Validate file size and MIME type via magic-byte sniff.

    Checks size before MIME so a single error type is raised when both fail.
    Raises PhotoTooLargeError if size > 10 MB.
    Raises PhotoInvalidTypeError if extension or magic bytes are not JPEG/PNG.
    """
    # Size check first (spec: 413 before 415)
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise PhotoTooLargeError(
            f"File '{filename}' is {len(file_bytes) / (1024 * 1024):.1f} MB; "
            f"each photo must be under 10 MB."
        )

    # Extension check
    ext = _get_extension(filename)
    if ext not in _ALLOWED:
        raise PhotoInvalidTypeError(
            f"File '{filename}' has unsupported extension '{ext}'. "
            "Only JPEG and PNG files are accepted."
        )

    # Magic-byte sniff (read first 8 bytes)
    header = file_bytes[:8]
    expected_magic = _ALLOWED[ext]
    if not header[: len(expected_magic)] == expected_magic:
        # Check if it matches the OTHER allowed type (mismatched extension + magic)
        raise PhotoInvalidTypeError(
            f"File '{filename}' has a '{ext}' extension but its content does not match "
            "JPEG or PNG magic bytes. Only JPEG and PNG files are accepted."
        )


def _get_extension(filename: str) -> str:
    """Return the lowercase file extension including the dot."""
    dot_pos = filename.rfind(".")
    if dot_pos == -1:
        return ""
    return filename[dot_pos:].lower()
