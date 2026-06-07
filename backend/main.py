import json
import os
import time
import requests
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from voice import speak_text_async, stop_speech
from tools import run_tool
from tool_router import detect_tool_intent


app = FastAPI(title="Local Assistant Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

MEMORY_FILE = "memory.txt"
PROFILE_FILE = "user_profile.json"
HISTORY_FILE = "chat_history.json"

MAX_HISTORY_MESSAGES = 14


class ChatRequest(BaseModel):
    message: str
    mode: str = "fast"
    speak: bool = False


class SpeakRequest(BaseModel):
    text: str


class ToolRequest(BaseModel):
    tool_name: str
    params: dict = {}


def now_text():
    return datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")


def load_json_file(path: str, default):
    if not os.path.exists(path):
        return default

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def save_json_file(path: str, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def load_profile():
    default_profile = {
        "name": "",
        "preferred_name": "",
        "tone": "witty, intelligent, warm, practical, slightly playful",
        "style": "concise but helpful",
        "project": "LocalOS AI desktop assistant",
        "likes": [],
        "dislikes": [],
        "goals": [
            "make the assistant feel like a real desktop AI app",
            "prepare the project for GitHub and LinkedIn"
        ],
    }

    return load_json_file(PROFILE_FILE, default_profile)


def save_profile(profile: dict):
    save_json_file(PROFILE_FILE, profile)


def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return ""

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            memory = file.read().strip()

        return memory[-1200:] if memory else ""
    except Exception:
        return ""


def load_history():
    history = load_json_file(HISTORY_FILE, [])

    if not isinstance(history, list):
        return []

    clean_history = []

    for item in history[-MAX_HISTORY_MESSAGES:]:
        role = item.get("role")
        content = item.get("content")

        if role in ["user", "assistant"] and isinstance(content, str):
            clean_history.append(
                {
                    "role": role,
                    "content": content[:3000],
                }
            )

    return clean_history


def save_history(history):
    save_json_file(HISTORY_FILE, history[-MAX_HISTORY_MESSAGES:])


def add_to_history(role: str, content: str):
    history = load_history()
    history.append(
        {
            "role": role,
            "content": content,
        }
    )
    save_history(history)


def clear_history():
    save_history([])


def update_profile_from_message(message: str):
    text = message.strip()
    lower = text.lower()

    profile = load_profile()
    changed = False

    name_prefixes = [
        "my name is ",
        "call me ",
        "you can call me ",
    ]

    for prefix in name_prefixes:
        if lower.startswith(prefix):
            value = text[len(prefix):].strip()

            if value:
                profile["preferred_name"] = value
                changed = True

    if lower.startswith("i like "):
        value = text[len("i like "):].strip()

        if value and value not in profile["likes"]:
            profile["likes"].append(value)
            changed = True

    if lower.startswith("i don't like ") or lower.startswith("i do not like "):
        if lower.startswith("i don't like "):
            value = text[len("i don't like "):].strip()
        else:
            value = text[len("i do not like "):].strip()

        if value and value not in profile["dislikes"]:
            profile["dislikes"].append(value)
            changed = True

    if "from now on" in lower and "tone" in lower:
        profile["tone"] = text
        changed = True

    if changed:
        save_profile(profile)

    return changed


def choose_model(mode: str) -> str:
    if mode == "fast":
        return "qwen2.5:0.5b"

    if mode == "normal":
        return "qwen2.5:1.5b"

    if mode == "reasoning":
        return "qwen2.5:1.5b"

    if mode == "coding":
        return "qwen2.5-coder:7b"

    return "qwen2.5:0.5b"


def get_num_predict(mode: str) -> int:
    if mode == "fast":
        return 130

    if mode == "normal":
        return 240

    if mode == "reasoning":
        return 360

    if mode == "coding":
        return 520

    return 160


def build_profile_text():
    profile = load_profile()

    preferred_name = profile.get("preferred_name") or profile.get("name") or "the user"
    tone = profile.get("tone", "")
    style = profile.get("style", "")
    project = profile.get("project", "")
    likes = profile.get("likes", [])
    dislikes = profile.get("dislikes", [])
    goals = profile.get("goals", [])

    return f"""
User profile:
- Preferred name: {preferred_name}
- Tone preference: {tone}
- Response style: {style}
- Current project: {project}
- Likes: {", ".join(likes) if likes else "not saved yet"}
- Dislikes: {", ".join(dislikes) if dislikes else "not saved yet"}
- Goals: {", ".join(goals) if goals else "not saved yet"}
"""


def build_system_prompt(mode: str) -> str:
    memory = load_memory()
    profile_text = build_profile_text()

    if mode == "fast":
        return f"""
You are a private local desktop AI assistant running on the user's computer.

Current time:
{now_text()}

{profile_text}

Saved memory:
{memory}

Personality:
- You are witty, sharp, warm, useful, and calm.
- You should feel more personal than a basic chatbot.
- You may ask the user natural follow-up questions when it helps.
- Do not ask unnecessary questions for simple commands.
- Keep answers concise, but not cold.
- If the user seems frustrated, respond gently and help them recover quickly.
- If the user is building this assistant, act like a thoughtful product partner.

Important behavior:
- For vague requests, ask one clear follow-up question.
- For personal preferences, remember them if the user states them clearly.
- For tool commands, stay brief.
- Do not pretend you can access something unless a tool actually did it.
- If the user asks to show/open folders, use tools.
- If the user asks to list files, list only names.
- Only read file contents if the user explicitly says "read file".

Mode:
Fast mode. Keep replies short and lively.
"""

    return f"""
You are a private local desktop AI assistant running on the user's computer.

Current time:
{now_text()}

{profile_text}

Saved memory:
{memory}

Personality:
- You are intelligent, witty, elegant, warm, practical, and slightly playful.
- You should feel personal and context-aware.
- You may ask thoughtful follow-up questions when the user’s request is vague.
- You should behave like a product partner, coding assistant, and local desktop assistant.
- You should not sound generic or robotic.
- You should not over-explain unless asked.

Important behavior:
- Use conversation history to maintain continuity.
- Ask one good question when you need more context.
- If the user is frustrated, slow down and simplify.
- If the user asks for code, give exact runnable code.
- If the user asks for project advice, be honest and practical.
- Do not pretend you can access something unless a tool actually did it.
- If the user asks to show/open folders, use tools.
- If the user asks to list files, list only names.
- Only read file contents if the user explicitly says "read file".

Mode:
{mode}
"""


def format_tool_result(tool_name: str, result: dict):
    message = result.get("message", "")

    if tool_name == "stop_speech":
        return "Stopped."

    if tool_name == "open_app":
        return message or "Opened app."

    if tool_name == "open_known_folder":
        return message or "Opened folder."

    if tool_name == "open_folder":
        return message or "Opened folder."

    if tool_name == "open_website":
        return message or "Opened website."

    if tool_name == "list_files" and result.get("status") == "success":
        folder = result.get("folder", "")
        folders = result.get("folders", [])
        files = result.get("files", [])

        lines = [f"Files in: {folder}", ""]

        if folders:
            lines.append("Folders:")
            for item in folders[:30]:
                lines.append(f"- {item.get('name')}")
            lines.append("")

        if files:
            lines.append("Files:")
            for item in files[:50]:
                size = item.get("size_bytes")
                size_text = f" ({size} bytes)" if size is not None else ""
                lines.append(f"- {item.get('name')}{size_text}")
        else:
            lines.append("No files found.")

        lines.append("")
        lines.append("Contents were not read.")

        return "\n".join(lines)

    if tool_name == "list_allowed_folders" and result.get("status") == "success":
        folders = result.get("folders", {})
        lines = ["Allowed folders:", ""]

        for key, path in folders.items():
            lines.append(f"- {key}: {path}")

        return "\n".join(lines)

    if tool_name == "search_files" and result.get("status") == "success":
        matches = result.get("matches", [])
        query = result.get("query", "")
        folder = result.get("folder", "")

        if not matches:
            return f"No matches found for '{query}' inside {folder}."

        lines = [f"Search results for '{query}' inside {folder}:", ""]

        for item in matches[:30]:
            lines.append(
                f"- {item.get('name')} [{item.get('match_type')}]\n  {item.get('path')}"
            )

        return "\n".join(lines)

    if tool_name == "read_file" and result.get("status") == "success":
        path = result.get("path", "")
        content = result.get("content", "")
        truncated = result.get("truncated", False)

        suffix = "\n\n[Output truncated]" if truncated else ""
        return f"Contents of:\n{path}\n\n{content}{suffix}"

    if tool_name == "system_status" and result.get("status") == "success":
        return (
            "System scan complete.\n\n"
            f"CPU: {result.get('cpu_percent')}%\n"
            f"Memory: {result.get('memory_percent')}%\n"
            f"Memory Used: {result.get('memory_used_gb')} GB / {result.get('memory_total_gb')} GB\n"
            f"Disk C Used: {result.get('disk_c_percent')}%\n"
            f"Disk C Free: {result.get('disk_c_free_gb')} GB"
        )

    if tool_name == "running_apps" and result.get("status") == "success":
        apps = result.get("apps", [])

        if not apps:
            return "No running apps found."

        lines = ["Top running apps by memory:", ""]

        for app_item in apps:
            lines.append(
                f"- {app_item.get('name')} | PID: {app_item.get('pid')} | Memory: {app_item.get('memory_percent')}%"
            )

        return "\n".join(lines)

    if tool_name == "show_memory":
        memory = result.get("memory", "")
        if not memory:
            return "No saved memory yet."
        return f"Saved memory:\n\n{memory}"

    if tool_name == "list_notes":
        notes = result.get("notes", [])
        if not notes:
            return "No notes found yet."

        lines = ["Notes:", ""]

        for note in notes[:5]:
            lines.append(f"- {note.get('file')}")
            lines.append(f"  {note.get('content', '')[:180]}")
            lines.append("")

        return "\n".join(lines)

    if message:
        return message

    return json.dumps(result, indent=2, ensure_ascii=False)


@app.get("/")
def home():
    return {
        "status": "backend online",
        "message": "Local backend is running.",
    }


@app.get("/startup")
def startup():
    profile = load_profile()
    preferred_name = profile.get("preferred_name") or profile.get("name")

    if preferred_name:
        greeting = f"System online. Welcome back, {preferred_name}."
    else:
        greeting = "System online. I’m ready. Tell me what you’d like me to call you."

    return {
        "greeting": greeting,
        "briefing": {
            "summary": "Startup ready.",
            "items": [],
        },
        "startup_text": greeting,
    }


@app.get("/wake-status")
def wake_status():
    return {
        "clap_detected": False,
        "status": "clap disabled",
    }


@app.post("/reset-wake")
def reset_wake():
    return {
        "status": "reset",
        "message": "Clap wake is disabled for stability.",
    }


@app.post("/stop-speech")
def stop_speech_endpoint():
    return stop_speech()


@app.post("/chat")
def chat(request: ChatRequest):
    start_time = time.time()
    user_message = request.message.strip()
    lowered = user_message.lower()

    if lowered in ["clear chat", "clear history", "reset conversation"]:
        clear_history()
        return {
            "model_used": "local-memory",
            "reply": "Conversation history cleared.",
            "latency_seconds": round(time.time() - start_time, 2),
        }

    if lowered in ["stop", "stop talking", "stop speaking", "be quiet", "silence", "shut up"]:
        stop_speech()
        return {
            "model_used": "speech-control",
            "reply": "Stopped.",
            "latency_seconds": round(time.time() - start_time, 2),
        }

    if not user_message:
        return {
            "model_used": "system",
            "reply": "I am here. Say the word.",
            "latency_seconds": 0,
        }

    update_profile_from_message(user_message)

    tool_intent = detect_tool_intent(user_message)

    if tool_intent:
        result = run_tool(tool_intent["tool_name"], tool_intent["params"])
        reply = format_tool_result(tool_intent["tool_name"], result)

        add_to_history("user", user_message)
        add_to_history("assistant", reply)

        if request.speak and tool_intent["tool_name"] != "stop_speech":
            speak_text_async(reply[:220])

        return {
            "model_used": "local-tool-router",
            "reply": reply,
            "latency_seconds": round(time.time() - start_time, 2),
        }

    model = choose_model(request.mode)
    history = load_history()

    messages = [
        {"role": "system", "content": build_system_prompt(request.mode)},
    ]

    messages.extend(history[-MAX_HISTORY_MESSAGES:])
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0.78,
            "top_p": 0.9,
            "num_predict": get_num_predict(request.mode),
            "num_ctx": 2048,
            "repeat_penalty": 1.06,
            "num_thread": 4,
        },
    }

    try:
        response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=90)
        response.raise_for_status()

        data = response.json()
        reply = data["message"]["content"].strip()

        if not reply:
            reply = "I am online, but the model went quiet. Try again."

    except Exception as error:
        reply = (
            "Ollama did not respond. Check that Ollama is running and the selected model is installed.\n\n"
            f"Technical detail: {str(error)}"
        )
        model = "ollama-error"

    add_to_history("user", user_message)
    add_to_history("assistant", reply)

    if request.speak:
        speak_text_async(reply[:420])

    return {
        "model_used": model,
        "reply": reply,
        "latency_seconds": round(time.time() - start_time, 2),
    }


@app.post("/speak")
def speak(request: SpeakRequest):
    speak_text_async(request.text[:500])
    return {"status": "speaking"}


@app.post("/tool")
def tool(request: ToolRequest):
    result = run_tool(request.tool_name, request.params)
    return result