"""Entry point: `audit-web` starts the FastAPI server."""

from __future__ import annotations

import argparse
import logging
import sys

import uvicorn


def main() -> None:
    """Start the audit web server."""
    parser = argparse.ArgumentParser(description="Audit Web Server")
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Bind address (default: 127.0.0.1). Use 0.0.0.0 to expose on all interfaces.",
    )
    parser.add_argument(
        "--port", type=int, default=8080,
        help="Port to listen on (default: 8080)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    print(f"audit-web starting on http://{args.host}:{args.port}")
    print(f"Open http://{'127.0.0.1' if args.host == '0.0.0.0' else args.host}:{args.port} in your browser")
    if args.host == "0.0.0.0":
        print("⚠️  Binding to 0.0.0.0 — accessible on all network interfaces")

    uvicorn.run(
        "web.app:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
