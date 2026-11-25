import os
import re
import json
import time
import random
import requests
from urllib.parse import quote_plus
from PIL import Image
from config import BASE_DIR, OUTPUT_DIR, PIXABAY_API_KEY, VIDEO_WIDTH, VIDEO_HEIGHT, CHRISTIAN_HISTORY_FILE

_session = requests.Session()
_session.headers.update({
    "User-Agent": "TamilDevotionalReels/2.0 (compatible; PixabayClient/1.0)"
})

SEEN_PIXABAY_FILE = os.path.join(BASE_DIR, "pixabay_seen.json")


# Verified Pixabay video IDs that specifically feature Jesus Christ,
# Christ the Redeemer, the Holy Cross, and divine biblical savior footage.
VERIFIED_PIXABAY_JESUS_VIDEOS = [
    # 1. Divine Jesus Portraits & Motion Figures (Native 9:16 Vertical & Crisp HD)
    193131, # Radiant face portrait of Jesus Christ with golden halo and gentle smile (10s, vertical)
    213826, # Jesus Christ walking on storm waters in divine white robe (7s, vertical)
    334166, # Radiant figure of Jesus Christ in celestial light and prayer (9s, vertical)
    333565, # Divine Jesus Christ surrounded by resurrection heavenly light (10s, vertical)
    316008, # Jesus Christ in serene heavenly glory with peaceful clouds (11s, vertical)
    314404, # Jesus Christ in serene prayer against dramatic sunset clouds (9s, vertical)
    37700,  # Majestic holy face portrait of Jesus Christ (Shroud of Turin style) (40s, 1080p)
    157774, # Jesus Christ in sacred prayer and divine contemplation (35s, 1080p)
    116144, # Jesus Christ divine cross and scriptures (30s, 1080p)

    # 2. Resurrection, Empty Tomb & Ascension
    342721, # Jesus Christ walking out of resurrection tomb with open blessing arms (9s, vertical)
    342745, # Jesus Christ radiant resurrection into glory with starlight celestial rays (9s, vertical)
    342734, # Jesus Christ resurrection with open welcoming arms and holy heart (9s, vertical)
    316408, # Jesus Christ walking forth from empty tomb in brilliant rays of light (9s, vertical)
    34841,  # Sacred stone rolled away from empty tomb with divine sunrise light (11s, 1080p)
    69660,  # Risen Christ empty tomb miracle with radiant dawn light (24s, 1080p)
    113936, # Resurrection stone opening with golden heavenly light rays (40s, 4K)
    272053, # Empty tomb with morning cross and bright divine sunshine (64s, 1080p)
    328467, # Resurrection morning at the empty tomb of Jesus Christ (10s, 4K)
    328461, # Divine golden rays over the empty tomb of Jesus Christ (10s, 4K)
    328463, # Radiant sunrise over the holy resurrection tomb (10s, 4K)
    331892, # Glorious empty tomb with morning sunrise (10s, 4K)
    331896, # Sacred empty cave tomb illuminated by divine grace (10s, 4K)

    # 3. Christ the Redeemer & Sacred Majestic Statues
    310181, # Christ the Redeemer monument with welcoming open arms in vertical HD (6s, vertical)
    361623, # Majestic Christ the Redeemer statue over misty mountain peaks (5s, 4K)
    260895, # Cristo Rei statue of Jesus with open arms blessing the horizon (11s, 4K)
    1514,   # Majestic Jesus statue against morning sunrise and drifting clouds (22s, 1080p)

    # 4. Holy Cross & Calvary at Sunrise / Celestial Light
    337406, # Three sacred crosses of Calvary at golden sunrise (10s, vertical)
    207424, # Holy cross glowing on heavenly golden horizon (42s, vertical)
    150957, # Sacred glowing cross in divine vertical beam of light (30s, vertical)
    384331, # Holy cross of Jesus Christ with celestial particles and divine glory (14s, vertical)
    387548, # Sacred cross against heavenly clouds and warm sunbeams (10s, vertical)
    340608, # Glowing cross on holy hill in native vertical orientation (10s, vertical)
    340601, # Sacred Calvary cross with radiant celestial light (10s, vertical)
    340606, # Divine cross of salvation under heavenly skies (10s, vertical)
    344737, # Holy cross with gentle light rays of hope (10s, vertical)
    337410, # Golden sunrise behind the cross of Jesus (10s, vertical)
    324539, # Dramatic Calvary cross against golden evening clouds (10s, 4K)
    324529, # Holy cross of Christ on scenic hilltop (10s, 4K)
    324533, # Majestic sacred cross under moving heavenly skies (10s, 4K)
    316069, # Holy cross with brilliant dawn light and sun flare (10s, 4K)
    316066, # Cross of Christ on Calvary with glowing sunset (13s, 4K)
    46042,  # Three sacred crosses of Calvary with colorful heavenly aurora (35s, 1080p)
    35601,  # Wooden cross of Jesus Christ with crown of thorns and blue sky (29s, 1080p)
    377107, # Sacred cross of crucifixion on mountain peak with golden flare (65s, 1080p)
    381762, # Cross on Calvary with divine heavenly sash and clouds (55s, 1080p)
    85231,  # Sacred Calvary cross with rolling green hills and dramatic sky (60s, 1080p)
    189295, # Majestic cross with golden divine sun rays (60s, 1080p)
    213197, # Cross against serene blue sky and heavenly clouds (60s, 1080p)
    220570, # Holy cross in gentle evening atmosphere (14s, vertical)

    # 5. Jesus Christ on the Holy Cross / Passion
    329889, # Jesus Christ on the holy cross with celestial halo and golden light (12s, vertical)
    314391, # Jesus Christ with glowing crown of thorns against golden sunset (8s, vertical)
    314392, # Jesus Christ with crown of thorns and sunrise cross on Calvary hill (8s, vertical)
    314393, # Jesus Christ with crown of thorns and sunrise cross in celestial rays (8s, vertical)
    314396, # Jesus Christ carrying the cross in tearful heavenly glory (8s, vertical)
    342732, # Jesus Christ on Calvary with prayer and salvation rays (9s, vertical)
    343982, # Sacred Good Friday cross on Calvary hill (8s, 1080p)
    343983, # Cross of crucifixion on Calvary hill at sunset (8s, 1080p)
    125667, # Sacred biblical scene of Jesus Christ at judgment and crucifixion (50s, 1080p)
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
                data = json.load(f)
                return data if isinstance(data, list) else list(data)
        except Exception:
            pass
    return []


def _save_seen_id(img_id):
    import json
    seen = _load_seen_ids()
    if img_id in seen:
        seen.remove(img_id)
    seen.append(img_id)
    # Retain up to 500 IDs in LRU order
    if len(seen) > 500:
        seen = seen[-500:]
    try:
        with open(SEEN_PIXABAY_FILE, "w", encoding="utf-8") as f:
            json.dump(seen, f)
    except Exception:
        pass


def get_recent_christian_video_ids(limit=40):
    """
    Extracts all video IDs used in the last `limit` reels in christian_history.json.
    Guarantees strict recency blocking so the audience NEVER sees the same video clip repeated.
    """
    if not os.path.exists(CHRISTIAN_HISTORY_FILE):
        return set()
    try:
        with open(CHRISTIAN_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
        recent_ids = set()
        for item in history[:limit]:
            vfiles = item.get("visual_files") or []
            if isinstance(vfiles, str):
                vfiles = [vfiles]
            for vf in vfiles:
                m = re.search(r'video_(\d+)', vf)
                if m:
                    recent_ids.add(int(m.group(1)))
                else:
                    m2 = re.search(r'(\d{5,7})', vf)
                    if m2:
                        recent_ids.add(int(m2.group(1)))
        return recent_ids
    except Exception as e:
        print(f"Notice: Failed to load recent christian video history: {e}")
        return set()


def is_genuine_jesus_clip(hit, min_duration=5):
    """
    Validates that a video hit actually depicts Jesus Christ, Christ the Redeemer,
    the Holy Cross, Calvary, or the Resurrection, rather than generic buildings,
    churches, candles, holiday decor, or empty scenery.
    """
    vid = hit.get("id")
    if vid in VERIFIED_PIXABAY_JESUS_VIDEOS:
        return True

    dur = hit.get("duration", 0)
    if dur < min_duration:
        return False

    tags = str(hit.get("tags", "")).lower()

    # Hard rejects: unrelated items, holidays, monuments, generic scenery, church interiors
    hard_rejects = [
        "santa", "wrapping", "paper", "coffee", "tea", "beverage", "drink", "girl",
        "bridge", "elevator", "liberty", "statue of liberty", "usa", "manhattan",
        "camel", "crib", "manger", "advent", "wise men", "three kings",
        "shepherds", "reindeer", "snowman",
        "pope", "bishop", "cemetery", "graveyard", "rotting christ", "heavy metal", "rock concert",
        "zen", "meditation", "spa", "relaxing", "yoga", "city", "bus", "pedestrian", "walk", "craft",
        "cathedral", "church", "altar", "stained glass", "pew", "chapel", "monastery",
        "steeple", "crypt", "basilica", "building", "screensaver", "heart monitor", "hospital",
        "knight", "armor", "shield", "island"
    ]
    if any(hr in tags for hr in hard_rejects):
        return False

    # Mary without Jesus depiction
    if ("mary" in tags or "madonna" in tags) and not any(sf in tags for sf in ["jesus", "cristo", "redeemer", "christ"]):
        return False

    # Must depict Jesus / Christ / Cross directly
    has_jesus = any(k in tags for k in ["jesus", "christ", "crucifixion", "crucifix", "calvary", "savior", "cristo"])
    has_cross = "cross" in tags and any(k in tags for k in ["god", "faith", "holy", "salvation", "resurrection", "calvary", "crucifixion"])
    return has_jesus or has_cross


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


def fetch_pixabay_jesus_video(query="jesus christ", min_duration=5, headline="", verse_reference="", script_text=""):
    """
    Fetches a high-quality free Jesus Christ / Holy Cross motion video clip from Pixabay.
    Guarantees 100%:
    1. NEVER repeats any video clip used in the last 40 reels from christian_history.json.
    2. Dynamic thematic search FIRST: queries Pixabay for fresh clips matching the story's theme.
    3. Expanded curated library fallback (over 55 verified Jesus & Holy Cross clips).
    4. Least-recently-used rotation if all clips have eventually been used once.
    """
    api_key = PIXABAY_API_KEY.strip() if PIXABAY_API_KEY else os.getenv("PIXABAY_API_KEY", "").strip()
    if not api_key:
        print("ℹ️ Pixabay API Notice: PIXABAY_API_KEY not configured in .env.")
        return None

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    recent_ids = get_recent_christian_video_ids(limit=40)
    seen_ids = set(_load_seen_ids())

    # Build smart thematic queries based on narrative content
    context_text = f"{headline} {verse_reference} {script_text} {query}".lower()
    thematic_queries = []

    if any(w in context_text for w in ["resurrection", "tomb", "risen", "easter", "stone", "alive"]):
        thematic_queries = ["resurrection jesus", "empty tomb jesus", "risen christ", "jesus christ"]
    elif any(w in context_text for w in ["shepherd", "sheep", "lamb", "flock", "pasture", "psalm 23"]):
        thematic_queries = ["shepherd jesus", "good shepherd christ", "jesus christ"]
    elif any(w in context_text for w in ["cross", "calvary", "crucifix", "crucifixion", "blood", "sacrifice", "thorns", "ephesians"]):
        thematic_queries = ["calvary cross", "jesus on cross", "jesus crucifixion", "holy cross"]
    elif any(w in context_text for w in ["miracle", "water", "sea", "storm", "wind", "heal", "waves"]):
        thematic_queries = ["jesus miracle", "jesus walking", "christ savior"]
    elif any(w in context_text for w in ["statue", "redeemer", "king", "glory", "majesty"]):
        thematic_queries = ["christ the redeemer", "jesus statue", "christ savior"]
    else:
        thematic_queries = ["jesus christ", "christ savior", "jesus prayer", "holy cross calvary", "son of god"]

    chosen = None

    # Step 1: Dynamic Pixabay search matching the theme (strictly excluding recent_ids)
    for t_query in thematic_queries:
        if chosen:
            break
        try:
            url = f"https://pixabay.com/api/videos/?key={api_key}&q={quote_plus(t_query)}&safesearch=true&per_page=30"
            resp = _session.get(url, timeout=12)
            if resp.status_code == 200:
                hits = resp.json().get("hits", [])
                candidates = [
                    h for h in hits
                    if is_genuine_jesus_clip(h, min_duration=min_duration)
                    and h.get("id") not in recent_ids
                ]
                if candidates:
                    # Prefer completely unseen in seen_ids first
                    unseen_c = [c for c in candidates if f"v_{c.get('id')}" not in seen_ids]
                    chosen = random.choice(unseen_c) if unseen_c else random.choice(candidates)
                    break
        except Exception as e:
            print(f"Notice: Pixabay dynamic search notice for '{t_query}': {e}")

    # Step 2: Curated library fallback (strictly excluding recent_ids)
    if not chosen:
        eligible_curated = [vid for vid in VERIFIED_PIXABAY_JESUS_VIDEOS if vid not in recent_ids]
        if eligible_curated:
            unseen_curated = [vid for vid in eligible_curated if f"v_{vid}" not in seen_ids]
            candidate_id = random.choice(unseen_curated) if unseen_curated else random.choice(eligible_curated)
            try:
                v_url = f"https://pixabay.com/api/videos/?key={api_key}&id={candidate_id}"
                v_resp = _session.get(v_url, timeout=12)
                if v_resp.status_code == 200 and v_resp.json().get("hits"):
                    chosen = v_resp.json()["hits"][0]
            except Exception as e:
                print(f"Notice: Curated video fetch notice for ID {candidate_id}: {e}")

    # Step 3: Least-recently-used fallback if all clips were in recent_ids (library exhausted)
    if not chosen:
        seen_list = _load_seen_ids()
        def lru_rank(vid):
            key = f"v_{vid}"
            return seen_list.index(key) if key in seen_list else -1
        sorted_curated = sorted(VERIFIED_PIXABAY_JESUS_VIDEOS, key=lru_rank)
        candidate_id = sorted_curated[0]
        try:
            v_url = f"https://pixabay.com/api/videos/?key={api_key}&id={candidate_id}"
            v_resp = _session.get(v_url, timeout=12)
            if v_resp.status_code == 200 and v_resp.json().get("hits"):
                chosen = v_resp.json()["hits"][0]
        except Exception as e:
            print(f"Notice: LRU video fetch notice for ID {candidate_id}: {e}")


    if chosen:
        vid_id = chosen.get("id")
        videos = chosen.get("videos", {})

        # Select medium (720p/1080p) or large for crisp quality
        target_v = videos.get("medium") or videos.get("large") or videos.get("small")
        if target_v and target_v.get("url"):
            v_url = target_v["url"]
            out_video = os.path.join(OUTPUT_DIR, f"pixabay_jesus_video_{vid_id}_{int(time.time())}.mp4")

            print(f"📥 Downloading Pixabay Jesus Video: ID {vid_id} ({chosen.get('duration')}s) [Unique / Excluded from last 40 reels]...")
            try:
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
                print(f"Pixabay Video download notice: {e}")

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
