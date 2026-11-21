import os
import re
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "generated")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def clean_fb_token(raw):
    """Safely extracts pure Facebook OAuth token, stripping quotes, whitespace, and prefixes."""
    if not raw:
        return ""
    s = str(raw).strip().strip("'\"").strip()
    match = re.search(r'(EAA[a-zA-Z0-9_\-\.]+)', s)
    return match.group(1).strip() if match else s.strip()

def clean_fb_pid(raw):
    """Safely extracts pure numeric Facebook Page ID."""
    if not raw:
        return ""
    s = str(raw).strip().strip("'\"").strip()
    match = re.search(r'(\d+)', s)
    return match.group(1).strip() if match else s.strip()

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

# Facebook Page Credentials (Main News Page)
FB_PAGE_ID = clean_fb_pid(os.getenv("FB_PAGE_ID", ""))
FB_ACCESS_TOKEN = clean_fb_token(os.getenv("FB_ACCESS_TOKEN", ""))
FB_BLOCK_STATE_FILE = os.path.join(BASE_DIR, "fb_block_state.json")
FB_ERROR_368_COOLDOWN_SECONDS = int(os.getenv("FB_ERROR_368_COOLDOWN_SECONDS", "7200"))  # Default 2 hours cooldown (Error 368)

# Christian Space Settings ("Jesus Hears You" - English Global Devotional)
CHRISTIAN_PAGE_NAME = "Jesus Hears You"
DEFAULT_CHRISTIAN_FB_PAGE_ID = "1383467624858784"
DEFAULT_CHRISTIAN_FB_ACCESS_TOKEN = "EAAZA4EJF6aPoBTKBbZCoQGZCkUrsqef4dZBg1L5BfWzFbZBoEEB3vYynmZCKHJfCpcyxoyr8ZCSD30c1yjtiBhJ1sWCChpVgqzgmAP0wbgLSi9ZAJiuDKSCO2jOUJnfUucObYoyrEPPg1cVjpTDZC7CJJWGgicvyGK1n1QTMHgvPB8BVzlZCG6NZAn8ARATiTcuRMpHkZBp5DKwe6I29V72Cza0P3x3O"

_c_pid = clean_fb_pid(os.getenv("CHRISTIAN_FB_PAGE_ID", ""))
_c_token = clean_fb_token(os.getenv("CHRISTIAN_FB_ACCESS_TOKEN", ""))

# Resolve Christian Page ID: env -> default
CHRISTIAN_FB_PAGE_ID = _c_pid if _c_pid else DEFAULT_CHRISTIAN_FB_PAGE_ID

# Resolve Christian Token: env (if valid EAA token) -> default permanent token -> fallback main FB token
if _c_token and _c_token.startswith("EAA"):
    CHRISTIAN_FB_ACCESS_TOKEN = _c_token
elif DEFAULT_CHRISTIAN_FB_ACCESS_TOKEN:
    CHRISTIAN_FB_ACCESS_TOKEN = DEFAULT_CHRISTIAN_FB_ACCESS_TOKEN
else:
    CHRISTIAN_FB_ACCESS_TOKEN = FB_ACCESS_TOKEN

CHRISTIAN_BG_AUDIO_PATH = os.path.join(ASSETS_DIR, "audio", "christian_bg.mp3")
CHRISTIAN_HISTORY_FILE = os.path.join(BASE_DIR, "christian_history.json")
CHRISTIAN_STATE_FILE = os.path.join(BASE_DIR, "christian_state.json")
CHRISTIAN_SEEN_VERSES_FILE = os.path.join(BASE_DIR, "christian_seen_verses.json")
# English Devotional Neural Voice (en-US-ChristopherNeural - warm, inspirational, compassionate male voice)
CHRISTIAN_VOICE_NAME = os.getenv("CHRISTIAN_VOICE_NAME", "en-US-ChristopherNeural")
CHRISTIAN_VOICE_RATE = os.getenv("CHRISTIAN_VOICE_RATE", "+0%")
CHRISTIAN_VOICE_PITCH = os.getenv("CHRISTIAN_VOICE_PITCH", "+0Hz")
CHRISTIAN_SENTENCE_GAP_MS = int(os.getenv("CHRISTIAN_SENTENCE_GAP_MS", "550"))

# Background News Soundtrack
BG_AUDIO_PATH = os.path.join(ASSETS_DIR, "audio", "news_bg.mp3")
BG_AUDIO_VOLUME = float(os.getenv("BG_AUDIO_VOLUME", "0.035"))  # Soft ambient background music (~3.5% volume)

# YouTube Shorts Configuration
ENABLE_YOUTUBE_CHRISTIAN_PUBLISH = os.getenv("ENABLE_YOUTUBE_CHRISTIAN_PUBLISH", "false").lower() in ("true", "1", "yes")
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
YOUTUBE_REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN", "").strip()
YOUTUBE_PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "public").strip()

# Pixabay Free Stock Art & Video API
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "").strip()
CHRISTIAN_USE_VIDEO_BG = os.getenv("CHRISTIAN_USE_VIDEO_BG", "true").lower() in ("true", "1", "yes")

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
