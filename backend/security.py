"""Per-install session token that every API request must carry.

Why this exists: the backend listens on 127.0.0.1, but a web page open in the
user's browser can still send requests to localhost. CORS alone does not stop
that, because a sandboxed iframe sends `Origin: null`, which the packaged
Electron app also needs to allow. A secret token that only the JARVIS frontend
knows closes that gap: a foreign page cannot read the token, so every request
it makes is rejected with 401.

Token source, in order:
1. the JARVIS_TOKEN environment variable (set by Electron when it starts the backend);
2. the token file in the data directory, created on first run with owner-only permissions.
"""
from __future__ import annotations

import hmac
import os
import secrets
from pathlib import Path

TOKEN_HEADER = "x-jarvis-token"
TOKEN_FILENAME = ".jarvis_token"

# Requests that never need the token: CORS preflights and the plain liveness check.
PUBLIC_PATHS = {"/", "/docs", "/openapi.json", "/docs/oauth2-redirect"}


def data_dir() -> Path:
    path = Path(os.getenv("LOCALOS_DATA_DIR", str(Path(__file__).resolve().parent / "data")))
    path.mkdir(parents=True, exist_ok=True)
    return path


def token_file() -> Path:
    return data_dir() / TOKEN_FILENAME


def load_or_create_token() -> str:
    from_env = os.getenv("JARVIS_TOKEN", "").strip()
    if from_env:
        return from_env

    path = token_file()
    if path.exists():
        existing = path.read_text(encoding="utf-8").strip()
        if len(existing) >= 32:
            return existing

    token = secrets.token_hex(32)
    # Create with owner-only permissions where the OS supports it.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(token)
    return token


def is_authorized(provided: str | None, expected: str) -> bool:
    if not provided:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))
