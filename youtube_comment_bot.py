import os
import json
import time
import re
import requests
from config import (
    BASE_DIR,
    GEMINI_API_KEY,
    CHRISTIAN_HISTORY_FILE
)
from youtube_publisher import (
    get_youtube_access_token,
    is_youtube_configured,
    is_news_youtube_configured
)
from fb_comment_bot import (
    record_replied_comment,
    is_comment_already_replied,
    generate_pastoral_ai_reply,
    load_replied_comments
)

_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*"
})

YOUTUBE_SEED_PRAYER_COMMENTS = [
    "🙏 Heavenly Father, I pray for everyone reading this right now. If you need a breakthrough in your health, finances, or family this week, write AMEN and your prayer request below. Jesus hears you! ❤️",
    "🕊️ Jesus said: 'Come to Me, all you who are weary, and I will give you rest.' Whatever burden you carried into today, leave it here in the comments. Type AMEN to surrender it! 🙏✨",
    "✨ May God open doors for you this week that no man can shut. If you receive this divine favor over your household, declare AMEN and share with someone you love! ❤️",
    "🛡️ Praying Psalm 91 protection over every single person watching this right now. No weapon formed against your family shall prosper. Type AMEN in Jesus' mighty name! 🙏",
    "💖 God sees your silent tears and hears your quiet prayers. Healing, unexpected peace, and restoration are coming to your life. Type AMEN to claim it! ✝️"
]

YOUTUBE_SEED_NEWS_COMMENTS = [
    "செய்தி மையம் AI: உடனுக்குடன் உண்மைச் செய்திகளைப் பெற பின்தொடருங்கள்! உங்கள் கருத்துக்களை கீழே பகிருங்கள். 👇",
    "முக்கிய நிகழ்வுகள் மற்றும் உண்மைச் செய்திகள் குறித்த உங்கள் கருத்துக்களை கீழே பதிவிடுங்கள்! 🇱🇰",
    "செய்தி மையம் AI: இலங்கையின் முக்கிய செய்திகள் உடனுக்குடன். உங்கள் ஆதரவிற்கு நன்றி! 🙏"
]

def fetch_recent_youtube_video_ids(channel="christian", max_videos=8):
    """
    Retrieves video IDs of recently posted YouTube Shorts:
    1. Checks christian_history.json (for Christian channel) or reels_history.json (for News).
    2. Also queries YouTube Search API if possible.
    """
    video_ids = []
    
    if channel == "christian":
        h_file = CHRISTIAN_HISTORY_FILE
    else:
        h_file = os.path.join(BASE_DIR, "reels_history.json")

    if os.path.exists(h_file):
        try:
            with open(h_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            if isinstance(history, list):
                for item in history:
                    vid = item.get("youtube_video_id")
                    if vid and str(vid) not in video_ids:
                        video_ids.append(str(vid))
                    elif item.get("youtube_url"):
                        m = re.search(r'(?:v=|shorts/|youtu\.be/)([a-zA-Z0-9_-]{11})', item.get("youtube_url"))
                        if m and m.group(1) not in video_ids:
                            video_ids.append(m.group(1))
        except Exception as e:
            print(f"Notice: Failed to load YouTube video IDs from {h_file}: {e}")

    # Fallback to search API if history has fewer than max_videos
    token = get_youtube_access_token(channel)
    if token and len(video_ids) < max_videos:
        try:
            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&forMine=true&type=video&maxResults={max_videos}&order=date"
            headers = {"Authorization": f"Bearer {token}"}
            resp = _session.get(url, headers=headers, timeout=12)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                for it in items:
                    vid = it.get("id", {}).get("videoId")
                    if vid and vid not in video_ids:
                        video_ids.append(vid)
        except Exception:
            pass

    return video_ids[:max_videos]


def fetch_comments_for_youtube_video(video_id, access_token):
    """
    Fetches comment threads on a YouTube video via YouTube Data API v3.
    API: GET https://www.googleapis.com/youtube/v3/commentThreads
    """
    url = f"https://www.googleapis.com/youtube/v3/commentThreads?part=snippet,replies&videoId={video_id}&maxResults=25&textFormat=plainText"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    try:
        resp = _session.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            return resp.json().get("items", []), None
        elif resp.status_code == 403:
            err_data = resp.json().get("error", {})
            reasons = [e.get("reason") for e in err_data.get("errors", [])]
            if "insufficientPermissions" in reasons or "ACCESS_TOKEN_SCOPE_INSUFFICIENT" in str(resp.text):
                return [], "insufficient_scope"
            else:
                print(f"Notice: YouTube API commentThreads 403 for video {video_id}: {resp.text}")
        else:
            print(f"Notice: YouTube commentThreads error {resp.status_code} for video {video_id}: {resp.text}")
    except Exception as e:
        print(f"Notice: Exception fetching YouTube comments for {video_id}: {e}")
    return [], None


def post_youtube_comment_reply(parent_id, reply_text, access_token):
    """
    Posts a reply directly underneath a viewer's YouTube comment thread.
    API: POST https://www.googleapis.com/youtube/v3/comments?part=snippet
    """
    url = "https://www.googleapis.com/youtube/v3/comments?part=snippet"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "snippet": {
            "parentId": parent_id,
            "textOriginal": reply_text
        }
    }
    try:
        resp = _session.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code in (200, 201):
            return {"success": True, "reply_id": resp.json().get("id")}
        else:
            return {"success": False, "error": resp.text, "status_code": resp.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


def post_youtube_seed_comment(video_id, channel="christian", category_id=None):
    """
    Posts an immediate high-engagement seed prayer / discussion comment from the channel
    right after a Short is published to YouTube. Drives immediate comment velocity.
    API: POST https://www.googleapis.com/youtube/v3/commentThreads?part=snippet
    """
    if not video_id:
        return {"success": False, "error": "No video_id provided."}

    token = get_youtube_access_token(channel)
    if not token:
        return {"success": False, "error": "YouTube access token not available."}

    import random
    if channel == "news":
        seed_msg = random.choice(YOUTUBE_SEED_NEWS_COMMENTS)
    else:
        seed_msg = random.choice(YOUTUBE_SEED_PRAYER_COMMENTS)

    url = "https://www.googleapis.com/youtube/v3/commentThreads?part=snippet"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {
                "snippet": {
                    "textOriginal": seed_msg
                }
            }
        }
    }

    try:
        resp = _session.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code in (200, 201):
            comm_data = resp.json()
            comm_id = comm_data.get("id")
            print(f"🎉 YouTube Seed Comment posted on Short {video_id}: ID {comm_id}")
            record_replied_comment(
                comment_id=comm_id,
                original_text="Seed YouTube Booster",
                reply_text=seed_msg,
                commenter_name="Channel Owner",
                post_id=video_id,
                reply_type="youtube_seed"
            )
            return {"success": True, "comment_id": comm_id}
        else:
            print(f"Notice: Failed to post YouTube seed comment: {resp.text}")
            return {"success": False, "error": resp.text, "status_code": resp.status_code}
    except Exception as e:
        print(f"Notice: YouTube seed comment exception: {e}")
        return {"success": False, "error": str(e)}


def generate_news_ai_reply(comment_text, commenter_name=None, headline=None):
    """
    Uses Google Gemini to craft a polite, professional, neutral Tamil news anchor reply.
    """
    if not comment_text or not comment_text.strip():
        return None

    clean_text = comment_text.strip()
    name_str = f" from {commenter_name}" if commenter_name else ""
    prompt = f"""
You are the professional news anchor and editor for the Sri Lankan Tamil News channel "செய்தி மையம் AI".
A viewer{name_str} commented on our breaking news YouTube Short:
"{clean_text}"

News context: {headline or 'Breaking Sri Lanka & World Tamil News'}

Write a polite, engaging, and professional reply in natural Tamil:
1. Thank them politely for their viewpoint and engaging with செய்தி மையம்.
2. Maintain strict editorial neutrality and journalistic ethics.
3. Encourage them to stay tuned for live verified updates.
4. Keep it short (20 to 35 words max in pure Tamil).
5. STRICT: Do not mention you are an AI or bot!

Return ONLY the reply text, no quotes, no extra formatting.
"""
    if GEMINI_API_KEY:
        models = ["gemini-flash-lite-latest", "gemini-flash-latest"]
        for model in models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 100}
                }
                resp = _session.post(url, json=payload, timeout=12)
                if resp.status_code == 200:
                    ans = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    ans = re.sub(r'^["\']|["\']$', '', ans).strip()
                    if ans:
                        return ans
            except Exception as e:
                print(f"Notice: Gemini news reply notice ({model}): {e}")

    # Fallback Tamil template
    return "செய்தி மையம் AI-ஐ பின்தொடர்வதற்கு நன்றி! உடனுக்குடன் உண்மைச் செய்திகளைப் பெற பின்தொடருங்கள். 🙏"


def run_youtube_comment_reply_cycle(channel="christian", max_replies_per_cycle=10):
    """
    Scans recent YouTube Shorts for new viewer comments,
    generates personalized AI replies with Gemini,
    and publishes replies automatically via YouTube Data API v3!
    """
    if not is_youtube_configured(channel):
        return {
            "success": False,
            "error": f"YouTube API credentials not configured for {channel} channel."
        }

    token = get_youtube_access_token(channel)
    if not token:
        return {
            "success": False,
            "error": f"Could not obtain YouTube access token for {channel}."
        }

    channel_display = "Jesus Hears You" if channel == "christian" else "செய்தி மையம்"
    print(f"\n📺 ========================================================")
    print(f"📺 YouTube AI Comment Replier: Scanning recent Shorts for '{channel_display}'...")
    print(f"📺 ========================================================\n")

    video_ids = fetch_recent_youtube_video_ids(channel=channel, max_videos=8)
    if not video_ids:
        print("Notice: No published YouTube video IDs found in history or search.")
        return {"success": True, "replied_count": 0, "message": "No active YouTube videos found to scan."}

    replied_count = 0
    results = []

    for vid in video_ids:
        if replied_count >= max_replies_per_cycle:
            break

        threads, err = fetch_comments_for_youtube_video(vid, token)
        if err == "insufficient_scope":
            print("\n⚠️ [YouTube Comment Bot] Scope Notice: The current YouTube OAuth token does not have 'youtube.force-ssl' permission.")
            print("👉 Please run: python setup_youtube.py once to grant comment management access.\n")
            return {
                "success": False,
                "error": "insufficient_scope",
                "message": "YouTube OAuth token requires 'youtube.force-ssl'. Run 'python setup_youtube.py' to update.",
                "replied_count": 0
            }

        for thread in threads:
            if replied_count >= max_replies_per_cycle:
                break

            top_comment = thread.get("snippet", {}).get("topLevelComment", {})
            comm_snippet = top_comment.get("snippet", {})
            cid = top_comment.get("id") or thread.get("id")
            thread_id = thread.get("id")
            text = comm_snippet.get("textDisplay", "").strip()
            sender_name = comm_snippet.get("authorDisplayName", "Viewer")

            # 1. Skip if already replied
            if is_comment_already_replied(cid) or is_comment_already_replied(thread_id):
                continue

            # 2. Skip if comment was authored by our own channel (verified via authorChannelId)
            # Or if text is an existing seed comment
            if any(sc in text for sc in ["Heavenly Father, I pray", "Jesus said: 'Come to Me", "செய்தி மையம் AI-ஐ"]):
                continue

            # 3. Skip empty comments
            if not text:
                continue

            print(f"💬 Found new YouTube comment on Video {vid} from {sender_name}: '{text[:60]}'...")

            # 4. Generate AI reply
            if channel == "christian":
                ai_reply = generate_pastoral_ai_reply(text, commenter_name=sender_name)
            else:
                ai_reply = generate_news_ai_reply(text, commenter_name=sender_name)

            if not ai_reply:
                continue

            print(f"🤖 Generated YouTube AI Reply: '{ai_reply}'")

            # 5. Post Public Reply underneath the comment thread
            pub_res = post_youtube_comment_reply(thread_id, ai_reply, token)

            if pub_res.get("success"):
                record_replied_comment(
                    comment_id=cid,
                    original_text=text,
                    reply_text=ai_reply,
                    commenter_name=sender_name,
                    post_id=f"yt_{vid}",
                    reply_type="youtube_public"
                )
                replied_count += 1
                results.append({
                    "comment_id": cid,
                    "platform": "YouTube",
                    "sender": sender_name,
                    "comment": text,
                    "reply": ai_reply,
                    "status": "Replied Successfully"
                })
                print(f"✅ Successfully replied to YouTube viewer {sender_name}!")
            else:
                err_msg = pub_res.get("error", "")
                results.append({
                    "comment_id": cid,
                    "platform": "YouTube",
                    "sender": sender_name,
                    "comment": text,
                    "reply": ai_reply,
                    "status": f"Failed: {err_msg[:80]}"
                })
                print(f"⚠️ Could not post YouTube reply: {err_msg}")

            time.sleep(1.5)  # Safe rate-limiting pause between YouTube API calls

    print(f"\n🎉 YouTube comment reply cycle complete! Replied to {replied_count} comments.\n")
    return {
        "success": True,
        "replied_count": replied_count,
        "results": results
    }


def get_youtube_comments_history():
    """
    Returns history of comments replied to on YouTube.
    """
    data = load_replied_comments()
    replies = data.get("replies", [])
    yt_replies = [r for r in replies if r.get("reply_type", "").startswith("youtube") or str(r.get("post_id", "")).startswith("yt_")]
    return yt_replies


if __name__ == "__main__":
    import sys
    ch = sys.argv[1] if len(sys.argv) > 1 else "christian"
    print(f"Testing YouTube comment replier for channel '{ch}'...")
    res = run_youtube_comment_reply_cycle(channel=ch)
    print("Result:", res)
