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
        pitch=VOICE_PITCH,
        boundary="WordBoundary"
    )
    words = []
    audio_bytes = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            words.append({
                "text": chunk["text"],
                "start": round(chunk["offset"] / 10_000_000.0, 3),
                "end": round((chunk["offset"] + chunk["duration"]) / 10_000_000.0, 3)
            })
    with open(output_file, "wb") as f:
        f.write(audio_bytes)
    return words

async def _synth_sentence_part(text, part_file, voice):
    c = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=VOICE_RATE,
        pitch=VOICE_PITCH,
        boundary="WordBoundary"
    )
    words = []
    audio_bytes = bytearray()
    async for chunk in c.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            words.append({
                "text": chunk["text"],
                "offset": chunk["offset"],
                "duration": chunk["duration"]
            })
    with open(part_file, "wb") as f:
        f.write(audio_bytes)
    return words

async def _synthesize_sentences_with_gaps(sentences, output_file, voice, gap_ms):
    with tempfile.TemporaryDirectory() as tmpdir:
        part_files = [os.path.join(tmpdir, f"part_{i:03d}.mp3") for i in range(len(sentences))]
        tasks = [_synth_sentence_part(s, pf, voice) for s, pf in zip(sentences, part_files)]
        sentence_words_list = await asyncio.gather(*tasks)

        # Calculate exact start and end timestamps for on-screen word-by-word subtitles
        all_word_timings = []
        curr_t = 0.0
        gap_sec = max(0.1, float(gap_ms) / 1000.0)

        for s, pf, words in zip(sentences, part_files, sentence_words_list):
            dur = get_audio_duration(pf)
            if dur > 0.0:
                for w in words:
                    w_start = round(curr_t + (w["offset"] / 10_000_000.0), 3)
                    w_end = round(curr_t + ((w["offset"] + w["duration"]) / 10_000_000.0), 3)
                    all_word_timings.append({
                        "text": w["text"],
                        "start": w_start,
                        "end": w_end
                    })
                curr_t += dur + gap_sec

        # Generate silence clip for the breath pause between sentences
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

        return all_word_timings

def _generate_fallback_word_timings(text, total_duration):
    raw_words = text.split()
    if not raw_words or total_duration <= 0:
        return []
    total_chars = max(1, sum(len(w) for w in raw_words))
    curr_t = 0.1
    dur_pool = max(1.0, total_duration - 0.4)
    timings = []
    for w in raw_words:
        w_dur = max(0.18, (len(w) / total_chars) * dur_pool)
        timings.append({
            "text": w,
            "start": round(curr_t, 3),
            "end": round(curr_t + w_dur, 3)
        })
        curr_t += w_dur
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
                timings = asyncio.run(_synthesize_async(safe_text, out_path, voice))

            if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
                duration = get_audio_duration(out_path)
                if duration > 0.0:
                    if not timings:
                        timings = _generate_fallback_word_timings(safe_text, duration)
                    print(f"🎙️ AI Voice generated: {filename} ({duration:.1f}s, {len(timings)} words, {len(sentences)} sentences) using {voice}")
                    if return_timings:
                        return out_path, duration, timings
                    return out_path, duration
        except Exception as e:
            print(f"Notice: Voice synthesis with gaps attempt {attempt + 1} error: {e}. Falling back to single pass.")
            try:
                timings = asyncio.run(_synthesize_async(safe_text, out_path, voice))
                if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
                    duration = get_audio_duration(out_path)
                    if duration > 0.0:
                        if not timings:
                            timings = _generate_fallback_word_timings(safe_text, duration)
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
