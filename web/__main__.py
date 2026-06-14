"""Entry point: `audit-web` starts the FastAPI server."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import uvicorn


def main() -> None:
    """Start the audit web server on 127.0.0.1:8080 by default."""
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    print(f"audit-web starting on http://{host}:{port}")
    print(f"Open http://{host}:{port} in your browser")
    if host == "0.0.0.0":
        print("⚠️  Binding to 0.0.0.0 — accessible on all network interfaces")

    uvicorn.run(
        "web.app:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
