import os
from pathlib import Path


BASE_USER = Path(r"C:\Users\H")
PROJECT_ROOT = BASE_USER / "Desktop" / "jarvis-local"

ALLOWED_FOLDERS = {
    "desktop": BASE_USER / "Desktop",
    "downloads": BASE_USER / "Downloads",
    "documents": BASE_USER / "Documents",
    "jarvis": PROJECT_ROOT,
    "project": PROJECT_ROOT,
    "backend": PROJECT_ROOT / "backend",
    "frontend": PROJECT_ROOT / "frontend",
}

ALLOWED_COMMANDS = {
    "ollama list": {
        "command": "ollama list",
        "cwd": str(PROJECT_ROOT),
        "requires_confirmation": False,
    },
    "dir backend": {
        "command": "dir",
        "cwd": str(PROJECT_ROOT / "backend"),
        "requires_confirmation": False,
    },
    "dir frontend": {
        "command": "dir",
        "cwd": str(PROJECT_ROOT / "frontend"),
        "requires_confirmation": False,
    },
    "start frontend": {
        "command": "npm run dev",
        "cwd": str(PROJECT_ROOT / "frontend"),
        "requires_confirmation": True,
    },
    "start backend": {
        "command": r".\venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000",
        "cwd": str(PROJECT_ROOT / "backend"),
        "requires_confirmation": True,
    },
    "npm install": {
        "command": "npm install",
        "cwd": str(PROJECT_ROOT / "frontend"),
        "requires_confirmation": True,
    },
}


BLOCKED_PATH_KEYWORDS = [
    r"c:\windows",
    r"c:\program files",
    r"c:\program files (x86)",
    r"c:\users\h\appdata",
    r"system32",
    ".ssh",
    "id_rsa",
    "cookies",
    "password",
    "credentials",
    "token",
    "secret",
]


BLOCKED_COMMAND_KEYWORDS = [
    "del ",
    "erase ",
    "format",
    "shutdown",
    "restart-computer",
    "remove-item",
    "rm ",
    "rmdir",
    "reg ",
    "regedit",
    "powershell -enc",
    "invoke-expression",
    "curl ",
    "wget ",
    "taskkill",
    "net user",
    "cipher",
]


def normalize_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


def is_blocked_path(path: Path) -> bool:
    lowered = str(path).lower()
    return any(keyword in lowered for keyword in BLOCKED_PATH_KEYWORDS)


def is_path_allowed(path: str) -> bool:
    try:
        target = normalize_path(path)

        if is_blocked_path(target):
            return False

        for allowed_root in ALLOWED_FOLDERS.values():
            allowed = allowed_root.resolve()
            try:
                target.relative_to(allowed)
                return True
            except ValueError:
                continue

        return False
    except Exception:
        return False


def get_allowed_folder(name: str):
    key = name.strip().lower().replace("my ", "")
    folder = ALLOWED_FOLDERS.get(key)

    if not folder:
        return None

    return str(folder)


def is_command_blocked(command: str) -> bool:
    lowered = command.lower()
    return any(keyword in lowered for keyword in BLOCKED_COMMAND_KEYWORDS)


def get_allowed_command(command_name: str):
    key = command_name.strip().lower()
    return ALLOWED_COMMANDS.get(key)