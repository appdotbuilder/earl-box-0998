import pytest
from io import BytesIO
from fastapi import UploadFile
from fastapi.datastructures import Headers

from app.database import reset_db
from app.file_service import (
    save_uploaded_file,
    get_file_stats,
    get_file_path,
    get_all_uploaded_files,
    format_file_size,
    generate_unique_filename,
    ensure_uploads_directory,
    MAX_FILE_SIZE,
)


@pytest.fixture()
def new_db():
    """Reset database for each test."""
    reset_db()
    yield
    reset_db()


@pytest.fixture()
def temp_uploads(tmp_path):
    """Use temporary directory for uploads during tests."""
    uploads_dir = tmp_path / "uploads"
    # Set the uploads directory for this test
    import app.file_service

    original_uploads_dir = app.file_service.UPLOADS_DIR
    app.file_service.UPLOADS_DIR = uploads_dir
    yield uploads_dir
    # Restore original directory
    app.file_service.UPLOADS_DIR = original_uploads_dir


def create_test_upload_file(filename: str, content: bytes, content_type: str = "text/plain") -> UploadFile:
    """Helper to create test upload file."""
    return UploadFile(
        BytesIO(content),
        filename=filename,
        headers=Headers(raw=[(b"content-type", content_type.encode())]),
    )


class TestFileService:
    """Test file service functionality."""

    def test_generate_unique_filename(self):
        """Test unique filename generation."""
        filename1 = generate_unique_filename("test.txt")
        filename2 = generate_unique_filename("test.txt")

        assert filename1 != filename2
        assert filename1.endswith(".txt")
        assert filename2.endswith(".txt")

    def test_ensure_uploads_directory(self, temp_uploads):
        """Test uploads directory creation."""
        # Directory should not exist initially
        assert not temp_uploads.exists()

        ensure_uploads_directory()

        # Directory should exist after calling function
        assert temp_uploads.exists()
        assert temp_uploads.is_dir()

    def test_format_file_size(self):
        """Test file size formatting."""
        assert format_file_size(0) == "0 B"
        assert format_file_size(512) == "512.0 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"

    def test_save_uploaded_file_success(self, new_db, temp_uploads):
        """Test successful file upload."""
        test_content = b"Hello, Earl Box!"
        upload_file = create_test_upload_file("test.txt", test_content)

        result = save_uploaded_file(upload_file)

        assert result is not None
        assert result.original_filename == "test.txt"
        assert result.file_size == len(test_content)
        assert result.content_type == "text/plain"
        assert result.public_url.startswith("/files/")

        # Check file was saved to disk
        file_path = temp_uploads / result.stored_filename
        assert file_path.exists()
        assert file_path.read_bytes() == test_content

    def test_save_uploaded_file_no_filename(self, new_db):
        """Test upload with no filename."""
        upload_file = UploadFile(BytesIO(b"content"))
        upload_file.filename = None

        result = save_uploaded_file(upload_file)

        assert result is None

    def test_save_uploaded_file_too_large(self, new_db):
        """Test upload file too large."""
        large_content = b"x" * (MAX_FILE_SIZE + 1)
        upload_file = create_test_upload_file("large.txt", large_content)

        result = save_uploaded_file(upload_file)

        assert result is None

    def test_get_file_stats_empty(self, new_db):
        """Test file stats with no files."""
        stats = get_file_stats()

        assert stats.total_files == 0
        assert stats.total_size_bytes == 0

    def test_get_file_stats_with_files(self, new_db, temp_uploads):
        """Test file stats with uploaded files."""
        # Upload first file
        content1 = b"File 1 content"
        upload1 = create_test_upload_file("file1.txt", content1)
        save_uploaded_file(upload1)

        # Upload second file
        content2 = b"File 2 content is longer"
        upload2 = create_test_upload_file("file2.txt", content2)
        save_uploaded_file(upload2)

        stats = get_file_stats()

        assert stats.total_files == 2
        assert stats.total_size_bytes == len(content1) + len(content2)

    def test_get_file_path_exists(self, temp_uploads):
        """Test getting path for existing file."""
        # Create test file
        test_file = temp_uploads / "test.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("content")

        result = get_file_path("test.txt")

        assert result == test_file

    def test_get_file_path_not_exists(self, temp_uploads):
        """Test getting path for non-existent file."""
        result = get_file_path("nonexistent.txt")

        assert result is None

    def test_get_all_uploaded_files(self, new_db, temp_uploads):
        """Test retrieving all uploaded files."""
        # Upload files
        upload1 = create_test_upload_file("first.txt", b"first")
        upload2 = create_test_upload_file("second.txt", b"second")

        save_uploaded_file(upload1)
        save_uploaded_file(upload2)

        files = get_all_uploaded_files()

        assert len(files) == 2
        # Should be ordered by upload timestamp descending
        assert files[0].original_filename == "second.txt"
        assert files[1].original_filename == "first.txt"

    def test_save_uploaded_file_different_content_types(self, new_db, temp_uploads):
        """Test saving files with different content types."""
        # Test image file
        image_upload = create_test_upload_file("image.jpg", b"fake_image_data", "image/jpeg")
        image_result = save_uploaded_file(image_upload)

        assert image_result is not None
        assert image_result.content_type == "image/jpeg"

        # Test binary file with unknown type
        binary_upload = create_test_upload_file("binary.dat", b"\x00\x01\x02", "application/octet-stream")
        binary_result = save_uploaded_file(binary_upload)

        assert binary_result is not None
        assert binary_result.content_type == "application/octet-stream"
