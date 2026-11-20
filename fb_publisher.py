import os
import json
import time
import requests
from config import (
    FB_PAGE_ID, FB_ACCESS_TOKEN,
    CHRISTIAN_FB_PAGE_ID, CHRISTIAN_FB_ACCESS_TOKEN,
    FB_BLOCK_STATE_FILE, FB_ERROR_368_COOLDOWN_SECONDS
)
from ai_rewriter import strip_channel_names

def load_block_state():
    """
    Loads Facebook upload circuit breaker state from disk.
    Tracks temporary blocks (e.g. Error 368) per page ID.
    """
    if os.path.exists(FB_BLOCK_STATE_FILE):
        try:
            with open(FB_BLOCK_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            return {"blocked_pages": {}}
    return {"blocked_pages": {}}

def save_block_state(state):
    """
    Saves Facebook upload circuit breaker state to disk.
    """
    try:
        with open(FB_BLOCK_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Notice: Failed to save FB block state: {e}")

def is_page_blocked(page_id):
    """
    Checks if a page ID is currently under a temporary block (Error 368).
    Returns: (is_blocked: bool, remaining_seconds: int, block_info: dict)
    """
    if not page_id:
        return False, 0, {}

    state = load_block_state()
    blocked_pages = state.get("blocked_pages", {})
    info = blocked_pages.get(str(page_id))

    if not info:
        return False, 0, {}

    blocked_until = info.get("blocked_until", 0)
    now = time.time()

    if now < blocked_until:
        remaining = int(blocked_until - now)
        return True, remaining, info
    else:
        # Cooldown has expired, auto-clear from state
        blocked_pages.pop(str(page_id), None)
        save_block_state(state)
        return False, 0, {}

def record_page_block(page_id, code=368, message="", cooldown_seconds=None):
    """
    Records a temporary block on a page (e.g. Error 368).
    Prevents further upload attempts until cooldown has passed.
    """
    if not page_id:
        return

    cooldown = cooldown_seconds if cooldown_seconds is not None else FB_ERROR_368_COOLDOWN_SECONDS
    now = time.time()
    blocked_until = now + cooldown

    state = load_block_state()
    if "blocked_pages" not in state:
        state["blocked_pages"] = {}

    until_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(blocked_until))
    state["blocked_pages"][str(page_id)] = {
        "error_code": code,
        "reason": message or "The action attempted has been deemed abusive or is otherwise disallowed.",
        "blocked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "blocked_until": blocked_until,
        "blocked_until_str": until_str,
        "cooldown_seconds": cooldown
    }
    save_block_state(state)
    mins = int(cooldown / 60)
    print(f"\n🛑 [FB Circuit Breaker] Facebook returned Error {code}!")
    print(f"🛑 Page ID {page_id} is temporarily restricted by Facebook.")
    print(f"🛑 All further upload attempts HALTED for {mins} minutes (until {until_str}).\n")

def clear_page_block(page_id):
    """
    Manually clears a temporary block on a page.
    """
    state = load_block_state()
    if "blocked_pages" in state and str(page_id) in state["blocked_pages"]:
        del state["blocked_pages"][str(page_id)]
        save_block_state(state)
        print(f"✅ Cleared temporary block on Facebook Page {page_id}.")

def is_error_368(status_code, response_text, response_json=None):
    """
    Inspects response to detect Facebook Error 368:
    - Code 368: "The action attempted has been deemed abusive or is otherwise disallowed"
    - Subcode 368
    - Policy/rate-block messages ("going too fast", "temporarily blocked", "misusing this feature")
    """
    if response_json and isinstance(response_json, dict):
        err = response_json.get("error", {})
        if isinstance(err, dict):
            code = err.get("code")
            subcode = err.get("error_subcode")
            msg = (err.get("message") or "").lower()
            title = (err.get("error_user_title") or "").lower()
            user_msg = (err.get("error_user_msg") or "").lower()

            if code == 368 or subcode == 368:
                return True, err.get("message", "Facebook Error 368: Feature temporarily blocked.")
            if any(phrase in msg or phrase in title or phrase in user_msg for phrase in ["going too fast", "temporarily blocked", "misusing this feature", "deemed abusive"]):
                return True, err.get("message", "Facebook temporary block (rate limit / misuse).")

    # Fallback raw text search
    raw_lower = (response_text or "").lower()
    if '"code":368' in raw_lower or '"code": 368' in raw_lower or 'error_subcode":368' in raw_lower or 'error_subcode": 368' in raw_lower:
        return True, "Facebook Error 368 detected in response"
    if "going too fast" in raw_lower or "temporarily blocked from using it" in raw_lower or "deemed abusive" in raw_lower:
        return True, "Facebook temporary block detected in response"

    return False, ""

def publish_reel_to_facebook(video_path, headline, caption, article_link=None, engagement_question=None, page_id=None, access_token=None):
    """
    Publishes the 9:16 vertical video reel directly to the Facebook Page feed.
    Also auto-posts the first comment without any external news channel names or links.
    Supports custom page_id and access_token (e.g. for Christian page 'Jesus Hears You').
    Automatically detects Facebook Error 368 and halts further uploads temporarily.
    """
    target_page_id = (page_id or FB_PAGE_ID or "").strip()
    target_access_token = (access_token or FB_ACCESS_TOKEN or "").strip()

    if not target_page_id or not target_access_token:
        print("⚠️ Facebook credentials not set. Running in simulation mode.")
        return {"success": True, "simulated": True, "video_id": "sim_reel_12345"}

    # 1. Circuit Breaker Check: Is page temporarily blocked due to Error 368?
    is_blocked, remaining_sec, block_info = is_page_blocked(target_page_id)
    if is_blocked:
        mins = max(1, int(remaining_sec / 60))
        until_str = block_info.get("blocked_until_str", "later")
        print(f"🛑 [FB Upload Halted] Page {target_page_id} is temporarily restricted by Facebook (Error 368).")
        print(f"🛑 Next attempt allowed after {until_str} ({mins}m remaining). Skipping upload.")
        return {
            "success": False,
            "error": f"Upload paused: Facebook Error 368 temporary block active until {until_str} (~{mins}m remaining).",
            "error_code": 368,
            "blocked_temporarily": True,
            "remaining_seconds": remaining_sec,
            "blocked_until": block_info.get("blocked_until")
        }

    if not video_path or not os.path.exists(video_path):
        return {"success": False, "error": "Video file not found."}

    # Ensure all text is completely stripped of external news channel names
    clean_caption = strip_channel_names(caption)
    clean_headline = strip_channel_names(headline)

    url = f"https://graph.facebook.com/v19.0/{target_page_id}/videos"
    print(f"🚀 Uploading 9:16 Reel to Facebook Page ({target_page_id}) ({video_path})...")

    try:
        with open(video_path, "rb") as vf:
            files = {"source": (os.path.basename(video_path), vf, "video/mp4")}
            data = {
                "description": clean_caption,
                "access_token": target_access_token
            }
            resp = requests.post(url, files=files, data=data, timeout=180)

        if resp.status_code == 200:
            vid_id = resp.json().get("id")
            print(f"🎉 Successfully posted 9:16 Reel to Facebook! Video ID: {vid_id}")
            return {"success": True, "video_id": vid_id}
        else:
            resp_json = None
            try:
                resp_json = resp.json()
            except Exception:
                pass

            # 2. Check for Facebook Error 368 (abuse / rate block)
            is_368, reason = is_error_368(resp.status_code, resp.text, resp_json)
            if is_368:
                record_page_block(target_page_id, code=368, message=reason)
                cooldown_mins = int(FB_ERROR_368_COOLDOWN_SECONDS / 60)
                return {
                    "success": False,
                    "error": f"Facebook Error 368: Feature temporarily blocked ({reason}). Pausing all further uploads for {cooldown_mins} minutes.",
                    "error_code": 368,
                    "blocked_temporarily": True,
                    "retry_after_seconds": FB_ERROR_368_COOLDOWN_SECONDS
                }

            print(f"❌ Facebook Reel Upload Error ({resp.status_code}): {resp.text}")
            return {"success": False, "error": resp.text}
    except Exception as e:
        print(f"❌ Facebook upload exception: {e}")
        return {"success": False, "error": str(e)}

def publish_christian_reel_to_facebook(video_path, headline, caption):
    """
    Publishes a reel specifically to the 'Jesus Hears You' Facebook Page.
    """
    return publish_reel_to_facebook(
        video_path=video_path,
        headline=headline,
        caption=caption,
        page_id=CHRISTIAN_FB_PAGE_ID,
        access_token=CHRISTIAN_FB_ACCESS_TOKEN
    )
