import os
import json
import time
import signal
import threading
import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from config import PORT, SECRET_KEY, OUTPUT_DIR, VOICE_NAME, FB_PAGE_ID, FB_ACCESS_TOKEN, GEMINI_API_KEY, NEWS_FEEDS, AUTO_POSTING_ENABLED
from news_fetcher import fetch_latest_news
from pipeline import create_ai_news_reel_for_article, load_history
from fb_publisher import publish_reel_to_facebook
from scheduler import scheduler

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = SECRET_KEY

@app.route("/")
def index():
    history = load_history()
    return render_template("index.html", history=history, current_voice=VOICE_NAME, fb_connected=bool(FB_PAGE_ID), gemini_connected=bool(GEMINI_API_KEY))

@app.route("/api/system-status", methods=["GET"])
def api_system_status():
    history = load_history()
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    today_reels = [h for h in history if (h.get("timestamp") or "").startswith(today_str)]
    reels_today_count = len(today_reels)
    fb_published_today = sum(1 for h in today_reels if h.get("status") == "published")
    
    gemini_daily_limit = 1500
    gemini_used = reels_today_count
    gemini_remaining = max(0, gemini_daily_limit - gemini_used)

    status_data = {
        "success": True,
        "gemini": {
            "connected": bool(GEMINI_API_KEY),
            "model": "gemini-flash-latest",
            "tier": "Google AI Studio Free Tier",
            "status": "Online (Active)" if GEMINI_API_KEY else "Missing API Key",
            "daily_limit": gemini_daily_limit,
            "used_today": gemini_used,
            "remaining": gemini_remaining,
            "rpm_limit": 15,
            "tpm_limit": "1,000,000",
            "usage_percent": round((gemini_used / gemini_daily_limit) * 100, 2),
            "cost": "$0.00 (Free Quota)"
        },
        "facebook": {
            "connected": bool(FB_PAGE_ID and FB_ACCESS_TOKEN),
            "page_name": "செய்தி மையம்",
            "page_id": FB_PAGE_ID if FB_PAGE_ID else "Not Configured",
            "status": "Connected (Live)" if (FB_PAGE_ID and FB_ACCESS_TOKEN) else "Simulation Mode",
            "rate_limit": "200 calls / hour",
            "published_today": fb_published_today,
            "credits": "Unlimited Page Posting",
            "auto_comment": True
        },
        "voice": {
            "provider": "Microsoft Edge Neural TTS",
            "voice_name": VOICE_NAME,
            "display_name": "Saranya (சரண்யா) - இலங்கை தமிழ்",
            "status": "Active (High Fidelity)",
            "rate": "+0%",
            "pitch": "+0Hz",
            "credits": "Unlimited (100% Free Cloud Neural)",
            "usage_cost": "$0.00"
        },
        "engine": {
            "resolution": "1080×1920 (9:16 Vertical HD)",
            "active_feeds_count": len(NEWS_FEEDS),
            "sources": [f["name"] for f in NEWS_FEEDS],
            "audio_ducking": "FFmpeg sidechain ducking",
            "status": "Operational",
            "credits": "Unlimited (Local GPU/CPU Rendering)"
        },
        "stats": {
            "total_reels_generated": len(history),
            "reels_today": reels_today_count,
            "fb_published_today": fb_published_today
        },
        "scheduler": scheduler.get_status()
    }
    return jsonify(status_data)

@app.route("/api/scheduler/status", methods=["GET"])
def api_scheduler_status():
    return jsonify({"success": True, "scheduler": scheduler.get_status()})

@app.route("/api/scheduler/toggle", methods=["POST"])
def api_scheduler_toggle():
    status = scheduler.get_status()
    if status["running"]:
        scheduler.stop()
    else:
        scheduler.start()
    return jsonify({"success": True, "scheduler": scheduler.get_status()})

@app.route("/api/scheduler/trigger", methods=["POST"])
def api_scheduler_trigger():
    scheduler.run_cycle_now()
    return jsonify({"success": True, "message": "Manual automation cycle triggered."})

@app.route("/api/scheduler/interval", methods=["POST"])
def api_scheduler_interval():
    data = request.get_json(silent=True) or {}
    minutes = int(data.get("interval_minutes", 30))
    scheduler.set_interval(minutes)
    return jsonify({"success": True, "scheduler": scheduler.get_status()})

@app.route("/api/server/stop", methods=["POST"])
def api_server_stop():
    """
    Safely shuts down the local Flask server and background automation.
    """
    def shutdown():
        time.sleep(0.5)
        try:
            scheduler.stop()
        except Exception:
            pass
        print("🛑 Received Stop Server request from Web UI. Terminating process...")
        os.kill(os.getpid(), signal.SIGTERM)

    threading.Thread(target=shutdown, daemon=True).start()
    return jsonify({"success": True, "message": "Server process stopping..."})

@app.route("/api/news", methods=["GET"])
def api_news():
    """
    Fetches the last 10 news stories from RSS feeds.
    If any news story inside that 10 has already been posted, it is partitioned
    into 'posted_news' containing its headline and full voice script body.
    Unposted stories remain in 'live_news'.
    """
    try:
        raw_articles = fetch_latest_news(limit_per_feed=4)
        last_10 = raw_articles[:10]

        history = load_history()
        history_links = {h.get("article_link"): h for h in history if h.get("article_link")}
        history_headlines = {h.get("headline", "").strip(): h for h in history if h.get("headline")}

        live_news = []
        posted_news = []

        for art in last_10:
            link = art.get("link", "")
            title = art.get("title", "").strip()

            matched_h = history_links.get(link)
            if not matched_h:
                for h_title, h_item in history_headlines.items():
                    if h_title and (h_title in title or title in h_title):
                        matched_h = h_item
                        break

            if matched_h:
                art["is_posted"] = True
                art["headline"] = matched_h.get("headline")
                art["voice_script"] = matched_h.get("voice_script")
                art["timestamp"] = matched_h.get("timestamp")
                art["status"] = matched_h.get("status")
                art["caption"] = matched_h.get("caption", "")
                art["id"] = matched_h.get("id")
                posted_news.append(art)
            else:
                art["is_posted"] = False
                live_news.append(art)

        # All recent posted history items (ensuring headline and full script body are included)
        all_posted = []
        for h in history[:25]:
            all_posted.append({
                "id": h.get("id"),
                "headline": h.get("headline"),
                "voice_script": h.get("voice_script"),
                "caption": h.get("caption", ""),
                "timestamp": h.get("timestamp"),
                "status": h.get("status", "Published"),
                "source": h.get("source", "செய்தி மையம்"),
                "article_link": h.get("article_link")
            })

        return jsonify({
            "success": True,
            "articles": last_10,
            "last_10": last_10,
            "live_news": live_news,
            "posted_news": posted_news,
            "all_posted": all_posted
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/create-reel", methods=["POST"])
def api_create_reel():
    data = request.get_json(silent=True) or {}
    article = {
        "title": (data.get("title") or "").strip(),
        "summary": (data.get("summary") or "").strip(),
        "category": (data.get("category") or "breaking").strip(),
        "link": (data.get("link") or "").strip(),
        "source": (data.get("source") or "செய்தி மையம் AI").strip(),
        "image_url": (data.get("image_url") or "").strip() or None
    }

    if not article["title"]:
        # Auto-pick freshest news article
        articles = fetch_latest_news(limit_per_feed=1)
        if not articles:
            return jsonify({"success": False, "error": "No breaking news stories found."}), 400
        article = articles[0]

    try:
        result = create_ai_news_reel_for_article(article)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/publish-reel", methods=["POST"])
def api_publish_reel():
    data = request.get_json(silent=True) or {}
    video_file = data.get("video_file")
    headline = data.get("headline", "முக்கிய செய்தி")
    caption = data.get("caption", "")
    article_link = data.get("article_link")
    question = data.get("question")

    if not video_file:
        return jsonify({"success": False, "error": "Missing video file parameter."}), 400

    video_path = os.path.join(OUTPUT_DIR, video_file)
    if not os.path.exists(video_path):
        return jsonify({"success": False, "error": f"Video file not found: {video_file}"}), 404

    res = publish_reel_to_facebook(
        video_path=video_path,
        headline=headline,
        caption=caption,
        article_link=article_link,
        engagement_question=question
    )

    if res.get("success"):
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
                print(f"🗑️ Deleted published reel from disk: {video_path}")
        except Exception as ce:
            print(f"Notice: Video cleanup error: {ce}")

    return jsonify(res)

@app.route("/api/history", methods=["GET"])
def api_history():
    return jsonify({"success": True, "history": load_history()})

@app.route("/media/<path:filename>")
def serve_media(filename):
    return send_from_directory(OUTPUT_DIR, filename)

if __name__ == "__main__":
    from heartbeat import start_heartbeat_loop
    start_heartbeat_loop()
    if AUTO_POSTING_ENABLED:
        scheduler.start()
    print(f"🚀 Starting AI Tamil News Reels Studio on http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
