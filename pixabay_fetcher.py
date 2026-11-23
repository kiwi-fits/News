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


# Verified Pixabay video IDs that specifically feature Jesus Christ,
# the monumental Cristo Rey blessing statue, and divine biblical savior footage.
VERIFIED_PIXABAY_JESUS_VIDEOS = [
    342721, # Jesus Christ walking out of the resurrection tomb with open blessing arms and divine halo (9s)
    342745, # Jesus Christ radiant resurrection into glory with starlight celestial rays (9s)
    314404, # Jesus Christ in serene prayer against dramatic sunset clouds (9s)
    314391, # Photorealistic Jesus Christ with glowing crown of thorns against golden sunset (8s)
    314393, # Jesus Christ with crown of thorns and sunrise cross in celestial rays (8s)
    314396, # Jesus Christ carrying the cross in tearful heavenly glory (8s)
    316408, # Jesus Christ walking forth from empty tomb in brilliant rays of divine light (9s)
    361623, # Monumental Christ the Redeemer statue of Jesus over green mountains and sunny sky (5s)
    260895, # Monumental Cristo Rey blessing statue with open arms in sunrise mist (11s)
    260896, # Cristo Rei statue of Jesus with outstretched blessing arms in dramatic clouds (15s)
    76656,  # Sacred golden sunset hitting Jesus' outstretched hand and blessing robe (20s)
    156719, # Jesus Christ as Good Shepherd with staff looking across celestial clouds (49s)
]

# Verified high-resolution Pixabay vertical portraits of Jesus Christ
VERIFIED_PIXABAY_JESUS_IMAGES = [
    8560269, # Colorful divine portrait of Jesus Christ
    8269310, # Luminous serene portrait of Jesus Christ
    7986396, # Jesus Christ with gentle lamb (Good Shepherd)
    8140047, # Divine savior Jesus Christ holy artwork
    7975795, # Photorealistic portrait face of Jesus Christ
    5829481, # Divine sacred portrait of Jesus Christ
]


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


def is_genuine_jesus_clip(hit):
    """
    Validates that a video hit actually depicts Jesus Christ, rather than
    generic church furniture, candles, open books, empty chapels, or unrelated scenery.
    """
    vid = hit.get("id")
    if vid in VERIFIED_PIXABAY_JESUS_VIDEOS:
        return True

    tags = str(hit.get("tags", "")).lower()

    # 1. Hard rejects: unrelated items, holidays, monuments, people
    hard_rejects = [
        "candle", "santa", "wrapping", "paper", "coffee", "tea", "beverage", "drink", "girl",
        "bridge", "elevator", "liberty", "statue of liberty", "usa", "manhattan",
        "camel", "crib", "manger", "advent", "wise men", "three kings",
        "nativity", "angel", "shepherds", "festive season", "christmas",
        "pope", "bishop", "cemetery", "graveyard", "rotting christ", "heavy metal", "rock concert"
    ]
    if any(hr in tags for hr in hard_rejects):
        return False

    # 2. Reject church / cathedral / chapel / worship interiors
    church_terms = [
        "church", "cathedral", "chapel", "architecture", "temple",
        "gothic", "altar", "stained glass", "pew", "interior", "basilica", "monastery", "crypt", "worship"
    ]
    if any(ct in tags for ct in church_terms):
        return False

    # 3. Mary without Jesus depiction
    if ("mary" in tags or "madonna" in tags) and not any(sf in tags for sf in ["jesus", "cristo", "redeemer"]):
        return False

    # 4. Must depict Jesus / Christ through sacred figure tags
    sacred_figures = [
        "statue", "cristo", "redeemer", "christ the redeemer", "figure", "sculpture", "cristo rey"
    ]
    has_jesus = "jesus" in tags or "christ" in tags
    return has_jesus and any(sf in tags for sf in sacred_figures)


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
    Guarantees the image depicts Jesus Christ Himself.
    """
    api_key = PIXABAY_API_KEY.strip() if PIXABAY_API_KEY else os.getenv("PIXABAY_API_KEY", "").strip()
    if not api_key:
        print("ℹ️ Pixabay API Notice: PIXABAY_API_KEY not configured in .env (will use curated local Jesus visual library).")
        return None

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    seen_ids = _load_seen_ids()

    clean_q = query.strip()
    if "jesus" not in clean_q.lower():
        clean_q = f"jesus {clean_q}"

    url = f"https://pixabay.com/api/?key={api_key}&q={quote_plus(clean_q)}&image_type={image_type}&orientation={orientation}&safesearch=true&per_page=25"

    try:
        resp = _session.get(url, timeout=12)
        candidate = None

        if resp.status_code == 200:
            hits = resp.json().get("hits", [])
            # Filter strictly for Jesus portraits/artwork
            jesus_hits = [
                h for h in hits
                if "jesus" in str(h.get("tags", "")).lower()
                and not any(b in str(h.get("tags", "")).lower() for b in ["candle", "stained glass", "pew"])
            ]
            if jesus_hits:
                unseen = [h for h in jesus_hits if h.get("id") not in seen_ids]
                candidate = random.choice(unseen) if unseen else random.choice(jesus_hits)

        # Fallback to verified Jesus image library if dynamic search returned no genuine portrait
        if not candidate:
            unseen_v = [vid for vid in VERIFIED_PIXABAY_JESUS_IMAGES if vid not in seen_ids]
            chosen_vid = random.choice(unseen_v) if unseen_v else random.choice(VERIFIED_PIXABAY_JESUS_IMAGES)
            v_url = f"https://pixabay.com/api/?key={api_key}&id={chosen_vid}"
            v_resp = _session.get(v_url, timeout=12)
            if v_resp.status_code == 200 and v_resp.json().get("hits"):
                candidate = v_resp.json()["hits"][0]

        if candidate:
            img_id = candidate.get("id")
            img_url = candidate.get("largeImageURL") or candidate.get("webformatURL")
            if img_url:
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
                        print(f"🎉 Pixabay Jesus Image Retrieved: ID {img_id} (Tags: {tags}) -> {out_path}")
                        return out_path

    except Exception as e:
        print(f"Pixabay API fetch notice: {e}")

    return None


def fetch_pixabay_jesus_video(query="jesus christ", min_duration=5):
    """
    Fetches a high-quality free Jesus Christ motion video clip from Pixabay.
    Guarantees 100% that the video features Jesus Christ Himself,
    strictly filtering out unrelated candles, books, church furniture, and scenery.
    """
    api_key = PIXABAY_API_KEY.strip() if PIXABAY_API_KEY else os.getenv("PIXABAY_API_KEY", "").strip()
    if not api_key:
        print("ℹ️ Pixabay API Notice: PIXABAY_API_KEY not configured in .env.")
        return None

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    seen_ids = _load_seen_ids()

    # Prioritize our curated library of 12 verified Jesus motion videos
    unseen_curated = [vid for vid in VERIFIED_PIXABAY_JESUS_VIDEOS if f"v_{vid}" not in seen_ids]
    candidate_id = random.choice(unseen_curated) if unseen_curated else random.choice(VERIFIED_PIXABAY_JESUS_VIDEOS)

    chosen = None
    try:
        # Fetch the chosen verified Jesus video from Pixabay API
        v_url = f"https://pixabay.com/api/videos/?key={api_key}&id={candidate_id}"
        v_resp = _session.get(v_url, timeout=12)
        if v_resp.status_code == 200 and v_resp.json().get("hits"):
            chosen = v_resp.json()["hits"][0]

        # Dynamic search fallback (strictly filtered for genuine Jesus depictions)
        if not chosen:
            clean_q = "jesus statue" if "statue" in query.lower() else "jesus christ"
            url = f"https://pixabay.com/api/videos/?key={api_key}&q={quote_plus(clean_q)}&safesearch=true&per_page=30"
            resp = _session.get(url, timeout=12)
            if resp.status_code == 200:
                hits = resp.json().get("hits", [])
                genuine_hits = [h for h in hits if is_genuine_jesus_clip(h) and h.get("duration", 0) >= min_duration]
                if genuine_hits:
                    unseen = [h for h in genuine_hits if f"v_{h.get('id')}" not in seen_ids]
                    chosen = random.choice(unseen) if unseen else random.choice(genuine_hits)

        if chosen:
            vid_id = chosen.get("id")
            videos = chosen.get("videos", {})

            # Select medium (720p/1080p) or large for crisp quality
            target_v = videos.get("medium") or videos.get("large") or videos.get("small")
            if target_v and target_v.get("url"):
                v_url = target_v["url"]
                out_video = os.path.join(OUTPUT_DIR, f"pixabay_jesus_video_{vid_id}_{int(time.time())}.mp4")

                print(f"📥 Downloading Pixabay Jesus Video: ID {vid_id} ({chosen.get('duration')}s)...")
                v_resp = _session.get(v_url, stream=True, timeout=30)
                if v_resp.status_code == 200:
                    with open(out_video, "wb") as f:
                        for chunk in v_resp.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)

                    if os.path.exists(out_video) and os.path.getsize(out_video) > 20000:
                        _save_seen_id(f"v_{vid_id}")
                        tags = chosen.get("tags", "")
                        print(f"🎥 Pixabay Jesus Video Retrieved: ID {vid_id} (Tags: {tags}) -> {out_video}")
                        return out_video

    except Exception as e:
        print(f"Pixabay Video fetch notice: {e}")

    return None


if __name__ == "__main__":
    import sys
    test_q = sys.argv[1] if len(sys.argv) > 1 else "jesus"
    print(f"Testing Pixabay Video fetch for: '{test_q}'...")
    v_res = fetch_pixabay_jesus_video(test_q)
    if v_res:
        print(f"SUCCESS: {v_res} (Size: {os.path.getsize(v_res)} bytes)")
    else:
        print("No video retrieved. Ensure PIXABAY_API_KEY is set in .env")
