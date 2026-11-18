import os
import time
import json
from news_fetcher import fetch_latest_news
from ai_rewriter import process_story, strip_channel_names
from voice_generator import generate_tamil_voiceover
from reel_composer import compose_ai_news_reel
from fb_publisher import publish_reel_to_facebook
from media_extractor import extract_media_urls, download_authentic_image, download_authentic_video, create_ambient_vertical_canvas, fetch_visual_for_story
from config import OUTPUT_DIR, SEEN_ARTICLES_FILE, FB_PAGE_ID, FB_ACCESS_TOKEN

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "reels_history.json")

def load_seen_articles():
    if os.path.exists(SEEN_ARTICLES_FILE):
        try:
            with open(SEEN_ARTICLES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        except Exception:
            return set()
    return set()

def mark_article_seen(url):
    if not url:
        return
    seen = load_seen_articles()
    seen.add(url)
    try:
        with open(SEEN_ARTICLES_FILE, "w", encoding="utf-8") as f:
            json.dump(list(seen), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Notice: Failed to save seen article: {e}")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(item):
    history = load_history()
    # Check if item with same id already in history
    for i, h in enumerate(history):
        if h.get("id") == item.get("id"):
            history[i] = item
            try:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(history[:100], f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return

    history.insert(0, item)
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[:100], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")

def create_ai_news_reel_for_article(article, auto_publish=False):
    """
    Unified AI News Reel Generation Pipeline:
    1. Rewrites news story using Gemini into conversational Tamil TV anchor script (~35s).
    2. Synthesizes Sri Lankan Tamil female voiceover (Edge-TTS Saranya).
    3. Extracts authentic news media (video clip or high-res photo from article link).
    4. Composes 1080x1920 (9:16 vertical) Facebook Reel with FFmpeg.
    5. Optionally publishes directly to Facebook Page (1448610858336603) with auto-comment.
    """
    raw_title = article.get("title", "")
    print(f"🎬 Starting AI Reel Pipeline for: {raw_title[:60]}...")

    # Step 1: Scriptwriting & Paraphrasing with Gemini
    print("🧠 Step 1: AI Paraphrasing & Scriptwriting with Gemini...")
    ai_data = process_story(article)
    reel_headline = ai_data["reel_headline"]
    voice_script = ai_data["voiceover_script"]
    visual_prompt = ai_data["visual_prompt"]
    question = ai_data.get("engagement_question", "உங்கள் கருத்தை கீழே கமெண்ட் செய்யுங்கள்!")

    # Step 2: Voiceover Generation
    print("🎙️ Step 2: Generating Neural Tamil Voiceover (Female: Saranya)...")
    voice_path, duration = generate_tamil_voiceover(voice_script)
    if not voice_path or not os.path.exists(voice_path):
        return {"success": False, "error": "Failed to synthesize Tamil voiceover."}

    # Step 3: Media Extraction (Authentic Video Clip or High-Res Image)
    print("🎨 Step 3: Extracting Authentic Media (Video / Photo)...")
    visual_path = None
    media_type = "image"
    media_urls = {}

    article_link = article.get("link")
    if article_link:
        try:
            media_urls = extract_media_urls(article_link)
        except Exception as me:
            print(f"Notice: Media extraction info: {me}")

    # 3a. Check for authentic news video clip
    vid_url = media_urls.get("video_url") or media_urls.get("video")
    if vid_url:
        try:
            print(f"📹 Found authentic news video clip: {vid_url}")
            vid_path = download_authentic_video(vid_url)
            if vid_path and os.path.exists(vid_path):
                visual_path = vid_path
                media_type = "video"
        except Exception as ve:
            print(f"Notice: Video clip download: {ve}")

    # 3b. Check for authentic news photo
    img_url = media_urls.get("image_url") or media_urls.get("image")
    if not visual_path and img_url:
        try:
            print(f"🖼️ Found authentic news photo: {img_url}")
            img_path = download_authentic_image(img_url)
            if img_path and os.path.exists(img_path):
                canvas_path = os.path.join(OUTPUT_DIR, f"canvas_{int(time.time())}.jpg")
                create_ambient_vertical_canvas(img_path, canvas_path)
                if os.path.exists(canvas_path):
                    visual_path = canvas_path
        except Exception as ie:
            print(f"Notice: Image download: {ie}")

    # 3c. Fallback to image_url or editorial visual
    if not visual_path:
        visual_path = fetch_visual_for_story(
            article_image_url=article.get("image_url"),
            keyword=visual_prompt
        )

    if not visual_path or not os.path.exists(visual_path):
        return {"success": False, "error": "Failed to prepare visual media background."}

    # Step 4: 9:16 Vertical Broadcast Reel Composition
    print("🎞️ Step 4: Rendering 9:16 Vertical Broadcast Reel with FFmpeg...")
    reel_video_path = compose_ai_news_reel(
        visual_path=visual_path,
        voice_audio_path=voice_path,
        voice_duration=duration,
        headline=reel_headline,
        category=article.get("category", "breaking")
    )

    if not reel_video_path or not os.path.exists(reel_video_path):
        return {"success": False, "error": "FFmpeg video rendering failed."}

    # Compose Facebook Caption (includes greeting in written caption, never in voiceover, channel names stripped)
    reel_headline = strip_channel_names(reel_headline)
    voice_script = strip_channel_names(voice_script)
    question = strip_channel_names(question)

    caption = (
        f"🔴 வணக்கம்! இன்றைய முக்கிய செய்தித் தொகுப்பு:\n\n"
        f"📌 {reel_headline}\n\n"
        f"🎙️ {voice_script}\n\n"
        f"💬 {question} 👇\n\n"
        f"🔔 இலங்கையின் நம்பகமான உண்மைச் செய்திகளை உடனுக்குடன் அறிய எமது பக்கத்தை Follow & Like செய்யுங்கள்! 👍\n\n"
        f"🔗 உங்கள் கருத்துக்களை முதலாவது கமெண்ட்டில் (First Comment) பகிருங்கள்! 👇\n\n"
        f"#Reels #TamilReels #SriLanka #lka #TamilNews #BreakingNews #AIReels #செய்திமையம்"
    )
    caption = strip_channel_names(caption)

    item = {
        "id": f"reel_{int(time.time())}",
        "headline": reel_headline,
        "voice_script": voice_script,
        "question": question,
        "caption": caption,
        "video_file": os.path.basename(reel_video_path),
        "video_path": reel_video_path,
        "voice_file": os.path.basename(voice_path),
        "visual_file": os.path.basename(visual_path),
        "media_type": media_type,
        "duration": duration,
        "article_link": article.get("link"),
        "source": article.get("source"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Generated"
    }

    # Step 5: Optional Auto-Publish to Facebook
    if auto_publish and FB_PAGE_ID and FB_ACCESS_TOKEN:
        print(f"🚀 Auto-Publishing Reel to Facebook Page ({FB_PAGE_ID})...")
        fb_res = publish_reel_to_facebook(
            video_path=reel_video_path,
            headline=reel_headline,
            caption=caption,
            article_link=article.get("link"),
            engagement_question=question
        )
        if fb_res.get("success"):
            item["status"] = "Published to Facebook"
            item["fb_video_id"] = fb_res.get("video_id")
            print(f"🎉 Successfully published to Facebook! Video ID: {fb_res.get('video_id')}")

            # Clean up all media files immediately after publishing to Facebook
            for p in [reel_video_path, voice_path, visual_path]:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                        print(f"🗑️ Deleted published media from disk: {os.path.basename(p)}")
                    except Exception as ce:
                        print(f"Notice: Media cleanup notice: {ce}")
        else:
            item["status"] = f"FB Error: {fb_res.get('error', 'Failed')}"

    # Mark as seen to prevent duplicates
    if article.get("link"):
        mark_article_seen(article["link"])

    save_history(item)
    return {"success": True, "reel": item}

def run_automated_news_cycle(auto_publish=True):
    """
    Executes one automated scan cycle:
    1. Fetches freshest news across Sri Lanka Tamil feeds.
    2. Identifies the newest unseen story.
    3. Generates complete 9:16 Reel.
    4. Posts directly to Facebook.
    """
    seen = load_seen_articles()
    articles = fetch_latest_news(limit_per_feed=4)

    target_article = None
    for art in articles:
        link = art.get("link")
        if link and link not in seen:
            target_article = art
            break

    if not target_article:
        return {
            "success": True,
            "processed": False,
            "message": "All news feeds are up to date. No new unseen stories."
        }

    print(f"⚡ Processing fresh story: {target_article['title']}")
    res = create_ai_news_reel_for_article(target_article, auto_publish=auto_publish)
    if res.get("success"):
        res["processed"] = True
    return res
