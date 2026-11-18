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
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin123")

# Free AI Voice Settings (Microsoft Edge Neural Voice)
# Options:
#   ta-LK-SaranyaNeural (Female, Sri Lanka Tamil - DEFAULT)
#   ta-LK-KumarNeural   (Male, Sri Lanka Tamil)
#   ta-IN-PallaviNeural (Female, Indian Tamil)
VOICE_NAME = os.getenv("VOICE_NAME", "ta-LK-SaranyaNeural")
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
REEL_MAX_DURATION = 35 # Seconds
MAX_SHORT_VIDEO_DURATION = int(os.getenv("MAX_SHORT_VIDEO_DURATION", "300"))

# Automation & Deduplication Settings
SEEN_ARTICLES_FILE = os.path.join(BASE_DIR, "seen_articles.json")
AUTO_POST_INTERVAL_MINUTES = int(os.getenv("AUTO_POST_INTERVAL_MINUTES", "3"))
AUTO_POSTING_ENABLED = os.getenv("AUTO_POSTING_ENABLED", "true").lower() in ("true", "1", "yes")

# Tamil News RSS Feeds
NEWS_FEEDS = [
    {
        "name": "Virakesari (வீரகேசரி)",
        "url": "https://www.virakesari.lk/feed",
        "category": "local"
    },
    {
        "name": "Ada Derana Tamil (அட தெரண)",
        "url": "http://tamil.adaderana.lk/rss.php",
        "category": "breaking"
    },
    {
        "name": "BBC News Tamil (பிபிசி)",
        "url": "https://feeds.bbci.co.uk/tamil/rss.xml",
        "category": "world"
    },
    {
        "name": "News 1st Tamil (நியூஸ்பர்ஸ்ட்)",
        "url": "https://www.newsfirst.lk/tamil/feed/",
        "category": "local"
    }
]
