from app.database import create_tables
from app.file_service import ensure_uploads_directory
import app.earl_box


def startup() -> None:
    # this function is called before the first request
    create_tables()
    ensure_uploads_directory()
    app.earl_box.create()
