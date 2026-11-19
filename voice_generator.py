import os
import time
import asyncio
import edge_tts
import subprocess
from config import OUTPUT_DIR, VOICE_NAME, VOICE_RATE, VOICE_PITCH

def get_audio_duration(file_path):
    """
    Returns audio duration in seconds using ffprobe.
    """
    if not file_path or not os.path.exists(file_path) or os.path.getsize(file_path) < 100:
        return 0.0
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 0.0

async def _synthesize_async(text, output_file, voice):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=VOICE_RATE,
        pitch=VOICE_PITCH
    )
    await communicate.save(output_file)

def generate_tamil_voiceover(text, voice=None):
    """
    Converts Tamil text into realistic broadcast neural audio using Microsoft Edge-TTS.
    Returns: (audio_path, duration_seconds)
    """
    safe_text = (text or "").strip()
    if not safe_text:
        safe_text = "முக்கிய செய்திகள் தொடர்பான விபரங்கள் வெளியாகியுள்ளன."

    voice = voice or VOICE_NAME
    filename = f"voice_{int(time.time())}.mp3"
    out_path = os.path.join(OUTPUT_DIR, filename)

    for attempt in range(2):
        try:
            asyncio.run(_synthesize_async(safe_text, out_path, voice))
            if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
                duration = get_audio_duration(out_path)
                if duration > 0.0:
                    print(f"🎙️ AI Voice generated: {filename} ({duration:.1f}s) using {voice}")
                    return out_path, duration
        except Exception as e:
            print(f"Notice: Voice synthesis attempt {attempt + 1} error: {e}")
            time.sleep(1)

    # Clean up empty or broken file
    if os.path.exists(out_path):
        try:
            os.remove(out_path)
        except Exception:
            pass

    return None, 0.0
