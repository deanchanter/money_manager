"""Environment configuration.

The .env file lives at the repository root, not inside backend/, and it is
gitignored -- which means a git worktree does NOT get a copy. Resolution walks
up from this file so the backend works regardless of the working directory it
was launched from.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent


def find_env_file() -> Path:
    """Nearest .env walking up from backend/.

    Walking all the way up matters for git worktrees: .env is gitignored, so a
    worktree has none of its own and the real one sits several levels above in
    the main checkout.
    """
    for directory in (BACKEND_DIR, *BACKEND_DIR.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
    return REPO_ROOT / ".env"


ENV_FILE = find_env_file()
load_dotenv(ENV_FILE)

# The setup token is written by hand; accept a couple of spellings since the
# SimpleFIN UI calls it different things in different places.
SETUP_TOKEN_KEYS = ("SIMPLEFIN_SETUP_TOKEN", "simpleFIN", "SIMPLEFIN", "SIMPLEFIN_TOKEN")
ACCESS_URL_KEY = "SIMPLEFIN_ACCESS_URL"


def get_setup_token() -> str | None:
    for key in SETUP_TOKEN_KEYS:
        value = os.getenv(key)
        if value and value.strip():
            return value.strip()
    return None


def get_access_url() -> str | None:
    value = os.getenv(ACCESS_URL_KEY)
    return value.strip() if value and value.strip() else None


def save_access_url(access_url: str) -> Path:
    """Persist a claimed access URL to .env.

    Setup tokens are single-use, so the claimed URL must outlive the database
    it gets written to -- otherwise resetting the DB (or discarding a worktree)
    costs a new token.
    """
    env_file = ENV_FILE
    env_file.parent.mkdir(parents=True, exist_ok=True)

    lines = env_file.read_text().splitlines() if env_file.is_file() else []
    replaced = False
    for index, line in enumerate(lines):
        if line.startswith(f"{ACCESS_URL_KEY}="):
            lines[index] = f"{ACCESS_URL_KEY}={access_url}"
            replaced = True
            break
    if not replaced:
        lines.append(f"{ACCESS_URL_KEY}={access_url}")

    env_file.write_text("\n".join(lines) + "\n")
    os.environ[ACCESS_URL_KEY] = access_url
    return env_file


def database_url() -> str:
    """Default the SQLite file to <repo>/data/, not the process working dir."""
    configured = os.getenv("DATABASE_URL")
    if configured:
        return configured
    data_dir = REPO_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{data_dir / 'money_manager.db'}"
