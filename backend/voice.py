import asyncio
import os
import tempfile
import threading
import edge_tts
import pygame


VOICE_NAME = "en-US-JennyNeural"

_voice_lock = threading.Lock()
_currently_speaking = False


def clean_text_for_voice(text: str) -> str:
    text = text.replace("*", "")
    text = text.replace("#", "")
    text = text.replace("`", "")
    text = text.replace("{", "")
    text = text.replace("}", "")
    text = text.replace("[", "")
    text = text.replace("]", "")

    if len(text) > 700:
        text = text[:700] + "..."

    return text.strip()


async def generate_voice_file(text: str, output_path: str):
    voice_text = clean_text_for_voice(text)

    communicate = edge_tts.Communicate(
        text=voice_text,
        voice=VOICE_NAME,
        rate="-6%",
        pitch="+3Hz",
        volume="+0%",
    )

    await communicate.save(output_path)


def stop_speech():
    global _currently_speaking

    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()

        _currently_speaking = False

        return {
            "status": "success",
            "message": "Speech stopped.",
        }
    except Exception as error:
        _currently_speaking = False

        return {
            "status": "error",
            "message": str(error),
        }


def play_audio_file(file_path: str):
    global _currently_speaking

    try:
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        _currently_speaking = True

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        pygame.mixer.music.stop()
        pygame.mixer.quit()
        _currently_speaking = False

    except Exception as error:
        _currently_speaking = False
        print("Voice playback failed:", error)


def speak_text(text: str):
    if not text or not text.strip():
        return

    with _voice_lock:
        stop_speech()

        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, "local_assistant_voice.mp3")

        try:
            asyncio.run(generate_voice_file(text, output_path))
            play_audio_file(output_path)
        except Exception as error:
            print("Voice generation failed:", error)


def speak_text_async(text: str):
    thread = threading.Thread(target=speak_text, args=(text,), daemon=True)
    thread.start()