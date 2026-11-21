import os
import re
import time
import json
from news_fetcher import fetch_latest_news
from ai_rewriter import process_story, strip_channel_names
from voice_generator import generate_tamil_voiceover
from reel_composer import compose_ai_news_reel
from fb_publisher import publish_reel_to_facebook
from media_extractor import extract_media_urls, download_authentic_image, download_authentic_video, create_ambient_vertical_canvas
from config import OUTPUT_DIR, SEEN_ARTICLES_FILE, FB_PAGE_ID, FB_ACCESS_TOKEN, REJECTED_ARTICLES_FILE, REJECTED_TTL_SECONDS

from urllib.parse import urlparse, urlunparse

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "reels_history.json")
NEWS_SEEN_TOPICS_FILE = os.path.join(os.path.dirname(__file__), "news_seen_topics.json")

TAMIL_STOPWORDS = {
    'மற்றும்', 'குறித்து', 'விசேட', 'அறிவிப்பு', 'செய்தி', 'செய்திகள்', 'இலங்கை', 'இலங்கையில்',
    'என', 'என்று', 'உள்ள', 'ஒரு', 'பற்றி', 'முதல்', 'வரை', 'ஆனால்', 'அல்லது',
    'அதில்', 'இதனை', 'அவர்', 'இவர்', 'இன்று', 'நேற்று', 'நாளை', 'செய்ய', 'செய்த',
    'பல்வேறு', 'பல', 'முக்கிய', 'தொடர்பில்', 'தொடர்பான', 'ஆகிய', 'என்பது', 'வந்த',
    'உள்ளது', 'உள்ளனர்', 'பட்டது', 'பெற்ற', 'கொழும்பு', 'நாடு'
}

def normalize_news_url(url):
    """
    Normalizes news URLs by removing tracking/analytics query params (?utm_..., ?at_medium=...)
    and standardizing subdomains (tamil.adaderana.lk -> adaderanatamil.lk) to prevent duplicate fetches.
    """
    if not url:
        return ""
    try:
        p = urlparse(url.strip())
        clean_path = p.path.rstrip('/')
        clean_url = urlunparse((p.scheme, p.netloc, clean_path, '', '', '')).lower()
        clean_url = clean_url.replace("tamil.adaderana.lk", "adaderanatamil.lk")
        return clean_url
    except Exception:
        return url.strip().lower()

def extract_tamil_keywords(text):
    """
    Extracts significant content words from Tamil text, stripping common grammatical suffixes.
    Enables fuzzy semantic deduplication across different news portals reporting the same event.
    """
    if not text:
        return set()
    words = re.findall(r'[\u0b80-\u0bffa-zA-Z0-9]{3,}', text.lower())
    clean_words = []
    for w in words:
        if w in TAMIL_STOPWORDS:
            continue
        # Strip common Tamil inflectional suffixes (case markers, plural, adverbial)
        stem = re.sub(r'(இல்|க்கு|ஆல்|உடன்|ஆக|கள்|ஐ|ற்கு|வது|மாக|பில்|ரின்)$', '', w)
        clean_words.append(stem if len(stem) >= 3 else w)
    return set(clean_words)

def load_seen_topics():
    """Loads recorded topic signatures (last 48 hours / up to 500 stories)."""
    if os.path.exists(NEWS_SEEN_TOPICS_FILE):
        try:
            with open(NEWS_SEEN_TOPICS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    now = time.time()
                    # Retain last 48 hours (172,800 seconds)
                    fresh = [t for t in data if (now - t.get("timestamp", 0)) <= 172800]
                    return fresh
        except Exception:
            pass
    return []

def record_seen_topic(title, link=""):
    """Records a published story's significant keywords into the topic deduplication database."""
    if not title:
        return
    kws = list(extract_tamil_keywords(title))
    if not kws:
        return

    topics = load_seen_topics()
    entry = {
        "title": title[:120],
        "keywords": kws,
        "link": normalize_news_url(link),
        "timestamp": int(time.time())
    }
    topics.insert(0, entry)
    topics = topics[:500]

    try:
        with open(NEWS_SEEN_TOPICS_FILE, "w", encoding="utf-8") as f:
            json.dump(topics, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Notice: Failed to record seen topic: {e}")

def is_article_duplicate_topic(candidate_title, candidate_summary=""):
    """
    Checks if an incoming article covers the exact same breaking news story
    that was already published by another news outlet in the last 48 hours.
    Returns: (is_duplicate: bool, matched_past_title: str)
    """
    if not candidate_title:
        return False, ""

    c_words = extract_tamil_keywords(candidate_title)
    if candidate_summary:
        c_words.update(extract_tamil_keywords(candidate_summary))

    if len(c_words) < 2:
        return False, ""

    # 1. Check against recorded topics in news_seen_topics.json
    past_topics = load_seen_topics()
    for topic in past_topics:
        p_words = set(topic.get("keywords") or [])
        if not p_words:
            continue
        overlap = c_words & p_words
        union = c_words | p_words
        jaccard = len(overlap) / len(union) if union else 0.0

        # Duplicate rule: 3+ content keywords match OR (2+ keywords with >= 28% Jaccard)
        if len(overlap) >= 3 or (len(overlap) >= 2 and jaccard >= 0.28):
            return True, topic.get("title", "")

    # 2. Check against recent 10 reels in history
    recent_reels = load_history()
    for reel in recent_reels:
        r_title = reel.get("headline") or reel.get("title") or ""
        r_words = extract_tamil_keywords(r_title)
        if not r_words:
            continue
        overlap = c_words & r_words
        union = c_words | r_words
        jaccard = len(overlap) / len(union) if union else 0.0

        if len(overlap) >= 3 or (len(overlap) >= 2 and jaccard >= 0.28):
            return True, r_title

    return False, ""

def load_rejected_articles():
    """
    Loads rejected articles from rejected_articles.json,
    automatically pruning any entries older than 2 hours (REJECTED_TTL_SECONDS).
    """
    if not os.path.exists(REJECTED_ARTICLES_FILE):
        return []
    try:
        with open(REJECTED_ARTICLES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []

        now = time.time()
        fresh = [item for item in data if (now - item.get("timestamp", 0)) <= REJECTED_TTL_SECONDS]
        if len(fresh) != len(data):
            try:
                with open(REJECTED_ARTICLES_FILE, "w", encoding="utf-8") as f:
                    json.dump(fresh, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        return fresh
    except Exception:
        return []

def record_rejected_article(article, reason="NO_AUTHENTIC_MEDIA"):
    """
    Records an article into rejected_articles.json with a timestamp,
    ensuring it is removed from live feed and auto-pruned after 2 hours.
    """
    rejected = load_rejected_articles()
    link = (article.get("link") or "").strip()
    title = (article.get("title") or "").strip()

    # Avoid duplicate rejected entries
    for item in rejected:
        if link and item.get("link") == link:
            return
        if title and item.get("title") == title:
            return

    entry = {
        "title": title,
        "link": link,
        "source": article.get("source", ""),
        "reason": reason,
        "timestamp": int(time.time()),
        "time_str": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    rejected.insert(0, entry)

    # Prune older than 2 hours
    now = time.time()
    fresh = [item for item in rejected if (now - item.get("timestamp", 0)) <= REJECTED_TTL_SECONDS]

    try:
        with open(REJECTED_ARTICLES_FILE, "w", encoding="utf-8") as f:
            json.dump(fresh, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Notice: Failed to record rejected article: {e}")

def is_article_rejected(article, rejected_list=None):
    if rejected_list is None:
        rejected_list = load_rejected_articles()
    link = (article.get("link") or "").strip()
    title = (article.get("title") or "").strip()
    for r in rejected_list:
        if link and r.get("link") == link:
            return True
        if title and r.get("title") == title:
            return True
    return False

def load_seen_articles():
    if os.path.exists(SEEN_ARTICLES_FILE):
        try:
            with open(SEEN_ARTICLES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        except Exception:
            return set()
    return set()

def mark_article_seen(url, title=None, summary=""):
    if not url and not title:
        return
    seen = load_seen_articles()
    if url:
        seen.add(url.strip())
        norm_u = normalize_news_url(url)
        if norm_u:
            seen.add(norm_u)
    if title:
        clean_t = re.sub(r'[\W_]+', '', title.strip().lower())
        if clean_t:
            seen.add(f"title:{clean_t}")
        # Record into semantic topic registry to block cross-portal duplicates
        record_seen_topic(title, url)

    # Retain up to 10,000 seen signatures so trimmed historical posts never re-post
    seen_list = list(seen)
    if len(seen_list) > 10000:
        seen_list = seen_list[-10000:]
    try:
        with open(SEEN_ARTICLES_FILE, "w", encoding="utf-8") as f:
            json.dump(seen_list, f, ensure_ascii=False)
    except Exception as e:
        print(f"Notice: Failed to save seen article: {e}")

def is_article_seen(article, seen_set=None):
    if seen_set is None:
        seen_set = load_seen_articles()

    # 1. Direct URL check (original & normalized)
    link = (article.get("link") or "").strip()
    if link:
        if link in seen_set or normalize_news_url(link) in seen_set:
            return True

    # 2. Exact Title check (cleaned)
    title = (article.get("title") or "").strip()
    if title:
        clean_t = re.sub(r'[\W_]+', '', title.lower())
        if clean_t and f"title:{clean_t}" in seen_set:
            return True

    # 3. Fuzzy Semantic Topic check (detects duplicate reporting across different news sources)
    if title:
        summary = (article.get("summary") or "").strip()
        is_dup, matched_title = is_article_duplicate_topic(title, summary)
        if is_dup:
            print(f"⏩ DUPLICATE NEWS SKIPPED: '{title[:45]}...' matches already published story '{matched_title[:45]}...'")
            mark_article_seen(link, title)
            return True

    return False

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data[:10] if isinstance(data, list) else []
        except Exception:
            return []
    return []

def save_history(item):
    """
    Saves the reel to history, strictly enforcing only the last 10 posts in the database.
    Older posts beyond the 10 are pruned from reels_history.json.
    """
    history = load_history()
    # Check if item with same id already in history
    for i, h in enumerate(history):
        if h.get("id") == item.get("id"):
            history[i] = item
            try:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(history[:10], f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return

    history.insert(0, item)
    # Strictly store only the last 10 posts in the database
    history = history[:10]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")

def prune_stale_media(max_age_seconds=7200):
    """
    Cleans up orphaned or stale generated media files in OUTPUT_DIR older than max_age_seconds
    (default 2 hours) if not referenced in recent history (last 10 items).
    Keeps repository lightweight, fast, and prevents disk accumulation.
    """
    if not os.path.exists(OUTPUT_DIR):
        return

    active_files = set()
    # 1. Main Reels history
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                hist = json.load(f)
                if isinstance(hist, list):
                    for h in hist[:10]:
                        for k in ("video_file", "voice_file", "visual_file", "media_file"):
                            v = h.get(k)
                            if isinstance(v, list):
                                for sub in v:
                                    if sub: active_files.add(os.path.basename(sub))
                            elif isinstance(v, str) and v:
                                active_files.add(os.path.basename(v))
    except Exception:
        pass

    # 2. Christian Devotional history
    try:
        from config import CHRISTIAN_HISTORY_FILE
        if os.path.exists(CHRISTIAN_HISTORY_FILE):
            with open(CHRISTIAN_HISTORY_FILE, "r", encoding="utf-8") as f:
                ch_hist = json.load(f)
                if isinstance(ch_hist, list):
                    for h in ch_hist[:10]:
                        for k in ("video_file", "voice_file", "visual_files"):
                            v = h.get(k)
                            if isinstance(v, list):
                                for sub in v:
                                    if sub: active_files.add(os.path.basename(sub))
                            elif isinstance(v, str) and v:
                                active_files.add(os.path.basename(v))
    except Exception:
        pass

    now = time.time()
    cleaned = 0
    try:
        for fname in os.listdir(OUTPUT_DIR):
            if fname.startswith(".") or fname == ".gitkeep":
                continue
            fpath = os.path.join(OUTPUT_DIR, fname)
            if not os.path.isfile(fpath):
                continue
            if fname in active_files:
                continue
            # Aggressively remove temporary overlays, downloaded Pixabay clips, and intermediate frames
            is_temp = fname.startswith("temp_") or fname.startswith("christian_overlay_") or fname.startswith("pixabay_") or fname.endswith(".tmp")
            threshold = 120 if is_temp else max_age_seconds
            try:
                if (now - os.path.getmtime(fpath)) > threshold:
                    os.remove(fpath)
                    cleaned += 1
            except Exception:
                pass
    except Exception:
        pass

    if cleaned > 0:
        print(f"🧹 Pruned {cleaned} stale/orphaned media file(s) from generated/")

def create_ai_news_reel_for_article(article, auto_publish=False):
    """
    Unified AI News Reel Generation Pipeline:
    1. Extracts & verifies authentic news media (video clip or genuine high-res photo).
       STRICT QUALITY RULE: If no authentic media is available, rejects the story immediately.
    2. Rewrites news story using Gemini into conversational Tamil TV anchor script.
    3. Synthesizes Tamil male voiceover (Edge-TTS Anbu).
    4. Composes 1080x1920 (9:16 vertical) Facebook Reel with FFmpeg.
    5. Optionally publishes directly to Facebook Page (1448610858336603) with auto-comment.
    """
    prune_stale_media()
    raw_title = article.get("title", "")
    print(f"🎬 Starting AI Reel Pipeline for: {raw_title[:60]}...")

    # Step 1: Media Extraction (Authentic Video Clip or High-Res Image)
    print("🎨 Step 1: Extracting & Verifying Authentic Media (Video / Photo)...")
    visual_path = None
    media_type = "image"
    media_urls = {}

    article_link = article.get("link")
    if article_link:
        try:
            media_urls = extract_media_urls(article_link)
        except Exception as me:
            print(f"Notice: Media extraction info: {me}")

    # 1a. Check for authentic news video clip
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

    # 1b. Check for authentic news photos (Collect and use MULTIPLE photos!)
    collected_canvases = []
    photo_urls = media_urls.get("image_urls") or []
    if not photo_urls and (media_urls.get("image_url") or media_urls.get("image")):
        photo_urls = [media_urls.get("image_url") or media_urls.get("image")]
    if not photo_urls and article.get("image_url"):
        photo_urls = [article["image_url"]]

    if not visual_path and photo_urls:
        for idx, p_url in enumerate(photo_urls[:4]):
            try:
                print(f"🖼️ Found authentic news photo [{idx + 1}/{len(photo_urls[:4])}]: {p_url}")
                img_path = download_authentic_image(p_url, f"news_photo_{idx}")
                if img_path and os.path.exists(img_path):
                    canvas_path = os.path.join(OUTPUT_DIR, f"canvas_{int(time.time())}_{idx}.jpg")
                    create_ambient_vertical_canvas(img_path, canvas_path)
                    if os.path.exists(canvas_path):
                        collected_canvases.append(canvas_path)
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
            except Exception as ie:
                print(f"Notice: Image download [{idx}]: {ie}")

        if collected_canvases:
            visual_path = collected_canvases if len(collected_canvases) > 1 else collected_canvases[0]
            media_type = f"{len(collected_canvases)}_photos"
            print(f"📸 Prepared {len(collected_canvases)} authentic photo slide(s) for Reel video.")

    # 1c. STRICT RULE: Reject stories without authentic video or photo
    if not visual_path:
        print(f"🚫 REJECTED: No authentic image or video found for story: {raw_title[:60]}")
        return {
            "success": False,
            "error": "REJECTED_NO_MEDIA"
        }

    # Step 2: Scriptwriting & Paraphrasing with Gemini
    print("🧠 Step 2: AI Paraphrasing & Scriptwriting with Gemini...")
    ai_data = process_story(article)
    reel_headline = ai_data["reel_headline"]
    voice_script = ai_data["voiceover_script"]
    question = ai_data.get("engagement_question", "உங்கள் கருத்தை கீழே கமெண்ட் செய்யுங்கள்!")

    # Step 3: Voiceover Generation
    print("🎙️ Step 3: Generating Neural Tamil Voiceover...")
    voice_path, duration, timings = generate_tamil_voiceover(voice_script, return_timings=True)
    if not voice_path or not os.path.exists(voice_path):
        return {"success": False, "error": "Failed to synthesize Tamil voiceover."}

    # Step 4: 9:16 Vertical Broadcast Reel Composition
    print("🎞️ Step 4: Rendering 9:16 Vertical Broadcast Reel with FFmpeg & Dynamic Subtitles...")
    reel_video_path = compose_ai_news_reel(
        visual_path=visual_path,
        voice_audio_path=voice_path,
        voice_duration=duration,
        headline=reel_headline,
        category=article.get("category", "breaking"),
        subtitles=timings
    )

    if not reel_video_path or not os.path.exists(reel_video_path):
        return {"success": False, "error": "FFmpeg video rendering failed."}

    # Compose Facebook Caption: High-engagement viral post format with bullet points and targeted hashtags
    reel_headline = strip_channel_names(reel_headline)
    voice_script = strip_channel_names(voice_script)

    cat = (article.get("category") or "breaking").lower()
    category_headers = {
        "breaking": "🔴 முக்கிய செய்தி",
        "local": "🇱🇰 இலங்கைச் செய்தி",
        "world": "🌍 உலகச் செய்தி",
        "sports": "🏏 விளையாட்டுச் செய்தி",
        "politics": "🏛️ அரசியல் செய்தி",
        "economy": "📈 பொருளாதாரச் செய்தி"
    }
    header_badge = category_headers.get(cat, "🔴 முக்கிய செய்தி")

    caption = ai_data.get("viral_caption")
    if not caption:
        caption = (
            f"{header_badge}\n\n"
            f"📌 {reel_headline}\n\n"
            f"🔔 உடனுக்குடன் உண்மைச் செய்திகளை அறிய எமது பக்கத்தை Follow செய்யுங்கள்! 👍\n\n"
            f"#Reels #TamilReels #SriLanka #lka #TamilNews #BreakingNews #செய்திமையம்"
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
        "visual_file": [os.path.basename(p) for p in visual_path] if isinstance(visual_path, (list, tuple)) else os.path.basename(visual_path),
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
            cleanup_list = [reel_video_path, voice_path]
            if isinstance(visual_path, (list, tuple)):
                cleanup_list.extend(visual_path)
            elif visual_path:
                cleanup_list.append(visual_path)

            for p in cleanup_list:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                        print(f"🗑️ Deleted published media from disk: {os.path.basename(p)}")
                    except Exception as ce:
                        print(f"Notice: Media cleanup notice: {ce}")
        else:
            if fb_res.get("error_code") == 368 or fb_res.get("blocked_temporarily"):
                item["status"] = f"FB Error 368: Temporary Block (Uploads Paused)"
                print(f"🛑 Facebook Error 368 temporary block active. Retaining media for later upload.")
            else:
                item["status"] = f"FB Error: {fb_res.get('error', 'Failed')}"

    # Mark as seen to prevent duplicates (both link and normalized title)
    mark_article_seen(article.get("link"), article.get("title"))

    save_history(item)
    return {"success": True, "reel": item}

def run_automated_news_cycle(auto_publish=True):
    """
    Executes one automated scan cycle:
    1. Fetches freshest news across Sri Lanka Tamil feeds.
    2. Scans candidate stories and filters strictly for those with authentic news photos or video.
    3. If a story has no media, rejects it, marks as seen, and advances to the next candidate.
    4. Generates complete 9:16 Reel and posts to Facebook.
    """
    seen = load_seen_articles()
    articles = fetch_latest_news(limit_per_feed=15)

    for art in articles:
        if is_article_seen(art, seen):
            continue

        raw_title = art.get("title", "")
        print(f"⚡ Evaluating candidate story: {raw_title[:60]}")
        res = create_ai_news_reel_for_article(art, auto_publish=auto_publish)

        if res.get("success"):
            res["processed"] = True
            return res
        elif res.get("error") == "REJECTED_NO_MEDIA":
            # Record in rejected_articles.json (auto-pruned after 2 hours)
            record_rejected_article(art, reason="NO_AUTHENTIC_MEDIA")
            # Reject and mark as seen so we don't re-scan image-less articles in future runs
            mark_article_seen(art.get("link"), art.get("title"))
            seen.add(art.get("link"))
            clean_t = re.sub(r'[\W_]+', '', (art.get("title") or "").lower())
            if clean_t:
                seen.add(f"title:{clean_t}")
            print(f"⏩ Moved to rejected (No media). Advancing to next story...")
            continue
        else:
            print(f"Notice: Story failed with error: {res.get('error')}")

    return {
        "success": True,
        "processed": False,
        "message": "All news feeds are up to date. No new unseen stories with authentic media."
    }

def create_ai_evergreen_reel(auto_publish=False):
    """
    Generates an engaging, viral Tamil Reel for Evergreen Topics:
    - 🏛️ History / Chola / Ancient Mysteries
    - 💡 General Knowledge / Did You Know?
    - 🔬 Deep Space / Nature / Science Wonders
    - ✨ Wisdom / Motivational Micro-Story
    """
    prune_stale_media()
    from evergreen_generator import get_evergreen_story, fetch_evergreen_visuals

    story = get_evergreen_story()
    headline = story["headline"]
    voice_script = story["voiceover_script"]
    visual_prompts = story.get("visual_prompts") or [story.get("visual_prompt")]
    category_id = story.get("category_id", "gk")
    cat_info = story.get("category_info", {})
    question = story.get("engagement_question", "இந்த தகவல் பற்றிய உங்கள் கருத்தை கீழே பகிருங்கள்!")

    print(f"💡 Starting Evergreen Reel Pipeline [{category_id}]: {headline[:50]}...")

    # Step 1: Voiceover Generation
    print("🎙️ Generating Neural Tamil Voiceover...")
    voice_path, duration, timings = generate_tamil_voiceover(voice_script, return_timings=True)
    if not voice_path or not os.path.exists(voice_path):
        return {"success": False, "error": "Failed to synthesize Tamil voiceover."}

    # Step 2: Visual Media Generation (Multiple scenes)
    print("🎨 Preparing Evergreen Visual Media (Multiple scene angles)...")
    visual_path = fetch_evergreen_visuals(visual_prompts, category_id)
    if not visual_path:
        return {"success": False, "error": "Failed to prepare visual media background."}

    # Step 3: Compose 9:16 Vertical Reel
    print("🎞️ Rendering 9:16 Vertical Evergreen Reel with FFmpeg & Dynamic Subtitles...")
    reel_video_path = compose_ai_news_reel(
        visual_path=visual_path,
        voice_audio_path=voice_path,
        voice_duration=duration,
        headline=headline,
        category=category_id,
        subtitles=timings
    )

    if not reel_video_path or not os.path.exists(reel_video_path):
        return {"success": False, "error": "FFmpeg video rendering failed."}

    badge_tag = cat_info.get("badge_tag", "💡 பொது அறிவுத் தகவல்")
    hashtags = cat_info.get("hashtags", "#TamilReels #Reels #TamilFacts #Knowledge")
    caption = (
        f"{badge_tag}\n\n"
        f"📌 {headline}\n\n"
        f"🔔 பயனுள்ள சுவாரசியமான தகவல்களை உடனுக்குடன் அறிய எமது பக்கத்தை Follow செய்யுங்கள்! 👍\n\n"
        f"{hashtags}"
    )

    item = {
        "id": f"reel_{int(time.time())}",
        "headline": headline,
        "voice_script": voice_script,
        "question": question,
        "caption": caption,
        "video_file": os.path.basename(reel_video_path),
        "video_path": reel_video_path,
        "voice_file": os.path.basename(voice_path),
        "visual_file": [os.path.basename(p) for p in visual_path] if isinstance(visual_path, (list, tuple)) else os.path.basename(visual_path),
        "media_type": f"{len(visual_path)}_scenes" if isinstance(visual_path, (list, tuple)) else "image",
        "duration": duration,
        "article_link": None,
        "source": cat_info.get("name", "பொது அறிவு & வரலாறு"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Generated"
    }

    # Optional Auto-Publish to Facebook
    if auto_publish and FB_PAGE_ID and FB_ACCESS_TOKEN:
        print(f"🚀 Auto-Publishing Evergreen Reel to Facebook Page ({FB_PAGE_ID})...")
        fb_res = publish_reel_to_facebook(
            video_path=reel_video_path,
            headline=headline,
            caption=caption,
            article_link=None,
            engagement_question=question
        )
        if fb_res.get("success"):
            item["status"] = "Published to Facebook"
            item["fb_video_id"] = fb_res.get("video_id")
            print(f"🎉 Successfully published to Facebook! Video ID: {fb_res.get('video_id')}")

            # Clean up media files
            cleanup_list = [reel_video_path, voice_path]
            if isinstance(visual_path, (list, tuple)):
                cleanup_list.extend(visual_path)
            elif visual_path:
                cleanup_list.append(visual_path)

            for p in cleanup_list:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
        else:
            if fb_res.get("error_code") == 368 or fb_res.get("blocked_temporarily"):
                item["status"] = f"FB Error 368: Temporary Block (Uploads Paused)"
                print(f"🛑 Facebook Error 368 temporary block active. Retaining media for later upload.")
            else:
                item["status"] = f"FB Error: {fb_res.get('error', 'Failed')}"

    # Mark topic seen
    topic_id = story.get("topic_id") or headline
    mark_article_seen(None, title=topic_id)
    save_history(item)
    return {"success": True, "reel": item}

def run_automated_evergreen_cycle(auto_publish=True):
    """
    Executes one evergreen fallback cycle when no breaking news is active.
    """
    res = create_ai_evergreen_reel(auto_publish=auto_publish)
    if res.get("success"):
        res["processed"] = True
    return res
