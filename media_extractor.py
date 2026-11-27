import os
import re
import io
import json
import html
import time
import requests
from urllib.parse import urljoin, urlparse, parse_qs
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
from config import OUTPUT_DIR, VIDEO_WIDTH, VIDEO_HEIGHT

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,video/*",
    "Accept-Language": "ta,en-US,en;q=0.9",
}

_session = requests.Session()
_session.headers.update(HEADERS)

def clean_extracted_url(raw_url, base_url):
    """Cleans, unescapes, and normalizes an extracted image or video URL."""
    if not raw_url or not isinstance(raw_url, str):
        return None
    url = html.unescape(raw_url.strip().strip("'\""))
    if not url or url.startswith("data:") or "javascript:" in url:
        return None

    # Handle Next.js image proxy wrappers (e.g. /_next/image?url=https%3A%2F%2Fmedia.adaderana...)
    if "_next/image" in url and "url=" in url:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if "url" in params and params["url"]:
            real_url = params["url"][0]
            if real_url.startswith("http"):
                url = real_url

    if url.startswith("//"):
        url = "https:" + url
    elif not url.startswith("http://") and not url.startswith("https://"):
        url = urljoin(base_url, url)
    return url

def extract_ld_json_images(html_text, base_url):
    """Extracts genuine news photos from Schema.org JSON-LD scripts (standard for WebP news images)."""
    urls = []
    scripts = re.findall(r'<script[^>]+type=[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script>', html_text, re.DOTALL | re.IGNORECASE)
    for s in scripts:
        try:
            data = json.loads(s.strip())
            items = data if isinstance(data, list) else [data]
            for item in items:
                img_val = item.get("image") or item.get("thumbnailUrl") or item.get("primaryImageOfPage")
                if isinstance(img_val, str):
                    c = clean_extracted_url(img_val, base_url)
                    if c: urls.append(c)
                elif isinstance(img_val, list):
                    for sub in img_val:
                        if isinstance(sub, str):
                            c = clean_extracted_url(sub, base_url)
                            if c: urls.append(c)
                        elif isinstance(sub, dict) and sub.get("url"):
                            c = clean_extracted_url(sub["url"], base_url)
                            if c: urls.append(c)
        except Exception:
            continue
    return urls

def extract_media_urls(article_url):
    """
    Scans the article HTML for authentic images (WebP, JPG, PNG) and MP4 video clips.
    Extracts MULTIPLE high-resolution photos so the Reel video can display multiple dynamic slides.
    Returns: dict with 'image_url', 'image_urls' (list), and 'video_url'
    """
    result = {"image_url": None, "image_urls": [], "video_url": None}
    if not article_url:
        return result

    target_url = article_url
    if "tamil.adaderana.lk/news/" in target_url:
        target_url = target_url.replace("tamil.adaderana.lk", "adaderanatamil.lk")

    m_id = re.search(r'/(?:news|article)/(\d+)', target_url)
    story_id = m_id.group(1) if m_id else None

    try:
        response = _session.get(target_url, allow_redirects=True, timeout=12)
        if response.status_code != 200:
            return result

        html_text = response.text
        raw_photos = []

        # 1. Extract Video URLs
        og_vid = re.search(r'<meta[^>]+property=[\"\'](?:og:video|og:video:url|og:video:secure_url)[\"\'][^>]+content=[\"\']([^\"\']+)[\"\']', html_text, re.IGNORECASE)
        if not og_vid:
            og_vid = re.search(r'<meta[^>]+content=[\"\']([^\"\']+)[\"\'][^>]+property=[\"\'](?:og:video|og:video:url|og:video:secure_url)[\"\']', html_text, re.IGNORECASE)
        if og_vid:
            v_url = clean_extracted_url(og_vid.group(1), target_url)
            if v_url and not ("youtube.com/embed" in v_url or "player.vimeo" in v_url):
                result["video_url"] = v_url

        if not result["video_url"]:
            tw_vid = re.search(r'<meta[^>]+name=[\"\']twitter:player:stream[\"\'][^>]+content=[\"\']([^\"\']+)[\"\']', html_text, re.IGNORECASE)
            if tw_vid:
                v_url = clean_extracted_url(tw_vid.group(1), target_url)
                if v_url:
                    result["video_url"] = v_url

        if not result["video_url"]:
            html5_vid = re.search(r'<(?:video|source)[^>]+src=[\"\']([^\"\']+\.mp4(?:\?[^\"\']*)?)[\"\']', html_text, re.IGNORECASE)
            if html5_vid:
                v_url = clean_extracted_url(html5_vid.group(1), target_url)
                if v_url:
                    result["video_url"] = v_url

        # 2. Extract Multiple Authentic Photos
        # 2a. OpenGraph Image (Authoritative primary photo)
        og_img = re.search(r'<meta[^>]+property=[\"\'](?:og:image|og:image:url|og:image:secure_url)[\"\'][^>]+content=[\"\']([^\"\']+)[\"\']', html_text, re.IGNORECASE)
        if not og_img:
            og_img = re.search(r'<meta[^>]+content=[\"\']([^\"\']+)[\"\'][^>]+property=[\"\'](?:og:image|og:image:url|og:image:secure_url)[\"\']', html_text, re.IGNORECASE)
        if og_img:
            i_url = clean_extracted_url(og_img.group(1), target_url)
            if i_url: raw_photos.append(i_url)

        # 2b. Twitter Card Image
        tw_img = re.search(r'<meta[^>]+name=[\"\']twitter:image[\"\'][^>]+content=[\"\']([^\"\']+)[\"\']', html_text, re.IGNORECASE)
        if not tw_img:
            tw_img = re.search(r'<meta[^>]+content=[\"\']([^\"\']+)[\"\'][^>]+name=[\"\']twitter:image[\"\']', html_text, re.IGNORECASE)
        if tw_img:
            i_url = clean_extracted_url(tw_img.group(1), target_url)
            if i_url: raw_photos.append(i_url)

        # 2c. Schema.org JSON-LD Gallery Images
        ld_images = extract_ld_json_images(html_text, target_url)
        raw_photos.extend(ld_images)

        # 2d. Article Body Images - parsed strictly inside article container, excluding sidebars/footers
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")
        for bad in soup.find_all(class_=re.compile(r"sidebar|related|popular|more-news|recommend|widget|banner|footer|trending", re.I)):
            bad.decompose()
        for bad in soup(["aside", "nav", "footer"]):
            bad.decompose()

        container = soup.find(class_=re.compile(r"article-html|prose|story-body|article-body|news-content|post-content", re.I)) or soup.find("article")
        search_root = container if container else soup
        for img_tag in search_root.find_all("img", src=True):
            src_val = clean_extracted_url(img_tag["src"], target_url)
            if src_val:
                raw_photos.append(src_val)

        for source_tag in search_root.find_all("source"):
            srcset = source_tag.get("srcset") or source_tag.get("data-srcset")
            if srcset:
                parts = [p.strip().split()[0] for p in srcset.split(",") if p.strip()]
                if parts:
                    best_src = clean_extracted_url(parts[-1], target_url)
                    if best_src: raw_photos.append(best_src)

        # Filter, clean, and deduplicate photos strictly belonging to THIS story
        seen_urls = set()
        cleaned_photos = []
        skip_keywords = ["placeholder", "default_news", "blank.gif", "logo", "avatar", "icon", "advert", "banner", "button", "pixel", "wp-includes", "emoji"]

        for photo in raw_photos:
            if not photo or photo in seen_urls:
                continue
            lower_p = photo.lower()
            if any(skip in lower_p for skip in skip_keywords):
                continue
            if not any(ext in lower_p for ext in [".webp", ".jpg", ".jpeg", ".png", "/image/"]):
                continue

            # CRITICAL: Exclude photos belonging to different articles on the same media CDN
            m_photo = re.search(r'/(?:news-articles|post/featured_image|articles?)/(\d+)', photo)
            if m_photo and story_id and m_photo.group(1) != story_id:
                continue

            seen_urls.add(photo)
            cleaned_photos.append(photo)
            if len(cleaned_photos) >= 6:
                break

        result["image_urls"] = cleaned_photos[:4]
        if cleaned_photos:
            result["image_url"] = cleaned_photos[0]

    except Exception as e:
        print(f"Notice: Media extraction error for {target_url}: {e}")

    return result

def _blur_zone(img, x1, y1, x2, y2, radius=28):
    """Blurs a rectangular zone on a PIL image in-place using Gaussian blur."""
    w, h = img.size
    x1 = max(0, x1); y1 = max(0, y1)
    x2 = min(w, x2); y2 = min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return
    region = img.crop((x1, y1, x2, y2))
    blurred = region.filter(ImageFilter.GaussianBlur(radius=radius))
    img.paste(blurred, (x1, y1))


def clean_image_watermarks_and_text(image_path, output_path=None):
    """
    Aggressively hides all news-site logos, watermarks, tickers and banners:
    - Blurs bottom strip (URL tickers, copyright lines, chyrons)
    - Blurs top strip (top banners / channel headers)
    - Blurs all 4 corners with heavy Gaussian (where channel logos always sit)
    - Blurs bottom-left & bottom-right corners (extra safety)
    - Removes full-width thin bar overlays at top and bottom edges
    """
    if output_path is None:
        output_path = image_path

    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            w, h = img.size

            # --- Zone definitions (as fractions of image size) ---
            corner_w  = int(w * 0.22)   # logo corner width  (~22% of width)
            corner_h  = int(h * 0.18)   # logo corner height (~18% of height)
            strip_h   = int(h * 0.12)   # top/bottom strip height (~12%)
            blur_r    = max(18, int(min(w, h) * 0.04))  # blur radius scales with image

            # 1. Bottom strip (URL tickers, copyright, website name)
            _blur_zone(img, 0, h - strip_h, w, h, radius=blur_r)

            # 2. Top strip (channel header, top banners)
            _blur_zone(img, 0, 0, w, strip_h, radius=blur_r)

            # 3. Top-Left corner (most common logo position)
            _blur_zone(img, 0, 0, corner_w, corner_h, radius=blur_r)

            # 4. Top-Right corner (second-most common logo position)
            _blur_zone(img, w - corner_w, 0, w, corner_h, radius=blur_r)

            # 5. Bottom-Left corner (source credit, photo attribution)
            _blur_zone(img, 0, h - corner_h, corner_w, h, radius=blur_r)

            # 6. Bottom-Right corner (timestamp, watermark)
            _blur_zone(img, w - corner_w, h - corner_h, w, h, radius=blur_r)

            img.save(output_path, "JPEG", quality=95)
            return output_path
    except Exception as e:
        print(f"Notice: Watermark cleanup notice: {e}")
        return image_path

def download_authentic_image(image_url, filename_prefix="news_photo"):
    """Downloads genuine news photo (WebP, JPG, PNG) and converts to high-quality RGB JPEG without watermarks."""
    if not image_url:
        return None
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"{filename_prefix}_{int(time.time())}.jpg")
    try:
        resp = _session.get(image_url, timeout=14)
        if resp.status_code == 200 and len(resp.content) > 3000:
            with Image.open(io.BytesIO(resp.content)) as im:
                im = im.convert("RGB")
                if im.width >= 300 and im.height >= 180:
                    im.save(out_path, "JPEG", quality=95)
                    # Automatically remove any burned-in ticker text and channel watermarks
                    clean_image_watermarks_and_text(out_path)
                    return out_path
    except Exception as e:
        print(f"Notice: Image download error ({image_url}): {e}")
    return None

def download_authentic_video(video_url, filename_prefix="news_video"):
    """Downloads genuine news video clip (capped at 50MB) and saves as .mp4."""
    if not video_url:
        return None
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"{filename_prefix}_{int(time.time())}.mp4")
    try:
        resp = _session.get(video_url, stream=True, timeout=30)
        if resp.status_code == 200:
            bytes_written = 0
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        bytes_written += len(chunk)
                        if bytes_written > 50 * 1024 * 1024:
                            print(f"⚠️ Video exceeds 50MB. Skipping.")
                            if os.path.exists(out_path):
                                os.remove(out_path)
                            return None
            if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
                return out_path
    except Exception as e:
        print(f"Notice: Video download error ({video_url}): {e}")
    return None

def create_ambient_vertical_canvas(source_image_path, output_path):
    """
    Transforms any standard news photo into a full 1080x1920 (9:16 vertical)
    broadcast canvas with dual-layer framing:
    - Ambient blurred + dimmed background
    - Crisp focused center visual with subtle edge glow
    Note: Watermark cleaning is already done in download_authentic_image().
    """
    with Image.open(source_image_path) as raw:
        raw = raw.convert("RGB")

        # 1. Background: Resize to fill 1080x1920, heavy blur, dimmed by 35%
        bg = raw.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=28))
        enhancer = ImageEnhance.Brightness(bg)
        bg = enhancer.enhance(0.50)

        # 2. Foreground: Center visual scaled to 1080 width
        fg_w = VIDEO_WIDTH
        scale_ratio = fg_w / raw.width
        fg_h = int(raw.height * scale_ratio)
        fg = raw.resize((fg_w, fg_h), Image.Resampling.LANCZOS)

        # Center vertically around Y = 460
        fg_y = 460
        bg.paste(fg, (0, fg_y))

        # Thin clean edge dividers
        draw = ImageDraw.Draw(bg)
        draw.line([(0, fg_y), (VIDEO_WIDTH, fg_y)], fill=(255, 255, 255, 45), width=1)
        draw.line([(0, fg_y + fg_h), (VIDEO_WIDTH, fg_y + fg_h)], fill=(255, 255, 255, 45), width=1)

        bg.save(output_path, "JPEG", quality=95)
        return output_path
