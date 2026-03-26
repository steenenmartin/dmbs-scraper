from __future__ import annotations

import argparse

from .utils import env_with_defaults, npm_cmd, run


def run_frontend() -> None:
    parser = argparse.ArgumentParser(
        prog="dmbs-frontend",
        description="Run dashboard frontend locally (Vite dev server).",
    )
    parser.add_argument("--host", default="localhost", help="Frontend host.")
    parser.add_argument("--port", type=int, default=5173, help="Frontend port.")
    args = parser.parse_args()

    # Frontend doesn't need DATABASE_URL directly.
    env = env_with_defaults(None)
    npm = npm_cmd()
    if not npm:
        raise SystemExit("npm was not found. Ensure Node.js is installed (where.exe npm).")

    run(
        [
            npm,
            "--prefix",
            "dashboard",
            "run",
            "dev",
            "-w",
            "dmbs-frontend",
            "--",
            "--host",
            args.host,
            "--port",
            str(args.port),
        ],
        env,
    )


if __name__ == "__main__":
    run_frontend()

