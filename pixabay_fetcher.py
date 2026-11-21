import os
import time
import random
import requests
from urllib.parse import quote_plus
from PIL import Image
from config import BASE_DIR, OUTPUT_DIR, PIXABAY_API_KEY, VIDEO_WIDTH, VIDEO_HEIGHT

_session = requests.Session()
_session.headers.update({
    "User-Agent": "TamilDevotionalReels/2.0 (compatible; PixabayClient/1.0)"
})

SEEN_PIXABAY_FILE = os.path.join(BASE_DIR, "pixabay_seen.json")


def _load_seen_ids():
    import json
    if os.path.exists(SEEN_PIXABAY_FILE):
        try:
            with open(SEEN_PIXABAY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def _save_seen_id(img_id):
    import json
    seen = _load_seen_ids()
    seen.add(img_id)
    # Keep only the last 300 IDs
    if len(seen) > 300:
        seen = set(list(seen)[-300:])
    try:
        with open(SEEN_PIXABAY_FILE, "w", encoding="utf-8") as f:
            json.dump(list(seen), f)
    except Exception:
        pass


def crop_to_exact_9_16(image_path, target_path, width=VIDEO_WIDTH, height=VIDEO_HEIGHT):
    """
    Crops and resizes an image to exact 1080x1920 vertical canvas
    using center crop and high-quality Lanczos resampling.
    """
    with Image.open(image_path) as im:
        im = im.convert("RGB")
        w, h = im.size
        ratio = max(width / w, height / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        im_resized = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - width) // 2
        top = (new_h - height) // 2
        im_cropped = im_resized.crop((left, top, left + width, top + height))
        im_cropped.save(target_path, "JPEG", quality=95)
    return target_path


def fetch_pixabay_jesus_image(query="jesus christ", image_type="all", orientation="vertical", min_width=640, min_height=960):
    """
    Fetches a high-quality vertical Jesus artwork from Pixabay's free API.
    
    Args:
        query: Search query (e.g. 'jesus christ', 'jesus good shepherd', 'jesus praying')
        image_type: 'illustration', 'photo', or 'all'
        orientation: 'vertical' (9:16 portrait)
        min_width: Minimum pixel width
        min_height: Minimum pixel height
        
    Returns:
        Absolute path to the downloaded, 1080x1920 cropped JPEG, or None if unavailable.
    """
    api_key = PIXABAY_API_KEY.strip() if PIXABAY_API_KEY else os.getenv("PIXABAY_API_KEY", "").strip()
    if not api_key:
        print("ℹ️ Pixabay API Notice: PIXABAY_API_KEY not configured in .env (will use curated local Jesus visual library).")
        return None

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    seen_ids = _load_seen_ids()

    # Build search query variations
    clean_q = query.strip()
    if "jesus" not in clean_q.lower() and "christ" not in clean_q.lower():
        clean_q = f"jesus {clean_q}"

    params = {
        "key": api_key,
        "q": clean_q,
        "image_type": image_type,
        "orientation": orientation,
        "safesearch": "true",
        "per_page": 20
    }

    url = f"https://pixabay.com/api/?key={api_key}&q={quote_plus(clean_q)}&image_type={image_type}&orientation={orientation}&safesearch=true&per_page=20"

    try:
        resp = _session.get(url, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            hits = data.get("hits", [])
            
            # If no results with specific query, fallback to broad 'jesus christ'
            if not hits and clean_q.lower() != "jesus christ":
                fallback_url = f"https://pixabay.com/api/?key={api_key}&q={quote_plus('jesus christ')}&image_type={image_type}&orientation={orientation}&safesearch=true&per_page=20"
                resp_fb = _session.get(fallback_url, timeout=12)
                if resp_fb.status_code == 200:
                    hits = resp_fb.json().get("hits", [])

            if not hits:
                print(f"Notice: Pixabay returned 0 results for '{clean_q}'.")
                return None

            # Filter for unseen candidates first
            unseen_hits = [h for h in hits if h.get("id") not in seen_ids]
            candidate = random.choice(unseen_hits) if unseen_hits else random.choice(hits)

            img_id = candidate.get("id")
            # Best resolution URL
            img_url = candidate.get("largeImageURL") or candidate.get("webformatURL")
            if not img_url:
                return None

            temp_raw = os.path.join(OUTPUT_DIR, f"temp_pixabay_{img_id}_{int(time.time())}.jpg")
            out_path = os.path.join(OUTPUT_DIR, f"pixabay_jesus_{img_id}_{int(time.time())}.jpg")

            img_resp = _session.get(img_url, timeout=15)
            if img_resp.status_code == 200 and len(img_resp.content) > 5000:
                with open(temp_raw, "wb") as f:
                    f.write(img_resp.content)

                crop_to_exact_9_16(temp_raw, out_path)
                
                if os.path.exists(temp_raw):
                    try:
                        os.remove(temp_raw)
                    except Exception:
                        pass

                if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
                    _save_seen_id(img_id)
                    tags = candidate.get("tags", "")
                    print(f"🎉 Pixabay Image Retrieved: ID {img_id} (Tags: {tags}) -> {out_path}")
                    return out_path

        elif resp.status_code == 400:
            print(f"Pixabay API Error: Invalid API key or request parameters (HTTP 400).")
        else:
            print(f"Pixabay API response: HTTP {resp.status_code}")

    except Exception as e:
        print(f"Pixabay API fetch notice: {e}")

    return None


if __name__ == "__main__":
    import sys
    test_q = sys.argv[1] if len(sys.argv) > 1 else "jesus shepherd"
    print(f"Testing Pixabay fetch for: '{test_q}'...")
    res = fetch_pixabay_jesus_image(test_q)
    if res:
        print(f"SUCCESS: {res} (Size: {os.path.getsize(res)} bytes)")
    else:
        print("No image retrieved. Ensure PIXABAY_API_KEY is set in .env")
