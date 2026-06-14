"""FastAPI application factory and lifecycle management."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from web.run_manager import run_manager
from web.ws_manager import ws_manager

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle for the FastAPI application."""
    log.info("audit-web server starting")
    yield
    # Shutdown: cancel any active runs
    active = list(run_manager.get_active_runs())
    for run_id in active:
        log.info("shutdown: cancelling active run %s", run_id)
        run_manager.cancel(run_id)
    log.info("audit-web server stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Audit Web",
        description="Web interface for the 8-stage vulnerability discovery agent",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow local dev server (Vite) and same-origin
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and register routers FIRST (before static mount)
    from web.routers import auth, findings, report, runs, ws

    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(runs.router, prefix="/api", tags=["runs"])
    app.include_router(findings.router, prefix="/api", tags=["findings"])
    app.include_router(report.router, prefix="/api", tags=["report"])
    app.include_router(ws.router, prefix="/ws", tags=["websocket"])

    @app.get("/api/health")
    async def health():
        return {
            "status": "ok",
            "active_runs": list(run_manager.get_active_runs()),
            "ws_connections": len(ws_manager.active_runs),
        }

    # Serve static frontend in production — only for non-API paths.
    # Mount assets on /assets to avoid overriding API routes, then serve
    # index.html as a catch-all for SPA client-side routing.
    if STATIC_DIR.exists():
        assets_dir = STATIC_DIR / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="static_assets")

        index_html = STATIC_DIR / "index.html"
        favicon = STATIC_DIR / "favicon.svg"

        @app.get("/favicon.svg", include_in_schema=False)
        async def favicon_endpoint():
            if favicon.exists():
                return FileResponse(str(favicon))
            return HTMLResponse(status_code=404)

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(request: Request, full_path: str):
            """Serve index.html for all non-API, non-asset paths (SPA routing)."""
            # Let API routes handle their own paths — we only reach here for
            # paths that don't match any registered route.
            if index_html.exists():
                return FileResponse(str(index_html), media_type="text/html")
            return HTMLResponse(
                content="<h1>Frontend not built</h1><p>Run: cd web/frontend && npm run build</p>",
                status_code=404,
            )

        log.info("serving static frontend from %s", STATIC_DIR)

    return app


app = create_app()
