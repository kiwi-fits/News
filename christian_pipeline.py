import os
import json
import time
from config import (
    CHRISTIAN_PAGE_NAME,
    CHRISTIAN_FB_PAGE_ID,
    CHRISTIAN_FB_ACCESS_TOKEN,
    CHRISTIAN_HISTORY_FILE,
    CHRISTIAN_STATE_FILE,
    OUTPUT_DIR
)
from christian_content_engine import (
    CHRISTIAN_CATEGORIES,
    get_scheduled_christian_category,
    generate_christian_story,
    fetch_christian_visuals,
    format_christian_caption
)
from christian_composer import compose_christian_reel
from voice_generator import generate_english_voiceover
from fb_publisher import publish_christian_reel_to_facebook
from pipeline import prune_stale_media

def load_christian_history():
    """
    Loads strictly the latest 10 posted/generated 'Jesus Hears You' devotional reels from disk.
    """
    if os.path.exists(CHRISTIAN_HISTORY_FILE):
        try:
            with open(CHRISTIAN_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data[:10] if isinstance(data, list) else []
        except Exception as e:
            print(f"Notice: Failed to load christian history: {e}")
            return []
    return []

def save_christian_history(item):
    """
    Saves a reel to christian_history.json, keeping strictly the last 10 entries.
    """
    history = load_christian_history()
    # Check if entry already exists (by ID) and update it
    for i, h in enumerate(history):
        if h.get("id") == item.get("id"):
            history[i] = item
            try:
                with open(CHRISTIAN_HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(history[:10], f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return

    history.insert(0, item)
    history = history[:10]
    try:
        with open(CHRISTIAN_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Notice: Failed to save christian history: {e}")

def create_christian_reel(category_id=None, auto_publish=False):
    """
    Executes the full devotional reel creation pipeline for 'Jesus Hears You':
    1. Selects category (by ID or current time slot).
    2. Generates devotional script, verse reference & headline.
    3. Synthesizes gentle Edge-TTS voiceover with word timings.
    4. Downloads/renders 9:16 vertical divine imagery.
    5. Composes 9:16 vertical video with White & Gold UI, word-by-word subtitles & soft acoustic piano.
    6. Optionally publishes directly to the 'Jesus Hears You' Facebook page.
    7. Saves entry into christian_history.json.
    """
    prune_stale_media()
    # 1. Resolve Category
    cat = None
    if category_id and category_id != "auto":
        for c in CHRISTIAN_CATEGORIES:
            if c["id"].lower() == category_id.lower():
                cat = c
                break
    if not cat:
        cat = get_scheduled_christian_category()

    print(f"\n✝️ ========================================================")
    print(f"✝️ Jesus Hears You Devotional Pipeline: {cat['badge_tag']} ({cat['time_slot']})")
    print(f"✝️ ========================================================\n")

    # 2. Content Generation
    story = generate_christian_story(cat["id"])
    script_text = (story.get("voiceover_script") or story.get("english_script") or story.get("script") or "").strip() if story else ""
    if not story or not script_text:
        return {"success": False, "error": "Failed to generate devotional content."}

    headline = story.get("headline", "")
    verse_ref = story.get("verse_reference", "")
    caption = (story.get("caption") or format_christian_caption(story, cat)).strip()
    visual_prompts = story.get("visual_prompts", [])

    print(f"📖 Verse: {verse_ref}")
    print(f"✨ Title: {headline}")
    print(f"📜 Script snippet: {script_text[:90]}...\n")
    print(f"📝 Facebook Reel Caption:\n{caption}\n")

    # 3. Voice Synthesis (Neural English Christopher voice with precise word boundary timestamps)
    print(f"🎙️ Generating inspirational English voiceover for: {cat['name']}...")
    voice_path, duration, word_timings = generate_english_voiceover(script_text, return_timings=True)
    if not voice_path or duration <= 0:
        return {"success": False, "error": "Voice synthesis failed."}

    # 4. Visual Imagery
    print(f"🎨 Gathering Divine 9:16 visuals...")
    visual_paths = fetch_christian_visuals(visual_prompts, cat["id"])
    if not visual_paths:
        return {"success": False, "error": "Failed to retrieve devotional visuals."}

    # 5. Video Composition (White & Gold UI, Word-by-Word Subtitles, Soft Piano Ducking)
    reel_video_path = compose_christian_reel(
        visual_path=visual_paths,
        voice_audio_path=voice_path,
        voice_duration=duration,
        headline=headline,
        verse_reference=verse_ref,
        category=cat["id"],
        subtitles=word_timings
    )

    if not reel_video_path or not os.path.exists(reel_video_path):
        return {"success": False, "error": "Video rendering failed."}

    item_id = f"christian_{cat['id']}_{int(time.time())}"
    item = {
        "id": item_id,
        "page_name": CHRISTIAN_PAGE_NAME,
        "category_id": cat["id"],
        "category_name": cat["name"],
        "badge_tag": cat["badge_tag"],
        "time_slot": cat["time_slot"],
        "headline": headline,
        "verse_reference": verse_ref,
        "script": script_text,
        "caption": caption,
        "video_file": os.path.basename(reel_video_path),
        "video_path": reel_video_path,
        "voice_file": os.path.basename(voice_path),
        "visual_files": [os.path.basename(p) for p in visual_paths],
        "duration": duration,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Generated"
    }

    # 6. Auto-Publish to Facebook Page
    if auto_publish:
        print(f"🚀 Auto-publishing to '{CHRISTIAN_PAGE_NAME}' Facebook Page...")
        fb_res = publish_christian_reel_to_facebook(
            video_path=reel_video_path,
            headline=headline,
            caption=caption
        )
        if fb_res.get("success"):
            item["status"] = "Published to Facebook"
            item["fb_video_id"] = fb_res.get("video_id")
            print(f"🎉 Devotional Reel successfully published! Video ID: {fb_res.get('video_id')}")

            # Clean up temporary media files to preserve disk space
            cleanup_files = [reel_video_path, voice_path] + visual_paths
            for p in cleanup_files:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                        print(f"🗑️ Cleaned temporary file: {os.path.basename(p)}")
                    except Exception:
                        pass
        else:
            if fb_res.get("error_code") == 368 or fb_res.get("blocked_temporarily"):
                item["status"] = "FB Error 368: Temporary Block (Uploads Paused)"
                print(f"🛑 'Jesus Hears You' Facebook Error 368 active. Pausing further attempts.")
            else:
                item["status"] = f"FB Error: {fb_res.get('error', 'Failed')}"

    # 7. Save to History
    save_christian_history(item)
    if auto_publish and not fb_res.get("success"):
        return {"success": False, "error": item["status"], "reel": item}
    return {"success": True, "reel": item}

def run_automated_christian_cycle(category_id=None, auto_publish=True):
    """
    Triggered by GitHub Actions or local scheduler to execute one scheduled posting cycle.
    """
    return create_christian_reel(category_id=category_id, auto_publish=auto_publish)
