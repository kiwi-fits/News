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
        return 20.0

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
    voice = voice or VOICE_NAME
    filename = f"voice_{int(time.time())}.mp3"
    out_path = os.path.join(OUTPUT_DIR, filename)

    try:
        asyncio.run(_synthesize_async(text, out_path, voice))
        duration = get_audio_duration(out_path)
        print(f"🎙️ AI Voice generated: {filename} ({duration:.1f}s) using {voice}")
        return out_path, duration
    except Exception as e:
        print(f"Error generating voice: {e}")
        return None, 0.0
