"""
Secure file validation for Quotation documents.
Guarantees file size limits, extension whitelisting, and deep magic-bytes inspection
to prevent executable uploads, path traversal, or file masquerading attacks.
"""

import hashlib
import io
import os
import re
import zipfile
from django.core.exceptions import ValidationError

# Maximum upload limit: 25 MB
MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
MIN_UPLOAD_SIZE_BYTES = 10  # 10 bytes minimum to reject empty/corrupt files

# Whitelist of allowed extensions
ALLOWED_EXTENSIONS = {
    'pdf': 'pdf',
    'xlsx': 'excel',
    'xls': 'excel',
    'png': 'image',
    'jpg': 'image',
    'jpeg': 'image',
}

# Standard MIME type mappings
MIME_TYPE_MAPPINGS = {
    'pdf': 'application/pdf',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'xls': 'application/vnd.ms-excel',
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
}

# Dangerous executable magic signatures (strictly forbidden)
DANGEROUS_SIGNATURES = [
    (b'MZ', 'Windows Executable/DLL'),
    (b'\x7fELF', 'Linux ELF Executable'),
    (b'#!', 'Unix Shell/Script'),
    (b'<?php', 'PHP Script'),
    (b'<script', 'HTML/JavaScript Script'),
]


def sanitize_filename(filename: str) -> str:
    """
    Strips path traversal attempts, directory separators, and control characters.
    Returns a clean base filename for display purposes only.
    """
    if not filename:
        return 'unnamed_document'

    # 1. Take base name only (strips / or \ or ../)
    clean_name = os.path.basename(filename)
    # 2. Strip non-printable / control characters
    clean_name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', clean_name)
    # 3. Strip dangerous characters
    clean_name = re.sub(r'[^\w\s\.\-_]', '', clean_name).strip()
    return clean_name or 'unnamed_document'


def get_file_extension(filename: str) -> str:
    """Extracts and lowercases the file extension without dot."""
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext


def validate_file_magic_bytes(file_obj, ext: str) -> str:
    """
    Reads the initial byte sequence of the file to verify its true format
    and prevent masquerading executables or malicious payloads.
    """
    # Read first 4096 bytes
    pos = file_obj.tell() if hasattr(file_obj, 'tell') else 0
    header = file_obj.read(4096)
    if hasattr(file_obj, 'seek'):
        file_obj.seek(pos)

    if len(header) < 4:
        raise ValidationError("Uploaded file is too small or corrupt.")

    # 1. Check for known dangerous executable headers
    for sig, label in DANGEROUS_SIGNATURES:
        if header.startswith(sig):
            raise ValidationError(f"File rejected: Detected {label} binary or script.")

    # 2. Strict format verification
    if ext == 'pdf':
        # PDF files must begin with '%PDF-'
        if not header.startswith(b'%PDF-'):
            raise ValidationError("File content does not match standard PDF header signature.")
        return 'application/pdf'

    elif ext == 'png':
        # PNG signature: \x89PNG\r\n\x1a\n
        if not header.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValidationError("File content does not match standard PNG header signature.")
        return 'image/png'

    elif ext in ('jpg', 'jpeg'):
        # JPEG signature: \xff\xd8\xff
        if not header.startswith(b'\xff\xd8\xff'):
            raise ValidationError("File content does not match standard JPEG header signature.")
        return 'image/jpeg'

    elif ext == 'xlsx':
        # XLSX is an OpenXML ZIP archive containing '[Content_Types].xml' or 'xl/'
        if not header.startswith(b'PK\x03\x04'):
            raise ValidationError("File content does not match Excel XLSX OpenXML archive signature.")

        # Deep check: verify it is a valid zip archive with excel parts
        try:
            zip_buffer = io.BytesIO(header if len(header) >= file_obj.size else file_obj.read())
            if hasattr(file_obj, 'seek'):
                file_obj.seek(pos)
            with zipfile.ZipFile(zip_buffer, 'r') as zf:
                namelist = zf.namelist()
                has_excel_parts = any(
                    name.startswith('xl/') or name == '[Content_Types].xml' for name in namelist
                )
                if not has_excel_parts:
                    raise ValidationError("ZIP archive does not contain required Excel spreadsheet structure.")
        except zipfile.BadZipFile:
            raise ValidationError("Invalid or corrupted Excel XLSX file archive.")
        return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    elif ext == 'xls':
        # Legacy Excel BIFF8 Compound File Binary Format signature
        if not header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
            raise ValidationError("File content does not match legacy Excel XLS binary signature.")
        return 'application/vnd.ms-excel'

    raise ValidationError(f"Unsupported file format '{ext}'.")


def compute_file_sha256(file_obj) -> str:
    """Computes SHA-256 digest of the uploaded file for deduplication and audit."""
    pos = file_obj.tell() if hasattr(file_obj, 'tell') else 0
    if hasattr(file_obj, 'seek'):
        file_obj.seek(0)

    hasher = hashlib.sha256()
    for chunk in file_obj.chunks() if hasattr(file_obj, 'chunks') else iter(lambda: file_obj.read(65536), b''):
        hasher.update(chunk)

    if hasattr(file_obj, 'seek'):
        file_obj.seek(pos)

    return hasher.hexdigest()


def validate_quotation_document_file(file_obj) -> dict:
    """
    Performs comprehensive security and integrity validation on an uploaded file.
    Returns validated metadata dictionary.
    """
    if not file_obj:
        raise ValidationError("No file provided for upload.")

    # 1. Size checks
    file_size = getattr(file_obj, 'size', None)
    if file_size is None and hasattr(file_obj, 'seek'):
        file_obj.seek(0, os.SEEK_END)
        file_size = file_obj.tell()
        file_obj.seek(0)

    if file_size > MAX_UPLOAD_SIZE_BYTES:
        max_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise ValidationError(f"File size exceeds maximum limit of {max_mb} MB.")

    if file_size < MIN_UPLOAD_SIZE_BYTES:
        raise ValidationError("File size is too small or file is empty.")

    # 2. Extension whitelist check
    clean_name = sanitize_filename(getattr(file_obj, 'name', 'document'))
    ext = get_file_extension(clean_name)
    if not ext or ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(ALLOWED_EXTENSIONS.keys())
        raise ValidationError(
            f'File extension ".{ext}" is not permitted. Allowed extensions are: {allowed}.'
        )

    file_category = ALLOWED_EXTENSIONS[ext]

    # 3. Magic bytes inspection
    mime_type = validate_file_magic_bytes(file_obj, ext)

    # 4. Compute SHA-256
    checksum = compute_file_sha256(file_obj)

    return {
        'original_filename': clean_name,
        'file_extension': ext,
        'file_type': file_category,
        'file_size': file_size,
        'mime_type': mime_type,
        'checksum_sha256': checksum,
    }
