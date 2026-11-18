import os
import requests
from config import FB_PAGE_ID, FB_ACCESS_TOKEN

def publish_reel_to_facebook(video_path, headline, caption, article_link=None, engagement_question=None):
    """
    Publishes the 9:16 vertical video reel directly to the Facebook Page feed.
    Also auto-posts the first comment with the original link.
    """
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        print("⚠️ Facebook credentials not set. Running in simulation mode.")
        return {"success": True, "simulated": True, "video_id": "sim_reel_12345"}

    if not video_path or not os.path.exists(video_path):
        return {"success": False, "error": "Video file not found."}

    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/videos"
    print(f"🚀 Uploading 9:16 Reel to Facebook Page ({video_path})...")

    try:
        with open(video_path, "rb") as vf:
            files = {"source": (os.path.basename(video_path), vf, "video/mp4")}
            data = {
                "description": caption,
                "title": headline,
                "access_token": FB_ACCESS_TOKEN
            }
            resp = requests.post(url, files=files, data=data, timeout=180)

        if resp.status_code == 200:
            vid_id = resp.json().get("id")
            print(f"🎉 Successfully posted 9:16 Reel to Facebook! Video ID: {vid_id}")

            # Post First Comment
            if article_link or engagement_question:
                comment_text = (
                    f"💬 {engagement_question or 'உங்கள் கருத்தை கீழே கமெண்ட் செய்யுங்கள்!'}\n\n"
                    f"🔗 முழு செய்தி அறிக்கை: {article_link or 'https://facebook.com'}\n\n"
                    f"🔔 உடனுக்குடன் உண்மைச் செய்திகளை அறிய எமது பக்கத்தை Follow & Like செய்யுங்கள்! 👍"
                )
                try:
                    c_url = f"https://graph.facebook.com/v19.0/{vid_id}/comments"
                    requests.post(c_url, data={"message": comment_text, "access_token": FB_ACCESS_TOKEN}, timeout=15)
                    print(f"💬 Auto-posted first comment for video {vid_id}")
                except Exception as ce:
                    print(f"Notice: First comment error: {ce}")

            return {"success": True, "video_id": vid_id}
        else:
            print(f"❌ Facebook Reel Upload Error ({resp.status_code}): {resp.text}")
            return {"success": False, "error": resp.text}
    except Exception as e:
        print(f"❌ Facebook upload exception: {e}")
        return {"success": False, "error": str(e)}
