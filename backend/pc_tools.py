import os
import sys
import shutil
from pathlib import Path
import socket
import subprocess
import webbrowser
import psutil


BASE_USER = str(Path.home())
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)


SAFE_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "vs code": "code",
    "vscode": "code",
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
}


SAFE_WEBSITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "linkedin": "https://www.linkedin.com",
    "chatgpt": "https://chatgpt.com",
}


SAFE_FOLDERS = {
    "desktop": os.path.join(BASE_USER, "Desktop"),
    "downloads": os.path.join(BASE_USER, "Downloads"),
    "documents": os.path.join(BASE_USER, "Documents"),
    "jarvis": PROJECT_ROOT,
    "project": PROJECT_ROOT,
    "backend": os.path.join(PROJECT_ROOT, "backend"),
    "frontend": os.path.join(PROJECT_ROOT, "frontend"),
}


def open_website(site: str):
    site = site.strip().lower()

    if site in SAFE_WEBSITES:
        url = SAFE_WEBSITES[site]
    elif site.startswith("http://") or site.startswith("https://"):
        url = site
    else:
        url = "https://" + site

    webbrowser.open(url)

    return {
        "status": "success",
        "message": f"Opened website: {url}",
        "url": url,
    }


def open_app(app_name: str):
    app_name = app_name.strip().lower()
    command = SAFE_APPS.get(app_name)

    if not command:
        return {
            "status": "error",
            "message": f"App '{app_name}' is not configured yet.",
        }

    try:
        executable = shutil.which(command)
        arguments = []
        if not executable and sys.platform == "win32":
            program_files = [os.environ.get("PROGRAMFILES", ""),
                             os.environ.get("PROGRAMFILES(X86)", ""),
                             os.environ.get("LOCALAPPDATA", "")]
            relative = {
                "chrome": "Google/Chrome/Application/chrome.exe",
                "edge": "Microsoft/Edge/Application/msedge.exe",
                "vscode": "Programs/Microsoft VS Code/Code.exe",
                "vs code": "Programs/Microsoft VS Code/Code.exe",
            }.get(app_name)
            if relative:
                executable = next((str(Path(base) / relative) for base in program_files
                                   if base and (Path(base) / relative).is_file()), None)
        if not executable and sys.platform == "darwin":
            mac_apps = {"notepad":"TextEdit", "calculator":"Calculator", "calc":"Calculator",
                        "vscode":"Visual Studio Code", "vs code":"Visual Studio Code",
                        "chrome":"Google Chrome", "edge":"Microsoft Edge"}
            if app_name in mac_apps:
                executable = "open"
                arguments = ["-a", mac_apps[app_name]]
        if not executable and sys.platform.startswith("linux"):
            linux_apps = {"notepad":["gedit","mousepad","kate"],
                          "calculator":["gnome-calculator","kcalc"],
                          "calc":["gnome-calculator","kcalc"],
                          "chrome":["google-chrome","chromium","chromium-browser"],
                          "edge":["microsoft-edge"]}
            executable = next((shutil.which(name) for name in linux_apps.get(app_name, [])
                              if shutil.which(name)), None)
        if not executable:
            return {"status": "error", "message": f"{app_name} is not installed or not on PATH on this computer."}
        subprocess.Popen([executable, *arguments], shell=False)
        return {"status": "success", "message": f"Opened {app_name}."}
    except Exception as error:
        return {
            "status": "error",
            "message": f"Could not open {app_name}: {str(error)}",
        }


def open_folder(path: str):
    path = path.strip()

    if not os.path.exists(path):
        return {
            "status": "error",
            "message": f"Folder does not exist: {path}",
        }

    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return {
            "status": "success",
            "message": f"Opened folder: {path}",
        }
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def open_known_folder(folder_name: str):
    folder_name = folder_name.strip().lower().replace("my ", "")
    path = SAFE_FOLDERS.get(folder_name)

    if not path:
        return {
            "status": "error",
            "message": f"Folder '{folder_name}' is not configured yet.",
        }

    return open_folder(path)


def system_status():
    try:
        disk = psutil.disk_usage(Path.home().anchor or "/")
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)

        return {
            "status": "success",
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": round(memory.used / (1024 ** 3), 2),
            "memory_total_gb": round(memory.total / (1024 ** 3), 2),
            "disk_c_percent": disk.percent,
            "disk_c_free_gb": round(disk.free / (1024 ** 3), 2),
            "message": (
                f"System scan complete. CPU: {cpu_percent}%, "
                f"Memory: {memory.percent}%, Disk C: {disk.percent}% used."
            ),
        }
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def battery_status():
    try:
        battery = psutil.sensors_battery()

        if battery is None:
            return {
                "status": "success",
                "battery_percent": None,
                "plugged_in": None,
                "message": "Battery information is not available on this device.",
            }

        plugged_text = "plugged in" if battery.power_plugged else "not plugged in"

        return {
            "status": "success",
            "battery_percent": battery.percent,
            "plugged_in": battery.power_plugged,
            "message": f"Battery is at {battery.percent}% and is {plugged_text}.",
        }
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def network_status():
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)

        return {
            "status": "success",
            "hostname": hostname,
            "ip_address": ip_address,
            "message": f"Network is active. Host: {hostname}, IP: {ip_address}.",
        }
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def running_apps(limit: int = 12):
    try:
        apps = []

        for process in psutil.process_iter(["pid", "name", "memory_percent"]):
            info = process.info
            name = info.get("name")

            if not name:
                continue

            apps.append(
                {
                    "pid": info.get("pid"),
                    "name": name,
                    "memory_percent": round(info.get("memory_percent") or 0, 2),
                }
            )

        apps = sorted(apps, key=lambda item: item["memory_percent"], reverse=True)

        return {
            "status": "success",
            "apps": apps[:limit],
            "message": "Here are the top running apps by memory usage.",
        }
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def open_project_in_vscode():
    try:
        executable = shutil.which('code')
        if not executable:
            return {"status": "error", "message": "VS Code is not on PATH."}
        subprocess.Popen([executable, PROJECT_ROOT])

        return {
            "status": "success",
            "message": "Opened project in VS Code.",
        }
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def start_frontend():
    try:
        frontend_path = os.path.join(PROJECT_ROOT, "frontend")

        if not os.path.exists(frontend_path):
            return {
                "status": "error",
                "message": "Frontend folder was not found.",
            }

        subprocess.Popen(
            "npm run dev",
            cwd=frontend_path,
            shell=True,
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )

        return {
            "status": "success",
            "message": "Started frontend in a new terminal window.",
        }
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def safe_command(command_name: str):
    command_name = command_name.strip().lower()

    allowed_commands = {
        "ollama list": {
            "command": "ollama list",
            "cwd": PROJECT_ROOT,
        },
        "dir backend": {
            "command": "dir",
            "cwd": os.path.join(PROJECT_ROOT, "backend"),
        },
        "dir frontend": {
            "command": "dir",
            "cwd": os.path.join(PROJECT_ROOT, "frontend"),
        },
    }

    command_info = allowed_commands.get(command_name)

    if not command_info:
        return {
            "status": "error",
            "message": "That command is not allowed. Allowed: ollama list, dir backend, dir frontend.",
        }

    try:
        result = subprocess.run(
            command_info["command"],
            cwd=command_info["cwd"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=25,
        )

        return {
            "status": "success",
            "command": command_info["command"],
            "output": result.stdout or result.stderr,
        }
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }