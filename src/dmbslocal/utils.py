from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = REPO_ROOT / ".env.dashboard.local"


def load_env_file(env_file: Path) -> Dict[str, str]:
    env_vars: Dict[str, str] = {}
    if not env_file.exists():
        return env_vars

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            env_vars[key] = value
    return env_vars


def run(cmd: List[str], env: dict[str, str]) -> None:
    subprocess.run(cmd, cwd=REPO_ROOT, env=env, check=True)


def npm_cmd() -> str:
    # Windows can have issues resolving "npm" vs "npm.cmd"; prefer cmd explicitly.
    return shutil.which("npm.cmd") or shutil.which("npm.exe") or shutil.which("npm") or ""


def require_database_url(env: dict[str, str]) -> None:
    if not env.get("DATABASE_URL"):
        raise SystemExit(
            "DATABASE_URL is missing or empty. Set it in environment or in .env.dashboard.local."
        )


def env_with_defaults(env_file: Path | None) -> dict[str, str]:
    env = os.environ.copy()
    if env_file is not None:
        env.update(load_env_file(env_file))
    return env

