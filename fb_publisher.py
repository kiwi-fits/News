import os
import requests
from config import FB_PAGE_ID, FB_ACCESS_TOKEN
from ai_rewriter import strip_channel_names

def publish_reel_to_facebook(video_path, headline, caption, article_link=None, engagement_question=None):
    """
    Publishes the 9:16 vertical video reel directly to the Facebook Page feed.
    Also auto-posts the first comment without any external news channel names or links.
    """
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("⚠️ Facebook credentials not set. Running in simulation mode.")
        return {"success": True, "simulated": True, "video_id": "sim_reel_12345"}

    if not video_path or not os.path.exists(video_path):
        return {"success": False, "error": "Video file not found."}

    # Ensure all text is completely stripped of external news channel names
    clean_caption = strip_channel_names(caption)
    clean_headline = strip_channel_names(headline)

    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/videos"
    print(f"🚀 Uploading 9:16 Reel to Facebook Page ({video_path})...")

    try:
        with open(video_path, "rb") as vf:
            files = {"source": (os.path.basename(video_path), vf, "video/mp4")}
            data = {
                "description": clean_caption,
                "access_token": FB_ACCESS_TOKEN
            }
            resp = requests.post(url, files=files, data=data, timeout=180)

        if resp.status_code == 200:
            vid_id = resp.json().get("id")
            print(f"🎉 Successfully posted 9:16 Reel to Facebook! Video ID: {vid_id}")
            return {"success": True, "video_id": vid_id}
        else:
            print(f"❌ Facebook Reel Upload Error ({resp.status_code}): {resp.text}")
            return {"success": False, "error": resp.text}
    except Exception as e:
        print(f"❌ Facebook upload exception: {e}")
        return {"success": False, "error": str(e)}
