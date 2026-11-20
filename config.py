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
VOICE_NAME = os.getenv("VOICE_NAME", "ta-SG-AnbuNeural")
VOICE_RATE = os.getenv("VOICE_RATE", "+5%")  # Natural news anchor pace
VOICE_PITCH = os.getenv("VOICE_PITCH", "+0Hz")
SENTENCE_GAP_MS = int(os.getenv("SENTENCE_GAP_MS", "650"))  # Natural breath pause between news sentences in ms

# Free AI Scriptwriting (Google Gemini API - Optional / Fallback Mock Mode Active)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Facebook Page Credentials
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN", "")
FB_BLOCK_STATE_FILE = os.path.join(BASE_DIR, "fb_block_state.json")
FB_ERROR_368_COOLDOWN_SECONDS = int(os.getenv("FB_ERROR_368_COOLDOWN_SECONDS", "7200"))  # Default 2 hours cooldown (Error 368)

# Christian Space Settings ("Jesus Hears You")
CHRISTIAN_PAGE_NAME = "Jesus Hears You"
_c_pid = os.getenv("CHRISTIAN_FB_PAGE_ID", "").strip()
_c_token = os.getenv("CHRISTIAN_FB_ACCESS_TOKEN", "").strip()
# Guard against boolean YAML strings ("true"/"false") and cleanly fallback to main FB credentials if unset
CHRISTIAN_FB_PAGE_ID = _c_pid if _c_pid and _c_pid.lower() not in ("true", "false") else os.getenv("FB_PAGE_ID", "").strip()
CHRISTIAN_FB_ACCESS_TOKEN = _c_token if _c_token and _c_token.lower() not in ("true", "false") else os.getenv("FB_ACCESS_TOKEN", "").strip()
CHRISTIAN_BG_AUDIO_PATH = os.path.join(ASSETS_DIR, "audio", "christian_bg.mp3")
CHRISTIAN_HISTORY_FILE = os.path.join(BASE_DIR, "christian_history.json")
CHRISTIAN_STATE_FILE = os.path.join(BASE_DIR, "christian_state.json")

# Background News Soundtrack
BG_AUDIO_PATH = os.path.join(ASSETS_DIR, "audio", "news_bg.mp3")
BG_AUDIO_VOLUME = float(os.getenv("BG_AUDIO_VOLUME", "0.035"))  # Soft ambient background music (~3.5% volume)

# Video Settings (9:16 Vertical Facebook Reels)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# Automation & Deduplication Settings
SEEN_ARTICLES_FILE = os.path.join(BASE_DIR, "seen_articles.json")
REJECTED_ARTICLES_FILE = os.path.join(BASE_DIR, "rejected_articles.json")
REJECTED_TTL_SECONDS = int(os.getenv("REJECTED_TTL_SECONDS", "7200"))  # Auto-prune rejected stories every 2 hours
AUTO_POST_INTERVAL_SECONDS = int(os.getenv("AUTO_POST_INTERVAL_SECONDS", "600"))
AUTO_POST_INTERVAL_MINUTES = int(os.getenv("AUTO_POST_INTERVAL_MINUTES", "10"))
AUTO_POSTING_ENABLED = os.getenv("AUTO_POSTING_ENABLED", "true").lower() in ("true", "1", "yes")

# Tamil News RSS Feeds (High-Availability Real-Time Feeds)
NEWS_FEEDS = [
    {
        "name": "Ada Derana Tamil (அட தெரண)",
        "url": "https://news.google.com/rss/search?q=site:adaderanatamil.lk&hl=ta&gl=LK&ceid=LK:ta",
        "category": "breaking"
    },
    {
        "name": "Virakesari (வீரகேசரி)",
        "url": "https://news.google.com/rss/search?q=site:virakesari.lk&hl=ta&gl=LK&ceid=LK:ta",
        "category": "local"
    },
    {
        "name": "Thinakaran (தினகரன்)",
        "url": "https://www.thinakaran.lk/feed/",
        "category": "local"
    },
    {
        "name": "IBC Tamil (ஐபிசி தமிழ்)",
        "url": "https://news.google.com/rss/search?q=site:ibctamil.com&hl=ta&gl=LK&ceid=LK:ta",
        "category": "breaking"
    },
    {
        "name": "Tamil Mirror (தமிழ் மிரர்)",
        "url": "https://news.google.com/rss/search?q=site:tamilmirror.lk&hl=ta&gl=LK&ceid=LK:ta",
        "category": "local"
    },
    {
        "name": "Google News (இலங்கை முக்கிய செய்திகள்)",
        "url": "https://news.google.com/rss/search?q=%E0%AE%87%E0%AE%B2%E0%AE%99%E0%AF%8D%E0%AE%95%E0%AF%88&hl=ta&gl=LK&ceid=LK:ta",
        "category": "breaking"
    },
    {
        "name": "BBC News Tamil (பிபிசி)",
        "url": "https://feeds.bbci.co.uk/tamil/rss.xml",
        "category": "world"
    }
]
