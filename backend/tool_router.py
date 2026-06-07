import re


def detect_tool_intent(message: str):
    raw_message = message.strip()
    text = raw_message.lower()

    stop_phrases = [
        "stop",
        "stop talking",
        "stop speaking",
        "be quiet",
        "silence",
        "shut up",
    ]

    if text in stop_phrases:
        return {
            "tool_name": "stop_speech",
            "params": {},
        }

    # OPEN APPS
    if text in ["open calculator", "open calc", "launch calculator", "launch calc"]:
        return {
            "tool_name": "open_app",
            "params": {"app_name": "calculator"},
        }

    if text in ["open notepad", "launch notepad"]:
        return {
            "tool_name": "open_app",
            "params": {"app_name": "notepad"},
        }

    if text in ["open vscode", "open vs code", "launch vscode", "launch vs code"]:
        return {
            "tool_name": "open_app",
            "params": {"app_name": "vscode"},
        }

    if text in ["open chrome", "launch chrome"]:
        return {
            "tool_name": "open_app",
            "params": {"app_name": "chrome"},
        }

    if text in ["open edge", "launch edge"]:
        return {
            "tool_name": "open_app",
            "params": {"app_name": "edge"},
        }

    # IMPORTANT:
    # "show files in frontend" should OPEN the folder in File Explorer.
    # "list files in frontend" should only list names in chat.
    if text in [
        "show files in frontend",
        "show frontend files",
        "open frontend files",
        "open files in frontend",
        "show frontend folder",
        "open frontend folder",
        "open frontend",
    ]:
        return {
            "tool_name": "open_known_folder",
            "params": {"folder_name": "frontend"},
        }

    if text in [
        "show files in backend",
        "show backend files",
        "open backend files",
        "open files in backend",
        "show backend folder",
        "open backend folder",
        "open backend",
    ]:
        return {
            "tool_name": "open_known_folder",
            "params": {"folder_name": "backend"},
        }

    if text in [
        "show files in project",
        "show project files",
        "open project files",
        "open files in project",
        "show project folder",
        "open project folder",
        "open project",
        "open jarvis",
    ]:
        return {
            "tool_name": "open_known_folder",
            "params": {"folder_name": "project"},
        }

    # LIST FILES ONLY
    if text in [
        "list files in frontend",
        "list frontend files",
    ]:
        return {
            "tool_name": "list_files",
            "params": {"folder": "frontend", "limit": 80},
        }

    if text in [
        "list files in backend",
        "list backend files",
    ]:
        return {
            "tool_name": "list_files",
            "params": {"folder": "backend", "limit": 80},
        }

    if text in [
        "list files in project",
        "list project files",
        "list jarvis files",
    ]:
        return {
            "tool_name": "list_files",
            "params": {"folder": "project", "limit": 80},
        }

    confirm_match = re.match(r"confirm\s+([a-zA-Z0-9_-]+)", text)
    if confirm_match:
        return {
            "tool_name": "confirm_action",
            "params": {"action_id": confirm_match.group(1)},
        }

    if "pending actions" in text or "show pending" in text:
        return {
            "tool_name": "show_pending_actions",
            "params": {},
        }

    if (
        "allowed folders" in text
        or "what folders can you access" in text
        or "which folders can you access" in text
    ):
        return {
            "tool_name": "list_allowed_folders",
            "params": {},
        }

    list_match = re.search(
        r"^(list|display)\s+files\s+(in|inside|from)\s+(.+)$",
        raw_message,
        re.IGNORECASE,
    )
    if list_match:
        return {
            "tool_name": "list_files",
            "params": {"folder": list_match.group(3).strip(), "limit": 80},
        }

    list_match_alt = re.search(
        r"^(list|display)\s+(.+)\s+files$",
        raw_message,
        re.IGNORECASE,
    )
    if list_match_alt:
        return {
            "tool_name": "list_files",
            "params": {"folder": list_match_alt.group(2).strip(), "limit": 80},
        }

    read_match = re.search(r"^read\s+file\s+(.+)$", raw_message, re.IGNORECASE)
    if read_match:
        return {
            "tool_name": "read_file",
            "params": {"path": read_match.group(1).strip().strip('"')},
        }

    search_match = re.search(
        r"^search\s+(.+?)\s+(in|inside|from)\s+(.+)$",
        raw_message,
        re.IGNORECASE,
    )
    if search_match:
        return {
            "tool_name": "search_files",
            "params": {
                "query": search_match.group(1).strip(),
                "folder": search_match.group(3).strip(),
            },
        }

    run_match = re.search(r"^run\s+command\s+(.+)$", raw_message, re.IGNORECASE)
    if run_match:
        return {
            "tool_name": "run_command_request",
            "params": {"command_name": run_match.group(1).strip()},
        }

    if "start backend" in text:
        return {
            "tool_name": "run_command_request",
            "params": {"command_name": "start backend"},
        }

    if "start frontend" in text or "run frontend" in text:
        return {
            "tool_name": "run_command_request",
            "params": {"command_name": "start frontend"},
        }

    if "npm install" in text:
        return {
            "tool_name": "run_command_request",
            "params": {"command_name": "npm install"},
        }

    if "ollama list" in text:
        return {
            "tool_name": "run_command_request",
            "params": {"command_name": "ollama list"},
        }

    calc_match = re.search(
        r"(calculate|what is|what's)\s+([0-9\+\-\*\/\.\(\) %]+)",
        text,
    )
    if calc_match:
        return {
            "tool_name": "calculate",
            "params": {"expression": calc_match.group(2).strip()},
        }

    if text.startswith("remember that "):
        return {
            "tool_name": "remember_fact",
            "params": {"fact": raw_message[len("remember that "):].strip()},
        }

    if text.startswith("remember "):
        return {
            "tool_name": "remember_fact",
            "params": {"fact": raw_message[len("remember "):].strip()},
        }

    if (
        "show memory" in text
        or "what do you remember" in text
        or "show my memory" in text
    ):
        return {
            "tool_name": "show_memory",
            "params": {},
        }

    if "show notes" in text or "show my notes" in text or "list notes" in text:
        return {
            "tool_name": "list_notes",
            "params": {},
        }

    note_match = re.search(
        r"create (a )?note (called|named)?\s*(.*?)\s+(saying|with|that)\s+(.*)",
        raw_message,
        re.IGNORECASE | re.DOTALL,
    )
    if note_match:
        title = note_match.group(3).strip() or "Untitled"
        content = note_match.group(5).strip()
        return {
            "tool_name": "create_note",
            "params": {"title": title, "content": content},
        }

    if (
        "check system status" in text
        or "system status" in text
        or "pc status" in text
        or "check my system" in text
    ):
        return {
            "tool_name": "system_status",
            "params": {},
        }

    if "battery" in text:
        return {
            "tool_name": "battery_status",
            "params": {},
        }

    if "network" in text or "wifi" in text or "wi-fi" in text:
        return {
            "tool_name": "network_status",
            "params": {},
        }

    if "running apps" in text or "running processes" in text or "what is running" in text:
        return {
            "tool_name": "running_apps",
            "params": {},
        }

    if "open project in vscode" in text or "open project in vs code" in text:
        return {
            "tool_name": "open_project_in_vscode",
            "params": {},
        }

    if text.startswith("open "):
        target = text.replace("open ", "", 1).strip()

        if target.startswith("my "):
            target = target.replace("my ", "", 1).strip()

        app_names = [
            "notepad",
            "calculator",
            "calc",
            "vscode",
            "vs code",
            "chrome",
            "edge",
        ]

        website_names = [
            "youtube",
            "google",
            "github",
            "linkedin",
            "chatgpt",
        ]

        folder_names = [
            "desktop",
            "downloads",
            "documents",
            "jarvis",
            "project",
            "backend",
            "frontend",
        ]

        if target in app_names:
            return {
                "tool_name": "open_app",
                "params": {"app_name": target},
            }

        if target in folder_names:
            return {
                "tool_name": "open_known_folder",
                "params": {"folder_name": target},
            }

        if target in website_names or "." in target:
            return {
                "tool_name": "open_website",
                "params": {"site": target},
            }

    return None