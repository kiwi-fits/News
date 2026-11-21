import os
import json
import time
import re
import requests
from config import (
    BASE_DIR,
    GEMINI_API_KEY,
    CHRISTIAN_FB_PAGE_ID,
    CHRISTIAN_FB_ACCESS_TOKEN,
    FB_PAGE_ID,
    FB_ACCESS_TOKEN,
    CHRISTIAN_HISTORY_FILE
)

REPLIED_COMMENTS_FILE = os.path.join(BASE_DIR, "replied_comments.json")

_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*"
})

def load_replied_comments():
    """
    Loads registry of all comments already answered by the AI bot.
    Never replies twice to the same comment.
    """
    if os.path.exists(REPLIED_COMMENTS_FILE):
        try:
            with open(REPLIED_COMMENTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            print(f"Notice: Failed to load replied comments: {e}")
    return {"replied_comment_ids": [], "replies": []}

def save_replied_comments(data):
    """
    Persists registry of answered comments to disk.
    """
    try:
        with open(REPLIED_COMMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Notice: Failed to save replied comments: {e}")

def record_replied_comment(comment_id, original_text, reply_text, commenter_name=None, post_id=None, reply_type="public"):
    """
    Logs an answered comment to prevent duplicate responses.
    """
    data = load_replied_comments()
    cid_str = str(comment_id).strip()
    if cid_str not in data.get("replied_comment_ids", []):
        data.setdefault("replied_comment_ids", []).append(cid_str)

    data.setdefault("replies", []).insert(0, {
        "comment_id": cid_str,
        "post_id": str(post_id or ""),
        "commenter_name": commenter_name or "Viewer",
        "comment_text": original_text,
        "reply_text": reply_text,
        "reply_type": reply_type,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

    if len(data["replies"]) > 500:
        data["replies"] = data["replies"][:500]

    save_replied_comments(data)

def is_comment_already_replied(comment_id):
    data = load_replied_comments()
    return str(comment_id).strip() in data.get("replied_comment_ids", [])

def generate_pastoral_ai_reply(comment_text, commenter_name=None, reel_context=None):
    """
    Uses Google Gemini to craft a warm, empathetic, compassionate Christian pastoral reply:
    - If user says 'Amen', 'Praise God', or 'Hallelujah': responds with a warm, personal blessing.
    - If user shares a prayer request (sickness, pain, sorrow, job, exams): writes a gentle, specific prayer lifting them up to Jesus.
    - If user asks about the Bible or verse: provides encouraging Biblical wisdom.
    - Short & heartfelt (1-3 sentences max).
    - NEVER mentions 'AI', 'bot', or robotic greetings.
    """
    if not comment_text or not comment_text.strip():
        return None

    clean_text = comment_text.strip()
    name_str = f" from {commenter_name}" if commenter_name else ""

    # Quick smart fallback rules if Gemini key is offline
    prompt = f"""
You are the warm, compassionate pastoral voice for the Christian Facebook page "Jesus Hears You".
A viewer{name_str} just left this comment on our devotional Reel:
"{clean_text}"

Reel context: {reel_context or 'Daily scripture promise & Christian prayer'}

Write a personal, faith-filled, and comforting reply in natural English:
1. If they said "Amen", "Praise the Lord", or similar: Send a warm, joyful blessing for their home and day.
2. If they asked for prayer (sickness, family, sadness, loneliness, exams): Write a heartfelt, specific 2-sentence prayer in Jesus' name lifting up their need.
3. If they asked a question about God or scripture: Offer gentle, encouraging Biblical reassurance.
4. Keep it short (25 to 45 words, 1-3 sentences).
5. Use warm faith emojis (🙏, ✨, 🕊️, 💖).
6. STRICT: NEVER say you are an AI or bot! Speak naturally with pastoral love.

Return ONLY the reply text, no quotes, no extra formatting.
"""
    if GEMINI_API_KEY:
        models = ["gemini-flash-lite-latest", "gemini-flash-latest"]
        for model in models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.8, "maxOutputTokens": 120}
                }
                resp = _session.post(url, json=payload, timeout=12)
                if resp.status_code == 200:
                    data = resp.json()
                    ans = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    # Clean up quotes if present
                    ans = re.sub(r'^["\']|["\']$', '', ans).strip()
                    if ans:
                        return ans
            except Exception as e:
                print(f"Notice: Gemini comment reply notice ({model}): {e}")

    # Fallback pastoral templates if Gemini is unavailable
    lower = clean_text.lower()
    if any(w in lower for w in ["amen", "praise", "hallelujah", "thank you", "thanks"]):
        blessings = [
            "God bless you richly! May His divine peace, love, and favor fill your home and heart today! 🙏✨",
            "Amen and Amen! Stand firm on His promises today—the Lord is fighting your battles! 🕊️💖",
            "Blessings to you! May the grace of our Lord Jesus Christ surround your family with unshakeable peace! 🌟🙏"
        ]
        import random
        return random.choice(blessings)
    elif any(w in lower for w in ["pray", "sick", "heal", "help", "pain", "sad", "mother", "father", "son", "daughter"]):
        return "Lord Jesus, we lift this precious need to You. Touch them with Your divine healing and comfort, replace every worry with peace, and make a way where there seems to be no way. In Jesus' mighty name, Amen. We are praying with you! 🙏🕊️"
    else:
        return "Thank you for watching and sharing your heart with us! May the Lord bless you, protect your steps, and fill your day with His everlasting joy! ✝️🕊️"

def fetch_recent_christian_video_ids(max_videos=5):
    """
    Retrieves video IDs of recently posted devotional reels:
    1. Reads from christian_history.json
    2. Queries Facebook Graph API for recent published videos
    """
    video_ids = []
    # From history
    if os.path.exists(CHRISTIAN_HISTORY_FILE):
        try:
            with open(CHRISTIAN_HISTORY_FILE, "r", encoding="utf-8") as f:
                hist = json.load(f)
                if isinstance(hist, list):
                    for h in hist:
                        vid = h.get("fb_video_id")
                        if vid and str(vid) not in video_ids:
                            video_ids.append(str(vid))
        except Exception:
            pass

    # From Facebook API
    if CHRISTIAN_FB_PAGE_ID and CHRISTIAN_FB_ACCESS_TOKEN:
        try:
            url = f"https://graph.facebook.com/v19.0/{CHRISTIAN_FB_PAGE_ID}/videos?fields=id,title&limit={max_videos}&access_token={CHRISTIAN_FB_ACCESS_TOKEN}"
            resp = _session.get(url, timeout=12)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                for v in data:
                    vid = str(v.get("id"))
                    if vid and vid not in video_ids:
                        video_ids.append(vid)
        except Exception as e:
            print(f"Notice: Failed to fetch videos from FB API: {e}")

    return video_ids[:max_videos]

def fetch_comments_for_video(video_id, access_token):
    """
    Fetches comments on a Facebook video/reel via Graph API.
    """
    url = f"https://graph.facebook.com/v19.0/{video_id}/comments?fields=id,message,from,created_time&limit=25&access_token={access_token}"
    try:
        resp = _session.get(url, timeout=12)
        if resp.status_code == 200:
            return resp.json().get("data", [])
        else:
            print(f"Notice: Failed to fetch comments for video {video_id}: {resp.status_code} {resp.text[:100]}")
    except Exception as e:
        print(f"Notice: Exception fetching comments: {e}")
    return []

def post_public_comment_reply(comment_id, reply_text, access_token):
    """
    Posts a public reply directly underneath the viewer's comment.
    API: POST https://graph.facebook.com/v19.0/{comment_id}/comments
    """
    url = f"https://graph.facebook.com/v19.0/{comment_id}/comments"
    payload = {
        "message": reply_text,
        "access_token": access_token
    }
    try:
        resp = _session.post(url, data=payload, timeout=15)
        if resp.status_code in (200, 201):
            return {"success": True, "reply_id": resp.json().get("id")}
        else:
            return {"success": False, "error": resp.text, "status_code": resp.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}

def post_private_messenger_reply(comment_id, reply_text, access_token):
    """
    Sends a DIRECT private Messenger message to the person who commented!
    Meta-approved feature: Allows Pages to send one direct private message
    in response to any post/reel comment.
    API: POST https://graph.facebook.com/v19.0/{comment_id}/private_replies
    """
    url = f"https://graph.facebook.com/v19.0/{comment_id}/private_replies"
    payload = {
        "message": reply_text,
        "access_token": access_token
    }
    try:
        resp = _session.post(url, data=payload, timeout=15)
        if resp.status_code in (200, 201):
            return {"success": True, "result": resp.json()}
        else:
            return {"success": False, "error": resp.text, "status_code": resp.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}

def run_christian_comment_reply_cycle(send_private_dms=False, max_replies_per_cycle=10):
    """
    Scans recent 'Jesus Hears You' reels for new viewer comments,
    generates personalized pastoral replies with Gemini,
    and publishes replies automatically!
    """
    if not CHRISTIAN_FB_PAGE_ID or not CHRISTIAN_FB_ACCESS_TOKEN:
        return {
            "success": False,
            "error": "Facebook Page credentials not configured for Jesus Hears You."
        }

    print("\n✝️ ========================================================")
    print("✝️ Jesus Hears You AI Comment Responder: Scanning for new comments...")
    print("✝️ ========================================================\n")

    video_ids = fetch_recent_christian_video_ids(max_videos=6)
    if not video_ids:
        print("Notice: No published video IDs found in history or Facebook API.")
        return {"success": True, "replied_count": 0, "message": "No active videos found to scan."}

    replied_count = 0
    results = []

    for vid in video_ids:
        if replied_count >= max_replies_per_cycle:
            break

        comments = fetch_comments_for_video(vid, CHRISTIAN_FB_ACCESS_TOKEN)
        for comm in comments:
            cid = comm.get("id")
            text = comm.get("message", "").strip()
            sender = comm.get("from", {})
            sender_id = sender.get("id")
            sender_name = sender.get("name", "Friend")

            # 1. Skip if already replied
            if is_comment_already_replied(cid):
                continue

            # 2. Skip if comment was made by the Page itself
            if sender_id and str(sender_id) == str(CHRISTIAN_FB_PAGE_ID):
                continue

            # 3. Skip empty comments
            if not text:
                continue

            print(f"💬 Found new comment on Video {vid} from {sender_name}: '{text[:60]}'...")

            # 4. Generate AI pastoral reply with Gemini
            ai_reply = generate_pastoral_ai_reply(text, commenter_name=sender_name)
            if not ai_reply:
                continue

            print(f"🤖 Generated AI Reply: '{ai_reply}'")

            # 5. Post Public Reply
            pub_res = post_public_comment_reply(cid, ai_reply, CHRISTIAN_FB_ACCESS_TOKEN)
            
            # 6. Optionally Send Private Messenger DM (if enabled)
            private_res = None
            if send_private_dms:
                private_msg = f"God bless you {sender_name}! Thank you for watching 'Jesus Hears You'. Here is our prayer for you: {ai_reply}"
                private_res = post_private_messenger_reply(cid, private_msg, CHRISTIAN_FB_ACCESS_TOKEN)

            if pub_res.get("success"):
                record_replied_comment(
                    comment_id=cid,
                    original_text=text,
                    reply_text=ai_reply,
                    commenter_name=sender_name,
                    post_id=vid,
                    reply_type="public"
                )
                replied_count += 1
                results.append({
                    "comment_id": cid,
                    "sender": sender_name,
                    "comment": text,
                    "reply": ai_reply,
                    "status": "Replied Successfully"
                })
                print(f"✅ Successfully replied to {sender_name}!")
            else:
                err_msg = pub_res.get("error", "")
                results.append({
                    "comment_id": cid,
                    "sender": sender_name,
                    "comment": text,
                    "reply": ai_reply,
                    "status": f"Failed: {err_msg[:80]}"
                })
                print(f"⚠️ Could not post reply: {err_msg}")

            time.sleep(1.5)  # Safe rate-limiting pause between comments

    print(f"\n🎉 Comment reply cycle complete! Replied to {replied_count} comments.\n")
    return {
        "success": True,
        "replied_count": replied_count,
        "results": results
    }
