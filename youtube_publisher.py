import os
import json
import time
import requests
from config import (
    BASE_DIR,
    YOUTUBE_CLIENT_ID,
    YOUTUBE_CLIENT_SECRET,
    YOUTUBE_REFRESH_TOKEN,
    YOUTUBE_PRIVACY_STATUS,
    ENABLE_YOUTUBE_CHRISTIAN_PUBLISH,
    ENABLE_YOUTUBE_NEWS_PUBLISH,
    NEWS_YOUTUBE_CLIENT_ID,
    NEWS_YOUTUBE_CLIENT_SECRET,
    NEWS_YOUTUBE_REFRESH_TOKEN,
    NEWS_YOUTUBE_PRIVACY_STATUS
)

_cached_tokens = {}  # channel_type -> (access_token, expiry_timestamp)

_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*"
})

def get_credentials_for_channel(channel="christian"):
    """
    Returns (client_id, client_secret, refresh_token, privacy_status) for the specified channel.
    Channel can be 'christian' or 'news'.
    Allows fallback to global YOUTUBE_* credentials if channel-specific keys are omitted.
    """
    if channel == "news":
        cid = (NEWS_YOUTUBE_CLIENT_ID or "").strip() or ((YOUTUBE_CLIENT_ID or "").strip() if ENABLE_YOUTUBE_NEWS_PUBLISH else "")
        csecret = (NEWS_YOUTUBE_CLIENT_SECRET or "").strip() or ((YOUTUBE_CLIENT_SECRET or "").strip() if ENABLE_YOUTUBE_NEWS_PUBLISH else "")
        rtoken = (NEWS_YOUTUBE_REFRESH_TOKEN or "").strip() or ((YOUTUBE_REFRESH_TOKEN or "").strip() if ENABLE_YOUTUBE_NEWS_PUBLISH else "")
        privacy = (NEWS_YOUTUBE_PRIVACY_STATUS or "").strip() or (YOUTUBE_PRIVACY_STATUS or "public").strip()
    else:
        cid = (YOUTUBE_CLIENT_ID or "").strip()
        csecret = (YOUTUBE_CLIENT_SECRET or "").strip()
        rtoken = (YOUTUBE_REFRESH_TOKEN or "").strip()
        privacy = (YOUTUBE_PRIVACY_STATUS or "public").strip()
    return cid, csecret, rtoken, privacy

def is_youtube_configured(channel="christian"):
    """
    Checks if valid YouTube API credentials are provided for the given channel.
    Channel can be 'christian' or 'news'.
    """
    cid, csecret, rtoken, _ = get_credentials_for_channel(channel)
    return bool(
        cid
        and csecret
        and rtoken
        and len(cid) > 5
        and len(csecret) > 5
        and len(rtoken) > 5
    )

def is_news_youtube_configured():
    """Helper alias for news channel check."""
    return is_youtube_configured(channel="news")

def get_youtube_access_token(channel="christian"):
    """
    Exchanges the permanent OAuth refresh token for a short-lived access token.
    Caches token in memory per channel until 60 seconds before expiration.
    """
    global _cached_tokens
    now = time.time()
    cached = _cached_tokens.get(channel)
    if cached and now < cached[1]:
        return cached[0]

    cid, csecret, rtoken, _ = get_credentials_for_channel(channel)
    if not (cid and csecret and rtoken):
        return None

    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": cid,
        "client_secret": csecret,
        "refresh_token": rtoken,
        "grant_type": "refresh_token"
    }

    try:
        resp = _session.post(token_url, data=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            access_tok = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            _cached_tokens[channel] = (access_tok, now + expires_in - 60)
            return access_tok
        else:
            print(f"Notice: Failed to refresh YouTube OAuth token ({channel}): {resp.status_code} {resp.text}")
            return None
    except Exception as e:
        print(f"Notice: YouTube OAuth refresh error ({channel}): {e}")
        return None

def _execute_resumable_upload(video_path, metadata, access_token, log_title=None):
    """
    Executes a Google YouTube Resumable Video Upload:
    1. Sends metadata packet to obtain upload session Location URL.
    2. Streams video binary payload with progress.
    3. Returns { "success": bool, "video_id": str, "url": str }.
    """
    file_size = os.path.getsize(video_path)
    init_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
    init_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Length": str(file_size),
        "X-Upload-Content-Type": "video/mp4"
    }

    display_title = log_title or metadata.get("snippet", {}).get("title", "Video")
    print(f"📺 Initializing YouTube Shorts Resumable Upload for: '{display_title}' ({file_size / (1024*1024):.1f} MB)...")
    try:
        init_resp = _session.post(init_url, headers=init_headers, json=metadata, timeout=20)
        if init_resp.status_code != 200:
            return {
                "success": False,
                "error": f"YouTube upload initialization failed ({init_resp.status_code}): {init_resp.text[:200]}"
            }

        upload_url = init_resp.headers.get("Location")
        if not upload_url:
            return {"success": False, "error": "No resumable upload Location header returned by YouTube."}

        # Stream Video Binary Payload
        print(f"🚀 Uploading video bytes to YouTube...")
        with open(video_path, "rb") as video_file:
            upload_headers = {
                "Content-Type": "video/mp4",
                "Content-Length": str(file_size)
            }
            upload_resp = _session.put(upload_url, headers=upload_headers, data=video_file, timeout=120)

        if upload_resp.status_code in (200, 201):
            res_data = upload_resp.json()
            video_id = res_data.get("id")
            shorts_url = f"https://www.youtube.com/shorts/{video_id}"
            print(f"🎉 Successfully posted to YouTube Shorts! URL: {shorts_url}")
            return {
                "success": True,
                "video_id": video_id,
                "url": shorts_url,
                "title": display_title
            }
        else:
            return {
                "success": False,
                "error": f"YouTube video upload failed ({upload_resp.status_code}): {upload_resp.text[:250]}"
            }

    except Exception as e:
        return {"success": False, "error": f"YouTube upload exception: {str(e)}"}

def publish_to_youtube_shorts(video_path, headline, script="", verse_reference="", tags=None, privacy_status=None):
    """
    Uploads a 9:16 vertical video directly as a Christian devotional YouTube Short:
    - Sets title (max 100 chars, includes #Shorts)
    - Formats devotional description with scripture, prayer & hashtags
    - Categorized under People & Blogs (22)
    - Returns: { "success": bool, "video_id": str, "url": str }
    """
    if not os.path.exists(video_path):
        return {"success": False, "error": f"Video file not found at {video_path}"}

    if not is_youtube_configured(channel="christian"):
        return {
            "success": False,
            "error": "Christian YouTube API credentials not configured (YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN in .env)"
        }

    access_token = get_youtube_access_token(channel="christian")
    if not access_token:
        return {"success": False, "error": "Failed to obtain YouTube access token from refresh token."}

    # 1. Format Title (YouTube max length: 100 characters)
    clean_title = (headline or "").strip().rstrip(".! ")
    emoji_prefix = "✝️ " if not any(clean_title.startswith(e) for e in ["✝️", "🕊️", "🙏", "✨", "📖", "🌅"]) else ""
    suffix = " #Shorts"
    max_headline_len = 97 - len(emoji_prefix) - len(suffix)
    if len(clean_title) > max_headline_len:
        clean_title = clean_title[:max_headline_len].rsplit(" ", 1)[0]
    title = f"{emoji_prefix}{clean_title}{suffix}"
    if len(title) > 100:
        title = title[:97] + "..."
    if not title.strip():
        title = "✝️ Jesus Hears You • Daily Bible Verse #Shorts"

    # 2. Format Description with Prayer Magnet Call to Action
    verse_line = f"📖 Scripture: {verse_reference}\n" if verse_reference else ""
    script_snippet = f"\n🕊️ Devotional Message:\n{script.strip()}\n" if script else ""
    description = (
        f"✝️ Jesus Hears You • Daily Christian Devotional & Prayer\n\n"
        f"{verse_line}"
        f"\"{headline}\"\n"
        f"{script_snippet}\n"
        f"💬 Leave your prayer request below — we pray over every name! Type AMEN to claim this blessing today! 🙏✨\n"
        f"🔔 Subscribe to @JesusHearsYou for daily uplifting Bible verses and Christian prayers! ✝️\n"
        f"↗️ Share this blessing with someone who needs God's peace today! ❤️\n\n"
        f"#Shorts #JesusHearsYou #Jesus #BibleVerse #DailyDevotional #Christian #Faith #Prayer #GodIsGood #ChristianMotivation #HolySpirit"
    ).strip()

    # 3. High-Ranking Devotional Tags
    default_tags = [
        "Shorts", "JesusHearsYou", "Jesus", "BibleVerse", "ChristianShorts",
        "DailyDevotional", "Prayer", "Faith", "Inspiration", "Gospel", "God",
        "JesusChrist", "ChristianMotivation", "MorningPrayer", "BiblePromises",
        "BedtimePrayer", "ScriptureOfTheDay"
    ]
    if tags and isinstance(tags, list):
        for t in tags:
            if t not in default_tags:
                default_tags.append(t)

    _, _, _, default_privacy = get_credentials_for_channel("christian")
    status_privacy = privacy_status or default_privacy or "public"

    metadata = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": default_tags[:15],
            "categoryId": "22",  # People & Blogs
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en"
        },
        "status": {
            "privacyStatus": status_privacy,
            "selfDeclaredMadeForKids": False,
            "embeddable": True
        }
    }

    return _execute_resumable_upload(video_path, metadata, access_token, title)

def publish_news_to_youtube_shorts(video_path, headline, voice_script="", article_link=None, category="breaking", tags=None, privacy_status=None):
    """
    Uploads a 9:16 vertical Tamil news video directly as a YouTube Short:
    - High-CTR breaking news title with emojis & hashtags
    - Formats description with news headline, summary, channel credit & hashtags
    - Categorized under News & Politics (25)
    - Default audio and language: Tamil ('ta')
    - Returns: { "success": bool, "video_id": str, "url": str }
    """
    if not os.path.exists(video_path):
        return {"success": False, "error": f"Video file not found at {video_path}"}

    if not is_news_youtube_configured():
        return {
            "success": False,
            "error": "News YouTube credentials not configured (NEWS_YOUTUBE_CLIENT_ID, NEWS_YOUTUBE_CLIENT_SECRET, NEWS_YOUTUBE_REFRESH_TOKEN in .env)"
        }

    access_token = get_youtube_access_token(channel="news")
    if not access_token:
        return {"success": False, "error": "Failed to obtain YouTube access token for News channel."}

    # 1. Format High-CTR News Title (YouTube max 100 chars)
    clean_title = (headline or "").strip().rstrip(".! ")
    # Truncate the raw headline so the full title fits within 97 chars with suffix
    suffix = " #Shorts #TamilNews"
    emoji_prefix = "🔴 " if not any(clean_title.startswith(e) for e in ["🔴", "🚨", "⚡", "📢", "💥"]) else ""
    max_headline_len = 97 - len(emoji_prefix) - len(suffix)
    if len(clean_title) > max_headline_len:
        clean_title = clean_title[:max_headline_len].rsplit(" ", 1)[0]  # cut at word boundary
    title = f"{emoji_prefix}{clean_title}{suffix}"
    # Final safety clamp
    if len(title) > 100:
        title = title[:97] + "..."
    if not title.strip():
        title = "🔴 Tamil News Update #Shorts #TamilNews"

    # 2. Format News Description
    category_names = {
        "breaking": "முக்கிய செய்தி (Breaking News)",
        "local": "இலங்கைச் செய்தி (Sri Lanka News)",
        "world": "உலகச் செய்தி (World News)",
        "sports": "விளையாட்டுச் செய்தி (Sports)",
        "politics": "அரசியல் களம் (Politics)",
        "economy": "பொருளாதாரம் (Economy)",
        "history": "வரலாற்று மர்மம் (History)",
        "gk": "பொது அறிவு (Facts)",
        "science": "அறிவியல் உலகம் (Science)",
        "story": "ஞானச் சிறுகதை (Wisdom Story)"
    }
    cat_name = category_names.get(category, "முக்கிய செய்தி")
    body_text = f"\n🎙️ செய்தி சுருக்கம்:\n{voice_script.strip()}\n" if voice_script else ""
    source_line = f"\n🔗 மூலம்: {article_link}\n" if article_link else ""

    description = (
        f"🔴 செய்தி மையம் • 24/7 AI Tamil News Reels\n\n"
        f"📌 {headline}\n"
        f"🏷️ பிரிவு: {cat_name}\n"
        f"{body_text}"
        f"{source_line}\n"
        f"🔔 உடனுக்குடன் உண்மைச் செய்திகளை அறிய எமது சேனலை Subscribe செய்யுங்கள்! 👍\n"
        f"↗️ இந்த முக்கியமான செய்தியை மற்றவர்களுக்கும் பகிருங்கள்!\n\n"
        f"#Shorts #TamilNews #BreakingNews #SriLankaNews #TamilNaduNews #News #TamilShorts #SeithiMaiyam #TrendingNews"
    ).strip()

    # 3. High-Ranking Tamil News Tags
    default_tags = [
        "Shorts", "TamilNews", "BreakingNews", "SriLankaNews", "NewsToday",
        "SeithiMaiyam", "TamilNadu", "TrendingNews", "TamilShorts", "WorldNews",
        "AdaDeranaTamil", "Virakesari", "DailyNewsTamil", "NewsInTamil"
    ]
    if tags and isinstance(tags, list):
        for t in tags:
            if t not in default_tags:
                default_tags.append(t)

    _, _, _, default_privacy = get_credentials_for_channel("news")
    status_privacy = privacy_status or default_privacy or "public"

    metadata = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": default_tags[:15],
            "categoryId": "25",  # News & Politics
            "defaultLanguage": "ta",
            "defaultAudioLanguage": "ta"
        },
        "status": {
            "privacyStatus": status_privacy,
            "selfDeclaredMadeForKids": False,
            "embeddable": True
        }
    }

    return _execute_resumable_upload(video_path, metadata, access_token, title)

def get_youtube_auth_url(client_id, redirect_uri="urn:ietf:wg:oauth:2.0:oob"):
    """Generates user consent URL to obtain an OAuth authorization code."""
    from urllib.parse import urlencode
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl",
        "access_type": "offline",
        "prompt": "consent"
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

def exchange_auth_code_for_refresh_token(client_id, client_secret, auth_code, redirect_uri="urn:ietf:wg:oauth:2.0:oob"):
    """Exchanges an authorization code for a permanent refresh token."""
    url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    resp = requests.post(url, data=payload, timeout=15)
    if resp.status_code == 200:
        return resp.json().get("refresh_token")
    else:
        print(f"Error exchanging auth code: {resp.status_code} {resp.text}")
        return None
