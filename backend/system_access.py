import os
import subprocess
from pathlib import Path
from datetime import datetime

from permissions import (
    is_path_allowed,
    get_allowed_folder,
    get_allowed_command,
    is_command_blocked,
)
from confirmation_store import (
    create_pending_action,
    pop_pending_action,
    list_pending_actions,
)


AUDIT_LOG = str(Path(__file__).resolve().parent / "data" / "audit_log.txt")


def audit(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    Path(AUDIT_LOG).parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {message}\n")


def list_allowed_folders():
    from permissions import ALLOWED_FOLDERS

    return {
        "status": "success",
        "mode": "folders_only",
        "message": "These are the folders I can access.",
        "folders": {key: str(value) for key, value in ALLOWED_FOLDERS.items()},
    }


def resolve_folder_or_path(folder_or_path: str):
    cleaned = folder_or_path.strip().lower().replace("my ", "")
    known = get_allowed_folder(cleaned)

    if known:
        return known

    return folder_or_path.strip().strip('"')


def list_files(folder_or_path: str, limit: int = 80):
    path = resolve_folder_or_path(folder_or_path)

    if not is_path_allowed(path):
        return {
            "status": "error",
            "message": "Access denied. This folder is not in the allowed list.",
        }

    target = Path(path)

    if not target.exists():
        return {
            "status": "error",
            "message": f"Folder does not exist: {target}",
        }

    if not target.is_dir():
        return {
            "status": "error",
            "message": f"Not a folder: {target}",
        }

    folders = []
    files = []

    for item in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        if len(folders) + len(files) >= limit:
            break

        if item.is_dir():
            folders.append(
                {
                    "name": item.name,
                    "type": "folder",
                    "path": str(item),
                }
            )
        else:
            files.append(
                {
                    "name": item.name,
                    "type": "file",
                    "path": str(item),
                    "size_bytes": item.stat().st_size,
                    "extension": item.suffix,
                }
            )

    audit(f"Listed filenames only in {target}")

    return {
        "status": "success",
        "mode": "list_only",
        "message": "LIST_ONLY_MODE: Only filenames and folder names are shown. File contents were not read.",
        "folder": str(target),
        "folders": folders,
        "files": files,
        "total_shown": len(folders) + len(files),
    }


def read_file(path: str, max_chars: int = 6000):
    cleaned_path = path.strip().strip('"')

    if not is_path_allowed(cleaned_path):
        return {
            "status": "error",
            "message": "Access denied. This file is outside allowed folders.",
        }

    target = Path(cleaned_path)

    if not target.exists():
        return {
            "status": "error",
            "message": f"File does not exist: {target}",
        }

    if not target.is_file():
        return {
            "status": "error",
            "message": f"Not a file: {target}",
        }

    try:
        content = target.read_text(encoding="utf-8", errors="ignore")
        audit(f"Read file contents from {target}")

        return {
            "status": "success",
            "mode": "read_contents",
            "message": f"Read file contents from {target}.",
            "path": str(target),
            "content": content[:max_chars],
            "truncated": len(content) > max_chars,
        }
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def search_files(folder_or_path: str, query: str, limit: int = 30):
    path = resolve_folder_or_path(folder_or_path)

    if not is_path_allowed(path):
        return {
            "status": "error",
            "message": "Access denied. This folder is outside allowed folders.",
        }

    root = Path(path)

    if not root.exists() or not root.is_dir():
        return {
            "status": "error",
            "message": f"Folder not found: {root}",
        }

    matches = []
    q = query.lower()

    searchable_extensions = [
        ".txt",
        ".md",
        ".py",
        ".tsx",
        ".ts",
        ".js",
        ".css",
        ".json",
    ]

    for current_root, dirs, files in os.walk(root):
        if len(matches) >= limit:
            break

        current_path = Path(current_root)

        if not is_path_allowed(str(current_path)):
            continue

        for file in files:
            if len(matches) >= limit:
                break

            file_path = current_path / file

            if q in file.lower():
                matches.append(
                    {
                        "name": file,
                        "path": str(file_path),
                        "match_type": "filename",
                    }
                )
                continue

            if file_path.suffix.lower() in searchable_extensions:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if q in content.lower():
                        matches.append(
                            {
                                "name": file,
                                "path": str(file_path),
                                "match_type": "content",
                            }
                        )
                except Exception:
                    pass

    audit(f"Searched {root} for {query}")

    return {
        "status": "success",
        "message": f"Search complete for '{query}' inside {root}.",
        "query": query,
        "folder": str(root),
        "matches": matches,
    }


def write_file_request(path: str, content: str):
    cleaned_path = path.strip().strip('"')

    if not is_path_allowed(cleaned_path):
        return {
            "status": "error",
            "message": "Access denied. This file is outside allowed folders.",
        }

    action = create_pending_action(
        "write_file",
        {
            "path": cleaned_path,
            "content": content,
        },
    )

    return {
        "status": "needs_confirmation",
        "message": (
            "I can write this file, but confirmation is required.\n\n"
            f"Action ID: {action['action_id']}\n"
            f"File: {cleaned_path}\n\n"
            f"Type: confirm {action['action_id']}"
        ),
        "action_id": action["action_id"],
    }


def append_file_request(path: str, content: str):
    cleaned_path = path.strip().strip('"')

    if not is_path_allowed(cleaned_path):
        return {
            "status": "error",
            "message": "Access denied. This file is outside allowed folders.",
        }

    action = create_pending_action(
        "append_file",
        {
            "path": cleaned_path,
            "content": content,
        },
    )

    return {
        "status": "needs_confirmation",
        "message": (
            "I can append to this file, but confirmation is required.\n\n"
            f"Action ID: {action['action_id']}\n"
            f"File: {cleaned_path}\n\n"
            f"Type: confirm {action['action_id']}"
        ),
        "action_id": action["action_id"],
    }


def run_command_request(command_name: str):
    command_info = get_allowed_command(command_name)

    if not command_info:
        return {
            "status": "error",
            "message": "Command not allowed. Use an approved command only.",
        }

    command = command_info["command"]

    if is_command_blocked(command):
        return {
            "status": "error",
            "message": "Command blocked for safety.",
        }

    if command_info.get("requires_confirmation", True):
        action = create_pending_action(
            "run_command",
            {
                "command": command,
                "cwd": command_info["cwd"],
            },
        )

        return {
            "status": "needs_confirmation",
            "message": (
                "I can run this command, but confirmation is required.\n\n"
                f"Action ID: {action['action_id']}\n"
                f"Command: {command}\n"
                f"Folder: {command_info['cwd']}\n\n"
                f"Type: confirm {action['action_id']}"
            ),
            "action_id": action["action_id"],
        }

    return execute_command(command, command_info["cwd"])


def execute_command(command: str, cwd: str):
    if is_command_blocked(command):
        return {
            "status": "error",
            "message": "Command blocked for safety.",
        }

    if not is_path_allowed(cwd):
        return {
            "status": "error",
            "message": "Command folder is not allowed.",
        }

    try:
        if "npm run dev" in command or "uvicorn" in command:
            subprocess.Popen(
                command,
                cwd=cwd,
                shell=True,
                creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
            )

            audit(f"Started command in new console: {command} | cwd={cwd}")

            return {
                "status": "success",
                "message": f"Started command: {command}",
            }

        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        audit(f"Ran command: {command} | cwd={cwd}")

        return {
            "status": "success",
            "command": command,
            "cwd": cwd,
            "output": result.stdout or result.stderr,
        }
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def confirm_action(action_id: str):
    action = pop_pending_action(action_id)

    if not action:
        return {
            "status": "error",
            "message": "No pending action found with that ID.",
        }

    action_type = action["action_type"]
    payload = action["payload"]

    if action_type == "write_file":
        path = payload["path"]
        content = payload["content"]

        if not is_path_allowed(path):
            return {
                "status": "error",
                "message": "Access denied.",
            }

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content, encoding="utf-8")
        audit(f"Wrote file {path}")

        return {
            "status": "success",
            "message": f"File written: {path}",
        }

    if action_type == "append_file":
        path = payload["path"]
        content = payload["content"]

        if not is_path_allowed(path):
            return {
                "status": "error",
                "message": "Access denied.",
            }

        Path(path).parent.mkdir(parents=True, exist_ok=True)

        with open(path, "a", encoding="utf-8") as file:
            file.write(content)

        audit(f"Appended file {path}")

        return {
            "status": "success",
            "message": f"Content appended to: {path}",
        }

    if action_type == "run_command":
        return execute_command(payload["command"], payload["cwd"])

    return {
        "status": "error",
        "message": "Unknown pending action type.",
    }


def show_pending_actions():
    return {
        "status": "success",
        "pending_actions": list_pending_actions(),
    }