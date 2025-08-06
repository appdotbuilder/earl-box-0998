import uuid
import mimetypes
from pathlib import Path
from typing import Optional
from fastapi import UploadFile
from sqlmodel import select
from datetime import datetime
from nicegui import events

from app.database import get_session
from app.models import UploadedFile, FileUploadStats

UPLOADS_DIR = Path("uploads")
MAX_FILE_SIZE = 300 * 1024 * 1024  # 300MB in bytes


def ensure_uploads_directory() -> None:
    """Create uploads directory if it doesn't exist."""
    UPLOADS_DIR.mkdir(exist_ok=True)


def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename to avoid conflicts."""
    file_extension = Path(original_filename).suffix
    unique_id = str(uuid.uuid4())
    return f"{unique_id}{file_extension}"


def get_file_stats() -> FileUploadStats:
    """Get statistics about uploaded files."""
    with get_session() as session:
        files = session.exec(select(UploadedFile)).all()
        total_files = len(files)
        total_size = sum(file.file_size for file in files)
        return FileUploadStats(total_files=total_files, total_size_bytes=total_size)


def save_upload_event(upload_event: events.UploadEventArguments) -> Optional[UploadedFile]:
    """Save uploaded file from NiceGUI upload event."""
    if upload_event.name is None:
        return None

    # Check file size
    content = upload_event.content.read()
    if len(content) > MAX_FILE_SIZE:
        return None

    ensure_uploads_directory()

    # Generate unique filename
    stored_filename = generate_unique_filename(upload_event.name)
    file_path = UPLOADS_DIR / stored_filename

    try:
        # Save file to disk
        with open(file_path, "wb") as f:
            f.write(content)

        # Determine content type
        content_type = upload_event.type or mimetypes.guess_type(upload_event.name)[0] or "application/octet-stream"

        # Create database record
        uploaded_file = UploadedFile(
            original_filename=upload_event.name,
            stored_filename=stored_filename,
            file_size=len(content),
            content_type=content_type,
            upload_timestamp=datetime.utcnow(),
            public_url=f"/files/{stored_filename}",
        )

        with get_session() as session:
            session.add(uploaded_file)
            session.commit()
            session.refresh(uploaded_file)
            return uploaded_file

    except Exception:
        import logging

        logging.exception(f"Failed to save uploaded file {upload_event.name}")
        # Clean up file if database operation fails
        if file_path.exists():
            file_path.unlink()
        return None


def save_uploaded_file(upload_file: UploadFile) -> Optional[UploadedFile]:
    """Save uploaded file and create database record."""
    if upload_file.filename is None:
        return None

    # Check file size
    content = upload_file.file.read()
    if len(content) > MAX_FILE_SIZE:
        return None

    ensure_uploads_directory()

    # Generate unique filename
    stored_filename = generate_unique_filename(upload_file.filename)
    file_path = UPLOADS_DIR / stored_filename

    try:
        # Save file to disk
        with open(file_path, "wb") as f:
            f.write(content)

        # Determine content type
        content_type = (
            upload_file.content_type or mimetypes.guess_type(upload_file.filename)[0] or "application/octet-stream"
        )

        # Create database record
        uploaded_file = UploadedFile(
            original_filename=upload_file.filename,
            stored_filename=stored_filename,
            file_size=len(content),
            content_type=content_type,
            upload_timestamp=datetime.utcnow(),
            public_url=f"/files/{stored_filename}",
        )

        with get_session() as session:
            session.add(uploaded_file)
            session.commit()
            session.refresh(uploaded_file)
            return uploaded_file

    except Exception:
        import logging

        logging.exception(f"Failed to save uploaded file {upload_file.filename}")
        # Clean up file if database operation fails
        if file_path.exists():
            file_path.unlink()
        return None


def get_file_path(stored_filename: str) -> Optional[Path]:
    """Get the file system path for a stored file."""
    file_path = UPLOADS_DIR / stored_filename
    if file_path.exists():
        return file_path
    return None


def get_all_uploaded_files() -> list[UploadedFile]:
    """Get all uploaded files from database."""
    with get_session() as session:
        from sqlmodel import desc

        return list(session.exec(select(UploadedFile).order_by(desc(UploadedFile.upload_timestamp))).all())


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size_float = float(size_bytes)
    while size_float >= 1024 and i < len(size_names) - 1:
        size_float /= 1024
        i += 1

    return f"{size_float:.1f} {size_names[i]}"
