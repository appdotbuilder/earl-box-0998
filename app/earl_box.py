from nicegui import ui, events, app
from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.file_service import (
    save_upload_event,
    get_file_stats,
    get_file_path,
    get_all_uploaded_files,
    format_file_size,
    MAX_FILE_SIZE,
)


def create() -> None:
    """Create Earl Box application routes and UI."""

    @app.get("/files/{filename}")
    async def serve_file(filename: str):
        """Serve uploaded files publicly."""
        file_path = get_file_path(filename)
        if file_path is None:
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(file_path)

    @ui.page("/")
    def index():
        """Main Earl Box page."""
        # Apply modern theme
        ui.colors(
            primary="#2563eb",
            secondary="#64748b",
            accent="#10b981",
            positive="#10b981",
            negative="#ef4444",
            warning="#f59e0b",
            info="#3b82f6",
        )

        ui.add_head_html("""
        <style>
        .earl-gradient {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .upload-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        </style>
        """)

        # Header with gradient background
        with ui.row().classes("w-full earl-gradient p-8 text-white"):
            with ui.column().classes("w-full items-center"):
                ui.label("📦 Earl Box").classes("text-4xl font-bold mb-2")
                ui.label("Simple file sharing made easy").classes("text-xl opacity-90")

        # Main content area
        with ui.column().classes("w-full max-w-4xl mx-auto p-6 gap-6"):
            # Statistics card
            stats_container = ui.row().classes("w-full gap-4 mb-6")

            # Upload section
            with ui.card().classes("upload-card p-6 shadow-xl rounded-xl"):
                ui.label("Upload Files").classes("text-2xl font-bold text-gray-800 mb-4")
                ui.label(f"Maximum file size: {format_file_size(MAX_FILE_SIZE)}").classes("text-sm text-gray-600 mb-4")

                def handle_upload(e: events.UploadEventArguments) -> None:
                    """Handle file upload."""
                    try:
                        uploaded_file = save_upload_event(e)
                        if uploaded_file is None:
                            ui.notify("Failed to upload file. Check file size limit.", type="negative")
                        else:
                            ui.notify(
                                f'File "{uploaded_file.original_filename}" uploaded successfully!', type="positive"
                            )
                            refresh_stats()
                            refresh_files()
                    except Exception as ex:
                        import logging

                        logging.exception(f"Upload error for file {e.name}")
                        ui.notify(f"Upload error: {str(ex)}", type="negative")

                ui.upload(on_upload=handle_upload, max_file_size=MAX_FILE_SIZE).classes("w-full").props("color=primary")

            # Files list section
            files_container = ui.column().classes("w-full")

            def refresh_stats() -> None:
                """Refresh statistics display."""
                stats_container.clear()
                with stats_container:
                    stats = get_file_stats()

                    # Total files card
                    with ui.card().classes("p-6 bg-white shadow-lg rounded-xl hover:shadow-xl transition-shadow"):
                        ui.label("Total Files").classes("text-sm text-gray-500 uppercase tracking-wider")
                        ui.label(str(stats.total_files)).classes("text-3xl font-bold text-blue-600 mt-2")
                        ui.icon("folder").classes("text-blue-500 text-2xl")

                    # Total size card
                    with ui.card().classes("p-6 bg-white shadow-lg rounded-xl hover:shadow-xl transition-shadow"):
                        ui.label("Total Size").classes("text-sm text-gray-500 uppercase tracking-wider")
                        ui.label(format_file_size(stats.total_size_bytes)).classes(
                            "text-3xl font-bold text-green-600 mt-2"
                        )
                        ui.icon("storage").classes("text-green-500 text-2xl")

            def refresh_files() -> None:
                """Refresh files list display."""
                files_container.clear()
                with files_container:
                    files = get_all_uploaded_files()

                    if not files:
                        with ui.card().classes("p-6 text-center bg-gray-50 rounded-xl"):
                            ui.label("No files uploaded yet").classes("text-gray-500 text-lg")
                            ui.icon("cloud_upload").classes("text-gray-400 text-4xl mt-2")
                    else:
                        ui.label("Uploaded Files").classes("text-2xl font-bold text-gray-800 mb-4")

                        for file in files:
                            with ui.card().classes(
                                "p-4 bg-white shadow-md rounded-lg hover:shadow-lg transition-shadow"
                            ):
                                with ui.row().classes("w-full items-center justify-between"):
                                    with ui.column().classes("flex-1"):
                                        ui.label(file.original_filename).classes("font-semibold text-lg text-gray-800")
                                        with ui.row().classes("gap-4 mt-1"):
                                            ui.label(f"Size: {format_file_size(file.file_size)}").classes(
                                                "text-sm text-gray-600"
                                            )
                                            ui.label(
                                                f"Uploaded: {file.upload_timestamp.strftime('%Y-%m-%d %H:%M')}"
                                            ).classes("text-sm text-gray-600")

                                    with ui.row().classes("gap-2"):
                                        # Copy link button
                                        def copy_link(file_url: str):
                                            ui.run_javascript(f'''
                                                navigator.clipboard.writeText(window.location.origin + "{file_url}").then(() => {{
                                                    // Success case handled by JavaScript
                                                }});
                                            ''')
                                            ui.notify("Link copied to clipboard!", type="info")

                                        ui.button(
                                            "Copy Link",
                                            icon="link",
                                            on_click=lambda _, file_url=file.public_url: copy_link(file_url),
                                        ).classes("bg-blue-500 text-white px-4 py-2 rounded")

                                        # Direct link button
                                        ui.link("Open", file.public_url, new_tab=True).classes(
                                            "bg-green-500 text-white px-4 py-2 rounded no-underline"
                                        )

            # Initial load
            refresh_stats()
            refresh_files()

        # Footer
        with ui.row().classes("w-full bg-gray-800 text-white p-4 mt-8"):
            with ui.column().classes("w-full items-center"):
                ui.label("Created by Earl Store❤️").classes("text-lg font-medium")
