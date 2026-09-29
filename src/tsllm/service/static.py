"""Built web UI under / with a single-page-application fallback."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response

from tsllm.service.errors import error_response


def mount_web(app: FastAPI, dist: Path) -> None:
    """Serve files from dist when dist/index.html exists. Unknown paths get index.html."""
    root = dist.resolve()
    index = root / "index.html"
    if not index.is_file():
        return

    @app.get("/{path:path}", include_in_schema=False)
    def web(path: str) -> Response:
        if path == "api" or path.startswith("api/"):
            return error_response(404, "NOT_FOUND", "Not Found")
        target = (root / path).resolve()
        if target.is_relative_to(root) and target.is_file():
            return FileResponse(target)
        return FileResponse(index)
