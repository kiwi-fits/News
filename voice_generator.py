import os
import re
import time
import asyncio
import tempfile
import edge_tts
import subprocess
from config import OUTPUT_DIR, VOICE_NAME, VOICE_RATE, VOICE_PITCH, SENTENCE_GAP_MS
from tamil_transliteration import transliterate_english_to_tamil
from ai_rewriter import clean_speech_cadence

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

def split_into_news_sentences(text):
    """
    Splits Tamil news script into clean individual sentences while preserving
    initials (e.g. வி.எஸ்.), honorifics (திரு.), and numbers.
    """
    if not text:
        return []
    raw_parts = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    merged = []
    for part in raw_parts:
        if merged and (len(merged[-1]) < 12 or len(merged[-1].split()) <= 2) and merged[-1].endswith('.'):
            # If previous part is a standalone intro/greeting, keep it separate
            if merged[-1].strip('.').strip() in ['வணக்கம்', 'நன்றி', 'செய்திகள்']:
                merged.append(part)
            else:
                merged[-1] = f"{merged[-1]} {part}"
        else:
            merged.append(part)
    return merged

async def _synthesize_async(text, output_file, voice):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=VOICE_RATE,
        pitch=VOICE_PITCH
    )
    await communicate.save(output_file)

async def _synthesize_sentences_with_gaps(sentences, output_file, voice, gap_ms):
    with tempfile.TemporaryDirectory() as tmpdir:
        part_files = []
        tasks = []
        for i, s in enumerate(sentences):
            pf = os.path.join(tmpdir, f"part_{i:03d}.mp3")
            part_files.append(pf)
            c = edge_tts.Communicate(s, voice=voice, rate=VOICE_RATE, pitch=VOICE_PITCH)
            tasks.append(c.save(pf))

        await asyncio.gather(*tasks)

        # Calculate exact start and end timestamps for on-screen subtitles
        timings = []
        curr_t = 0.0
        gap_sec = max(0.1, float(gap_ms) / 1000.0)
        for s, pf in zip(sentences, part_files):
            dur = get_audio_duration(pf)
            if dur > 0.0:
                timings.append({
                    "text": s,
                    "start": round(curr_t, 2),
                    "end": round(curr_t + dur, 2)
                })
                curr_t += dur + gap_sec

        # Generate a small silence clip for the breath pause between sentences
        silence_file = os.path.join(tmpdir, "silence.mp3")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
            "-t", str(gap_sec), "-q:a", "9", "-acodec", "libmp3lame", silence_file
        ], capture_output=True, check=True)

        # Concatenate using ffmpeg concat demuxer
        concat_list = os.path.join(tmpdir, "concat.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for i, pf in enumerate(part_files):
                f.write(f"file '{pf}'\n")
                if i < len(part_files) - 1:
                    f.write(f"file '{silence_file}'\n")

        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c", "copy", output_file
        ], capture_output=True, check=True)

        return timings

def generate_tamil_voiceover(text, voice=None, return_timings=False):
    """
    Converts Tamil text into realistic broadcast neural audio using Microsoft Edge-TTS,
    inserting natural, audible pauses between sentences.
    Returns: (audio_path, duration_seconds) or (audio_path, duration_seconds, sentence_timings)
    """
    safe_text = (text or "").strip()
    if not safe_text:
        safe_text = "முக்கிய செய்திகள் தொடர்பான விபரங்கள் வெளியாகியுள்ளன."

    # Convert English words, abbreviations & symbols into phonetic Tamil (Thanglish)
    safe_text = transliterate_english_to_tamil(safe_text)
    # Strip pause-inducing punctuation and normalize word-to-word spacing
    safe_text = clean_speech_cadence(safe_text)

    voice = voice or VOICE_NAME
    filename = f"voice_{int(time.time())}.mp3"
    out_path = os.path.join(OUTPUT_DIR, filename)

    sentences = split_into_news_sentences(safe_text)
    timings = []

    for attempt in range(2):
        try:
            if len(sentences) > 1 and SENTENCE_GAP_MS > 0:
                timings = asyncio.run(_synthesize_sentences_with_gaps(sentences, out_path, voice, SENTENCE_GAP_MS))
            else:
                asyncio.run(_synthesize_async(safe_text, out_path, voice))
                dur = get_audio_duration(out_path)
                timings = [{"text": safe_text, "start": 0.0, "end": round(dur, 2)}] if dur > 0 else []

            if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
                duration = get_audio_duration(out_path)
                if duration > 0.0:
                    print(f"🎙️ AI Voice generated: {filename} ({duration:.1f}s, {len(sentences)} sentences) using {voice}")
                    if return_timings:
                        return out_path, duration, timings
                    return out_path, duration
        except Exception as e:
            print(f"Notice: Voice synthesis with gaps attempt {attempt + 1} error: {e}. Falling back to single pass.")
            try:
                asyncio.run(_synthesize_async(safe_text, out_path, voice))
                if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
                    duration = get_audio_duration(out_path)
                    if duration > 0.0:
                        timings = [{"text": safe_text, "start": 0.0, "end": round(duration, 2)}]
                        if return_timings:
                            return out_path, duration, timings
                        return out_path, duration
            except Exception:
                pass
            time.sleep(1)

    # Clean up empty or broken file
    if os.path.exists(out_path):
        try:
            os.remove(out_path)
        except Exception:
            pass

    if return_timings:
        return None, 0.0, []
    return None, 0.0
