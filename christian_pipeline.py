import os
import json
import time
from config import (
    CHRISTIAN_PAGE_NAME,
    CHRISTIAN_HISTORY_FILE,
    ENABLE_YOUTUBE_CHRISTIAN_PUBLISH
)
from christian_content_engine import (
    CHRISTIAN_CATEGORIES,
    get_scheduled_christian_category,
    generate_christian_story,
    fetch_christian_visuals,
    format_christian_caption,
    record_used_christian_content
)
from christian_composer import compose_christian_reel
from voice_generator import generate_english_voiceover
from fb_publisher import publish_christian_reel_to_facebook
from youtube_publisher import publish_to_youtube_shorts, is_youtube_configured
from pipeline import prune_stale_media

def load_christian_history():
    """
    Loads recent posted/generated 'Jesus Hears You' devotional reels from disk (up to 150).
    """
    if os.path.exists(CHRISTIAN_HISTORY_FILE):
        try:
            with open(CHRISTIAN_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data[:150] if isinstance(data, list) else []
        except Exception as e:
            print(f"Notice: Failed to load christian history: {e}")
            return []
    return []

def get_today_christian_post_count():
    """
    Returns the number of devotional reels successfully published today (UTC/local).
    Used to track and enforce the 40 reels/day target.
    """
    import datetime
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    hist = load_christian_history()
    return sum(
        1 for h in hist
        if str(h.get("timestamp", "")).startswith(today_str)
        and (h.get("status") == "Published to Facebook" or h.get("fb_video_id"))
    )

def save_christian_history(item):
    """
    Saves a reel to christian_history.json, keeping the last 100 entries.
    """
    history = load_christian_history()
    # Check if entry already exists (by ID) and update it
    for i, h in enumerate(history):
        if h.get("id") == item.get("id"):
            history[i] = item
            try:
                with open(CHRISTIAN_HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(history[:100], f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return

    history.insert(0, item)
    history = history[:150]
    try:
        with open(CHRISTIAN_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Notice: Failed to save christian history: {e}")

def create_christian_reel(category_id=None, auto_publish=False, custom_story=None, publish_to_youtube=None):
    """
    Executes the full devotional reel creation pipeline for 'Jesus Hears You':
    1. Selects category (by ID or current time slot).
    2. Generates devotional script, verse reference & headline (or accepts custom_story).
    3. Synthesizes gentle Edge-TTS voiceover with word timings.
    4. Downloads/renders 9:16 vertical divine imagery.
    5. Composes 9:16 vertical video with White & Gold UI, word-by-word subtitles & soft acoustic piano.
    6. Publishes directly to the 'Jesus Hears You' Facebook page and/or YouTube Shorts.
    7. Saves entry into christian_history.json.
    """
    prune_stale_media()
    should_yt = ENABLE_YOUTUBE_CHRISTIAN_PUBLISH if publish_to_youtube is None else bool(publish_to_youtube)
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
    if custom_story and (custom_story.get("script") or custom_story.get("voiceover_script")):
        story = custom_story
        if not story.get("visual_prompts"):
            story["visual_prompts"] = [
                f"Peaceful serene Christian morning light, cross on hill, warm sunrise, cinematic 9:16 vertical 8k",
                f"Hands praying with open Holy Bible, soft golden candlelight, sacred hope, cinematic 9:16 vertical 8k"
            ]
    else:
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

    # 4. Visual Imagery (Thematic Jesus Christ Visual matching reel topic, no rapid transitions)
    print(f"🎨 Selecting Thematic Jesus Christ 9:16 visual...")
    if custom_story and custom_story.get("visual_paths"):
        visual_paths = custom_story["visual_paths"]
        if isinstance(visual_paths, str):
            visual_paths = [visual_paths]
    else:
        visual_paths = fetch_christian_visuals(
            visual_prompts=visual_prompts,
            category_id=cat["id"],
            headline=headline,
            verse_reference=verse_ref,
            script_text=script_text
        )
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

    # 6. Auto-Publish to Facebook Page & YouTube Shorts
    fb_res = None
    yt_res = None

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
            item["fb_reel_url"] = f"https://www.facebook.com/reel/{fb_res.get('video_id')}/"
            print(f"🎉 Devotional Reel successfully published to Facebook! Video ID: {fb_res.get('video_id')}")

            # Post immediate viral seed prayer comment to trigger comment velocity & algorithmic distribution
            try:
                from fb_comment_bot import post_seed_prayer_comment
                post_seed_prayer_comment(video_id=fb_res.get("video_id"), category_id=cat["id"])
            except Exception as s_err:
                print(f"Notice: Seed prayer comment notice: {s_err}")
        else:
            if fb_res.get("error_code") == 368 or fb_res.get("blocked_temporarily"):
                item["status"] = "FB Error 368: Temporary Block (Uploads Paused)"
                print(f"🛑 'Jesus Hears You' Facebook Error 368 active. Pausing further attempts.")
            else:
                item["status"] = f"FB Error: {fb_res.get('error', 'Failed')}"

    # 6B. Auto-Publish to YouTube Shorts
    if should_yt:
        if is_youtube_configured():
            print(f"📺 Publishing devotional Reel to YouTube Shorts...")
            yt_res = publish_to_youtube_shorts(
                video_path=reel_video_path,
                headline=headline,
                script=script_text,
                verse_reference=verse_ref
            )
            if yt_res.get("success"):
                item["youtube_video_id"] = yt_res.get("video_id")
                item["youtube_url"] = yt_res.get("url")
                if item["status"] == "Published to Facebook":
                    item["status"] = "Published to Facebook & YouTube Shorts"
                else:
                    item["status"] = "Published to YouTube Shorts"
                print(f"🎉 Devotional Reel published to YouTube Shorts: {yt_res.get('url')}")
            else:
                item["youtube_error"] = yt_res.get("error")
                print(f"⚠️ YouTube Shorts upload notice: {yt_res.get('error')}")
        else:
            print("Notice: YouTube publishing requested, but YouTube credentials not yet configured in .env")

    # 7. Deduplication & Cleanup
    if (fb_res and fb_res.get("success")) or (yt_res and yt_res.get("success")):
        try:
            record_used_christian_content(
                verse_ref=verse_ref,
                headline=headline,
                topic_id=story.get("topic_id"),
                category=cat["id"],
                fb_video_id=fb_res.get("video_id") if fb_res else None
            )
        except Exception as d_err:
            print(f"Notice: Failed to record deduplication video ID: {d_err}")

        # Clean up temporary media files to preserve disk space
        cleanup_files = [reel_video_path, voice_path] + visual_paths
        for p in cleanup_files:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                    print(f"🗑️ Cleaned temporary file: {os.path.basename(p)}")
                except Exception:
                    pass

    # 8. Save to History
    save_christian_history(item)

    # 9. Trigger Automated AI Comment Bot (reply to all new comments to boost engagement)
    if auto_publish:
        try:
            import threading
            from fb_comment_bot import run_christian_comment_reply_cycle
            threading.Thread(target=run_christian_comment_reply_cycle, kwargs={"send_private_dms": False}, daemon=True).start()
            print("💬 AI Comment Bot scan triggered in background.")
        except Exception as c_err:
            print(f"Notice: Comment reply sync notice: {c_err}")

    if auto_publish and fb_res and not fb_res.get("success") and not (yt_res and yt_res.get("success")):
        return {"success": False, "error": item["status"], "reel": item}
    return {"success": True, "reel": item}

def run_automated_christian_cycle(category_id=None, auto_publish=True, publish_to_youtube=None):
    """
    Triggered by GitHub Actions or local scheduler to execute one scheduled posting cycle.
    """
    return create_christian_reel(category_id=category_id, auto_publish=auto_publish, publish_to_youtube=publish_to_youtube)
