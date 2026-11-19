import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "generated")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Web Dashboard Port
PORT = int(os.getenv("PORT", "5001"))
SECRET_KEY = os.getenv("SECRET_KEY", "tamil-ai-reel-maker-secret-key-2026")

# Free AI Voice Settings (Microsoft Edge Neural Voice)
VOICE_NAME = os.getenv("VOICE_NAME", "ta-IN-ValluvarNeural")
VOICE_RATE = os.getenv("VOICE_RATE", "+0%")
VOICE_PITCH = os.getenv("VOICE_PITCH", "+0Hz")

# Free AI Scriptwriting (Google Gemini API - Optional / Fallback Mock Mode Active)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Facebook Page Credentials
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN", "")

# Background News Soundtrack
BG_AUDIO_PATH = os.path.join(ASSETS_DIR, "audio", "news_bg.mp3")

# Video Settings (9:16 Vertical Facebook Reels)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# Automation & Deduplication Settings
SEEN_ARTICLES_FILE = os.path.join(BASE_DIR, "seen_articles.json")
AUTO_POST_INTERVAL_MINUTES = int(os.getenv("AUTO_POST_INTERVAL_MINUTES", "15"))
AUTO_POSTING_ENABLED = os.getenv("AUTO_POSTING_ENABLED", "true").lower() in ("true", "1", "yes")

# Tamil News RSS Feeds (High-Availability Real-Time Feeds)
NEWS_FEEDS = [
    {
        "name": "Google News (இலங்கை)",
        "url": "https://news.google.com/rss/search?q=%E0%AE%87%E0%AE%B2%E0%AE%99%E0%AF%8D%E0%AE%95%E0%AF%88+-site:newsfirst.lk+when:1d&hl=ta&gl=LK&ceid=LK:ta",
        "category": "breaking"
    },
    {
        "name": "Thinakaran (தினகரன்)",
        "url": "https://www.thinakaran.lk/feed/",
        "category": "local"
    },
    {
        "name": "Virakesari (வீரகேசரி)",
        "url": "https://news.google.com/rss/search?q=site:virakesari.lk+when:2d&hl=ta&gl=LK&ceid=LK:ta",
        "category": "local"
    },
    {
        "name": "Ada Derana Tamil (அட தெரண)",
        "url": "https://news.google.com/rss/search?q=site:adaderanatamil.lk+when:2d&hl=ta&gl=LK&ceid=LK:ta",
        "category": "breaking"
    },
    {
        "name": "BBC News Tamil (பிபிசி)",
        "url": "https://feeds.bbci.co.uk/tamil/rss.xml",
        "category": "world"
    }
]
