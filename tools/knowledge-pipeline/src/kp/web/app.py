from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from kp.web.routes import router

_STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(title="Knowledge Pipeline Review UI", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    app.include_router(router)
    return app


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Start the uvicorn server."""
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port, log_level="info")
