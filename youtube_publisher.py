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
    ENABLE_YOUTUBE_CHRISTIAN_PUBLISH
)

_cached_access_token = None
_token_expiry = 0

_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*"
})

def is_youtube_configured():
    """
    Checks if valid YouTube API credentials are provided.
    Requires CLIENT_ID, CLIENT_SECRET, and REFRESH_TOKEN.
    """
    return bool(
        YOUTUBE_CLIENT_ID
        and YOUTUBE_CLIENT_SECRET
        and YOUTUBE_REFRESH_TOKEN
        and len(YOUTUBE_CLIENT_ID.strip()) > 5
        and len(YOUTUBE_CLIENT_SECRET.strip()) > 5
        and len(YOUTUBE_REFRESH_TOKEN.strip()) > 5
    )

def get_youtube_access_token():
    """
    Exchanges the permanent OAuth refresh token for a short-lived access token.
    Caches token in memory until 60 seconds before expiration.
    """
    global _cached_access_token, _token_expiry
    now = time.time()
    if _cached_access_token and now < _token_expiry:
        return _cached_access_token

    if not is_youtube_configured():
        return None

    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": YOUTUBE_CLIENT_ID,
        "client_secret": YOUTUBE_CLIENT_SECRET,
        "refresh_token": YOUTUBE_REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }

    try:
        resp = _session.post(token_url, data=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            _cached_access_token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            _token_expiry = now + expires_in - 60
            return _cached_access_token
        else:
            print(f"Notice: Failed to refresh YouTube OAuth token: {resp.status_code} {resp.text}")
            return None
    except Exception as e:
        print(f"Notice: YouTube OAuth refresh error: {e}")
        return None

def publish_to_youtube_shorts(video_path, headline, script="", verse_reference="", tags=None, privacy_status=None):
    """
    Uploads a 9:16 vertical video directly as a YouTube Short via YouTube Data API v3 Resumable Upload:
    - Sets title (max 100 chars, includes #Shorts)
    - Formats devotional description with scripture, prayer & hashtags
    - Categorized under People & Blogs (22)
    - Returns: { "success": bool, "video_id": str, "url": str }
    """
    if not os.path.exists(video_path):
        return {"success": False, "error": f"Video file not found at {video_path}"}

    if not is_youtube_configured():
        return {
            "success": False,
            "error": "YouTube API credentials not configured (YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN in .env)"
        }

    access_token = get_youtube_access_token()
    if not access_token:
        return {"success": False, "error": "Failed to obtain YouTube access token from refresh token."}

    # 1. Format Title (YouTube max length: 100 characters)
    clean_title = headline.strip().rstrip(".! ")
    if "#Shorts" not in clean_title and "#shorts" not in clean_title:
        title = f"{clean_title} #Shorts"
    else:
        title = clean_title
    if len(title) > 95:
        title = title[:90] + "... #Shorts"

    # 2. Format Description
    verse_line = f"📖 Scripture: {verse_reference}\n" if verse_reference else ""
    script_snippet = f"\n🕊️ Devotional Message:\n{script.strip()}\n" if script else ""
    description = (
        f"✝️ Jesus Hears You • Daily Christian Devotional\n\n"
        f"{verse_line}"
        f"\"{headline}\"\n"
        f"{script_snippet}\n"
        f"💬 Type AMEN to claim this blessing today! 🕊️✨\n"
        f"🔔 Subscribe to @JesusHearsYou for daily uplifting Bible verses and Christian prayers! ✝️\n\n"
        f"#Shorts #JesusHearsYou #Jesus #BibleVerse #DailyDevotional #Christian #Faith #Prayer #GodIsGood"
    ).strip()

    # 3. Tags
    default_tags = [
        "Shorts", "JesusHearsYou", "Jesus", "BibleVerse", "ChristianShorts",
        "DailyDevotional", "Prayer", "Faith", "Inspiration", "Gospel", "God"
    ]
    if tags and isinstance(tags, list):
        for t in tags:
            if t not in default_tags:
                default_tags.append(t)

    status_privacy = privacy_status or YOUTUBE_PRIVACY_STATUS or "public"

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

    file_size = os.path.getsize(video_path)
    init_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
    init_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Length": str(file_size),
        "X-Upload-Content-Type": "video/mp4"
    }

    print(f"📺 Initializing YouTube Shorts Resumable Upload for: '{title}' ({file_size / (1024*1024):.1f} MB)...")
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

        # 4. Stream Video Binary Payload
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
                "title": title
            }
        else:
            return {
                "success": False,
                "error": f"YouTube video upload failed ({upload_resp.status_code}): {upload_resp.text[:250]}"
            }

    except Exception as e:
        return {"success": False, "error": f"YouTube upload exception: {str(e)}"}

def get_youtube_auth_url(client_id, redirect_uri="urn:ietf:wg:oauth:2.0:oob"):
    """Generates user consent URL to obtain an OAuth authorization code."""
    from urllib.parse import urlencode
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/youtube.upload",
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
