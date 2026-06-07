import time
import threading
import numpy as np
import sounddevice as sd


wake_state = {
    "clap_detected": False,
    "last_clap_time": None,
    "is_listening": False,
    "message": "Waiting for clap.",
}


def reset_clap():
    wake_state["clap_detected"] = False
    wake_state["message"] = "Waiting for clap."


def get_wake_state():
    return wake_state


def audio_callback(indata, frames, time_info, status):
    if status:
        print("Audio status:", status)

    volume = float(np.linalg.norm(indata))
    now = time.time()

    threshold = 0.38
    cooldown = 2.0

    last_time = wake_state["last_clap_time"]

    if volume > threshold:
        if last_time is None or now - last_time > cooldown:
            wake_state["clap_detected"] = True
            wake_state["last_clap_time"] = now
            wake_state["message"] = "Clap detected. Jarvis wake signal activated."
            print("👏 Clap detected. Jarvis wake signal activated.")


def start_clap_listener():
    if wake_state["is_listening"]:
        return

    wake_state["is_listening"] = True

    def run():
        try:
            print("Clap listener active. Clap near your microphone.")
            with sd.InputStream(callback=audio_callback):
                while True:
                    time.sleep(0.1)
        except Exception as error:
            wake_state["is_listening"] = False
            wake_state["message"] = f"Clap listener failed: {error}"
            print("Clap listener failed:", error)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()