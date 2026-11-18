"""Speech playback. Edge TTS is optional; offline pyttsx3 is the fallback.

Only invoked when the user explicitly enables speech. Failure to install a
speaker backend must never prevent the assistant API from starting.
"""
import asyncio
import os
import tempfile
import threading

try:
    import edge_tts
    import pygame
except ImportError:
    edge_tts = None
    pygame = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

_voice_lock = threading.RLock()
_stop_event = threading.Event()
_engine = None


def clean_text_for_voice(text: str) -> str:
    for character in '*#`{}[]':
        text = text.replace(character, '')
    return text.strip()[:700]


def stop_speech():
    _stop_event.set()
    try:
        if pygame and pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()
    except Exception:
        pass
    try:
        if _engine:
            _engine.stop()
    except Exception:
        pass
    return {'status': 'success', 'message': 'Speech stopped.'}


async def _make_edge_voice(text: str, destination: str):
    communication = edge_tts.Communicate(text=text, voice='en-US-JennyNeural')
    await communication.save(destination)


def speak_text(text: str):
    global _engine
    text = clean_text_for_voice(text)
    if not text:
        return
    with _voice_lock:
        _stop_event.clear()
        if edge_tts and pygame:
            try:
                path = os.path.join(tempfile.gettempdir(), 'localos_speech.mp3')
                asyncio.run(_make_edge_voice(text, path))
                if _stop_event.is_set():
                    return
                pygame.mixer.init()
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy() and not _stop_event.wait(0.1):
                    pass
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                return
            except Exception as exc:
                print('Online voice engine unavailable:', exc)
        if pyttsx3 and not _stop_event.is_set():
            try:
                _engine = pyttsx3.init()
                _engine.setProperty('rate', 174)
                _engine.say(text)
                _engine.runAndWait()
            except Exception as exc:
                print('Offline voice engine unavailable:', exc)
            finally:
                _engine = None


def speak_text_async(text: str):
    threading.Thread(target=speak_text, args=(text,), daemon=True).start()
