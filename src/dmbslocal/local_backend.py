from __future__ import annotations

import argparse
from pathlib import Path

from .utils import DEFAULT_ENV_FILE, env_with_defaults, npm_cmd, require_database_url, run


def run_backend() -> None:
    parser = argparse.ArgumentParser(
        prog="dmbs-backend",
        description="Run dashboard backend locally (watch mode).",
    )
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE, help="Path to env file.")
    parser.add_argument("--port", type=int, default=3001, help="Backend port.")
    args = parser.parse_args()

    env = env_with_defaults(args.env_file)
    env["PORT"] = str(args.port)  # command-line flag should override env file
    require_database_url(env)

    npm = npm_cmd()
    if not npm:
        raise SystemExit("npm was not found. Ensure Node.js is installed (where.exe npm).")

    run(["npm", "--prefix", "dashboard", "run", "dev", "-w", "dmbs-backend"], env)


if __name__ == "__main__":
    run_backend()

