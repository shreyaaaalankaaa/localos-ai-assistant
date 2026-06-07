import os
import re
from datetime import datetime

from pc_tools import (
    open_website,
    open_app,
    open_folder,
    open_known_folder,
    system_status,
    battery_status,
    network_status,
    running_apps,
    open_project_in_vscode,
    start_frontend,
    safe_command,
)

from voice import stop_speech

try:
    from system_access import (
        list_allowed_folders,
        list_files,
        read_file,
        search_files,
        write_file_request,
        append_file_request,
        run_command_request,
        confirm_action,
        show_pending_actions,
    )
except Exception:
    list_allowed_folders = None
    list_files = None
    read_file = None
    search_files = None
    write_file_request = None
    append_file_request = None
    run_command_request = None
    confirm_action = None
    show_pending_actions = None


NOTES_DIR = "notes"
MEMORY_FILE = "memory.txt"


def ensure_notes_dir():
    if not os.path.exists(NOTES_DIR):
        os.makedirs(NOTES_DIR)


def create_note(title: str, content: str):
    ensure_notes_dir()

    safe_title = re.sub(r"[^a-zA-Z0-9_-]", "_", title.strip())

    if not safe_title:
        safe_title = "Untitled"

    filepath = os.path.join(NOTES_DIR, f"{safe_title}.txt")

    with open(filepath, "w", encoding="utf-8") as file:
        file.write(f"Title: {title}\n")
        file.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        file.write(content)

    return {
        "status": "success",
        "message": f"Note '{title}' created successfully.",
        "path": filepath,
    }


def list_notes():
    ensure_notes_dir()
    files = [file for file in os.listdir(NOTES_DIR) if file.endswith(".txt")]

    if not files:
        return {
            "status": "success",
            "message": "No notes found yet.",
            "notes": [],
        }

    notes = []

    for file in files:
        path = os.path.join(NOTES_DIR, file)

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        notes.append(
            {
                "file": file,
                "content": content[:1000],
            }
        )

    return {
        "status": "success",
        "notes": notes,
    }


def calculate(expression: str):
    allowed_chars = "0123456789+-*/(). %"

    if not expression.strip():
        return {
            "status": "error",
            "message": "No expression provided.",
        }

    if not all(char in allowed_chars for char in expression):
        return {
            "status": "error",
            "message": "Only basic math expressions are allowed.",
        }

    try:
        result = eval(expression, {"__builtins__": None}, {})
        return {
            "status": "success",
            "expression": expression,
            "result": result,
            "message": f"{expression} = {result}",
        }
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def remember_fact(fact: str):
    if not fact.strip():
        return {
            "status": "error",
            "message": "No fact provided.",
        }

    with open(MEMORY_FILE, "a", encoding="utf-8") as file:
        file.write(f"- {fact}\n")

    return {
        "status": "success",
        "message": "Memory saved locally.",
        "fact": fact,
    }


def show_memory():
    if not os.path.exists(MEMORY_FILE):
        return {
            "status": "success",
            "memory": "",
            "message": "No memory saved yet.",
        }

    with open(MEMORY_FILE, "r", encoding="utf-8") as file:
        memory = file.read()

    return {
        "status": "success",
        "memory": memory,
    }


def unavailable_tool(tool_name: str):
    return {
        "status": "error",
        "message": f"{tool_name} is not available because system_access.py was not loaded correctly.",
    }


def run_tool(tool_name: str, params: dict):
    if params is None:
        params = {}

    if tool_name == "stop_speech":
        return stop_speech()

    if tool_name == "create_note":
        return create_note(
            title=params.get("title", "Untitled"),
            content=params.get("content", ""),
        )

    if tool_name == "list_notes":
        return list_notes()

    if tool_name == "calculate":
        return calculate(params.get("expression", ""))

    if tool_name == "remember_fact":
        return remember_fact(params.get("fact", ""))

    if tool_name == "show_memory":
        return show_memory()

    if tool_name == "open_website":
        return open_website(params.get("site", ""))

    if tool_name == "open_app":
        return open_app(params.get("app_name", ""))

    if tool_name == "open_folder":
        return open_folder(params.get("path", ""))

    if tool_name == "open_known_folder":
        return open_known_folder(params.get("folder_name", ""))

    if tool_name == "system_status":
        return system_status()

    if tool_name == "battery_status":
        return battery_status()

    if tool_name == "network_status":
        return network_status()

    if tool_name == "running_apps":
        return running_apps()

    if tool_name == "open_project_in_vscode":
        return open_project_in_vscode()

    if tool_name == "start_frontend":
        return start_frontend()

    if tool_name == "safe_command":
        return safe_command(params.get("command_name", ""))

    if tool_name == "list_allowed_folders":
        if list_allowed_folders is None:
            return unavailable_tool(tool_name)
        return list_allowed_folders()

    if tool_name == "list_files":
        if list_files is None:
            return unavailable_tool(tool_name)
        return list_files(params.get("folder", ""), params.get("limit", 80))

    if tool_name == "read_file":
        if read_file is None:
            return unavailable_tool(tool_name)
        return read_file(params.get("path", ""))

    if tool_name == "search_files":
        if search_files is None:
            return unavailable_tool(tool_name)
        return search_files(params.get("folder", ""), params.get("query", ""))

    if tool_name == "write_file_request":
        if write_file_request is None:
            return unavailable_tool(tool_name)
        return write_file_request(params.get("path", ""), params.get("content", ""))

    if tool_name == "append_file_request":
        if append_file_request is None:
            return unavailable_tool(tool_name)
        return append_file_request(params.get("path", ""), params.get("content", ""))

    if tool_name == "run_command_request":
        if run_command_request is None:
            return unavailable_tool(tool_name)
        return run_command_request(params.get("command_name", ""))

    if tool_name == "confirm_action":
        if confirm_action is None:
            return unavailable_tool(tool_name)
        return confirm_action(params.get("action_id", ""))

    if tool_name == "show_pending_actions":
        if show_pending_actions is None:
            return unavailable_tool(tool_name)
        return show_pending_actions()

    return {
        "status": "error",
        "message": f"Unknown tool: {tool_name}",
    }