import pytest
from io import BytesIO
from fastapi import UploadFile
from fastapi.datastructures import Headers
from nicegui.testing import User
from nicegui import ui

from app.database import reset_db
from app.file_service import save_uploaded_file


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


def create_test_upload_file(filename: str, content: bytes) -> UploadFile:
    """Helper to create test upload file for testing."""
    return UploadFile(
        BytesIO(content),
        filename=filename,
        headers=Headers(raw=[(b"content-type", b"text/plain")]),
    )


class TestEarlBoxUI:
    """Test Earl Box user interface."""

    async def test_home_page_loads(self, user: User):
        """Test that the home page loads correctly."""
        await user.open("/")
        await user.should_see("Earl Box")
        await user.should_see("Simple file sharing made easy")
        await user.should_see("Created by Earl Store❤️")

    async def test_initial_stats_display(self, user: User, new_db):
        """Test initial statistics display with no files."""
        await user.open("/")
        await user.should_see("Total Files")
        await user.should_see("Total Size")
        await user.should_see("0")  # Should show 0 files initially

    async def test_upload_area_present(self, user: User):
        """Test that upload area is present."""
        await user.open("/")
        await user.should_see("Upload Files")
        await user.should_see("Maximum file size")
        # Check that upload component exists
        upload_elements = list(user.find(ui.upload).elements)
        assert len(upload_elements) > 0

    async def test_file_upload_success(self, user: User, new_db, temp_uploads):
        """Test successful file upload through UI."""
        await user.open("/")

        # Find upload component
        upload = user.find(ui.upload).elements.pop()

        # Simulate file upload
        test_upload = create_test_upload_file("test.txt", b"Hello Earl Box!")
        upload.handle_uploads([test_upload])

        # Should see success notification and updated stats
        await user.should_see("uploaded successfully")

        # Stats should be updated (wait a moment for UI refresh)
        await user.should_see("1")  # Should show 1 file

    async def test_files_list_with_uploads(self, user: User, new_db, temp_uploads):
        """Test files list display after uploading files."""
        # Pre-upload a file using service
        test_upload = create_test_upload_file("sample.txt", b"Sample content")
        uploaded_file = save_uploaded_file(test_upload)
        assert uploaded_file is not None

        await user.open("/")

        # Should see the uploaded file
        await user.should_see("Uploaded Files")
        await user.should_see("sample.txt")
        await user.should_see("Copy Link")
        await user.should_see("Open")

    async def test_empty_files_state(self, user: User, new_db):
        """Test display when no files are uploaded."""
        await user.open("/")
        await user.should_see("No files uploaded yet")

    async def test_file_size_display(self, user: User, new_db, temp_uploads):
        """Test file size formatting in UI."""
        # Upload file with known size
        content = b"x" * 1024  # 1KB content
        test_upload = create_test_upload_file("1kb.txt", content)
        uploaded_file = save_uploaded_file(test_upload)
        assert uploaded_file is not None

        await user.open("/")

        # Should see formatted file size
        await user.should_see("1.0 KB")

    async def test_multiple_files_upload(self, user: User, new_db, temp_uploads):
        """Test uploading multiple files."""
        # Pre-upload multiple files
        for i in range(3):
            test_upload = create_test_upload_file(f"file{i}.txt", f"Content {i}".encode())
            save_uploaded_file(test_upload)

        await user.open("/")

        # Should see all files and correct count
        await user.should_see("3")  # Total files count
        await user.should_see("file0.txt")
        await user.should_see("file1.txt")
        await user.should_see("file2.txt")

    async def test_upload_timestamp_display(self, user: User, new_db, temp_uploads):
        """Test that upload timestamp is displayed."""
        from datetime import datetime

        test_upload = create_test_upload_file("timestamped.txt", b"content")
        uploaded_file = save_uploaded_file(test_upload)
        assert uploaded_file is not None

        await user.open("/")

        # Should see timestamp (year at minimum)
        await user.should_see("Uploaded:")
        current_year = str(datetime.now().year)
        await user.should_see(current_year)  # Should contain current year
