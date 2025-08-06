from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class UploadedFile(SQLModel, table=True):
    """Model for tracking uploaded files in Earl Box application."""

    __tablename__ = "uploaded_files"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    original_filename: str = Field(max_length=255)
    stored_filename: str = Field(max_length=255, unique=True)
    file_size: int = Field(description="File size in bytes")
    content_type: str = Field(max_length=100)
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    public_url: str = Field(max_length=500, description="Public URL to access the file")


class FileUploadStats(SQLModel, table=False):
    """Schema for file upload statistics."""

    total_files: int
    total_size_bytes: int
