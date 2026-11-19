import os
import re
import io
import json
import html
import time
import requests
from urllib.parse import urljoin, quote as urlquote
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
from config import OUTPUT_DIR, VIDEO_WIDTH, VIDEO_HEIGHT

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,video/*",
    "Accept-Language": "ta,en-US,en;q=0.9",
}

def clean_extracted_url(raw_url, base_url):
    """Cleans, unescapes, and normalizes an extracted image or video URL."""
    if not raw_url or not isinstance(raw_url, str):
        return None
    url = html.unescape(raw_url.strip().strip("'\""))
    if not url or url.startswith("data:") or "javascript:" in url:
        return None

    # Handle Next.js image proxy wrappers (e.g. /_next/image?url=https%3A%2F%2Fmedia.adaderana...)
    if "_next/image" in url and "url=" in url:
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
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
    try:
        response = requests.get(target_url, headers=HEADERS, allow_redirects=True, timeout=12)
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
        # 2a. OpenGraph Image
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

        # 2d. Article Content Images (<article>, <figure>, <img> inside story body)
        for img_match in re.finditer(r'<img[^>]+(?:src|data-src|data-orig-file)=[\"\']([^\"\']+)[\"\']', html_text, re.IGNORECASE):
            src_val = clean_extracted_url(img_match.group(1), target_url)
            if src_val:
                raw_photos.append(src_val)

        # 2e. HTML5 <source> tags
        sources = re.findall(r'<source[^>]+(?:srcset|data-srcset)=[\"\']([^\"\']+)[\"\']', html_text, re.IGNORECASE)
        for s in sources:
            parts = [p.strip().split()[0] for p in s.split(",") if p.strip()]
            if parts:
                best_src = clean_extracted_url(parts[-1], target_url)
                if best_src: raw_photos.append(best_src)

        # Filter, clean, and deduplicate photos
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

def clean_image_watermarks_and_text(image_path, output_path=None):
    """
    Cleans burned-in news tickers, website banners, and corner channel watermarks.
    - Crops lower-third banner (where news portals burn ticker text and URLs).
    - Inpaints/blends corner watermark zones (top-left and top-right).
    - Preserves crisp high-resolution photo content with zero branding.
    """
    if output_path is None:
        output_path = image_path

    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            w, h = img.size

            # 1. Lower banner / ticker removal (crop bottom 13% where tickers & website URLs sit)
            crop_bottom = int(h * 0.87)
            cropped = img.crop((0, 0, w, crop_bottom))
            cw, ch = cropped.size

            # 2. Corner watermark removal:
            logo_w = int(cw * 0.16)
            logo_h = int(ch * 0.13)

            # Inpaint Top-Right watermark using neighbor patch
            if cw > 2 * logo_w and ch > logo_h:
                patch_tr = cropped.crop((cw - 2 * logo_w, 0, cw - logo_w, logo_h))
                patch_tr = patch_tr.filter(ImageFilter.GaussianBlur(radius=2))
                cropped.paste(patch_tr, (cw - logo_w, 0))

            # Inpaint Top-Left watermark using neighbor patch
            if cw > 2 * logo_w and ch > logo_h:
                patch_tl = cropped.crop((logo_w, 0, 2 * logo_w, logo_h))
                patch_tl = patch_tl.filter(ImageFilter.GaussianBlur(radius=2))
                cropped.paste(patch_tl, (0, 0))

            cropped.save(output_path, "JPEG", quality=95)
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
        resp = requests.get(image_url, headers=HEADERS, timeout=14)
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
        resp = requests.get(video_url, headers=HEADERS, stream=True, timeout=30)
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

def create_white_logo_canvas(output_path=None):
    """
    Creates a clean white vertical 9:16 background canvas (1080x1920)
    with the official channel logo (assets/logo.png) centered in the visual area.
    Used whenever no authentic news photo or video clip is available.
    """
    from config import ASSETS_DIR
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, f"white_logo_{int(time.time())}.jpg")

    canvas = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (255, 255, 255))
    logo_path = os.path.join(ASSETS_DIR, "logo.png")

    if os.path.exists(logo_path):
        try:
            with Image.open(logo_path) as logo:
                logo = logo.convert("RGBA")
                logo_size = 540
                logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                # Position in center of visual zone (midpoint between Y=360 and Y=1000 is Y=680)
                pos_x = (VIDEO_WIDTH - logo_size) // 2
                pos_y = 680 - (logo_size // 2)
                canvas.paste(logo, (pos_x, pos_y), logo)
        except Exception as e:
            print(f"Notice: Failed to paste logo on white canvas: {e}")

    canvas.save(output_path, "JPEG", quality=95)
    return output_path

def fetch_visual_for_story(article_image_url=None, keyword="Sri Lanka News"):
    """
    Fallback visual generator:
    1. Downloads provided article_image_url if authentic photo exists
    2. If no photo or video is available, uses the official logo centered on a clean white background.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_filename = f"visual_{int(time.time())}.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_filename)
    temp_raw = os.path.join(OUTPUT_DIR, f"temp_{int(time.time())}.jpg")

    # 1. Try Article Image
    if article_image_url:
        try:
            resp = requests.get(article_image_url, headers=HEADERS, timeout=12)
            if resp.status_code == 200 and len(resp.content) > 5000:
                with open(temp_raw, "wb") as f:
                    f.write(resp.content)
                create_ambient_vertical_canvas(temp_raw, out_path)
                if os.path.exists(temp_raw):
                    os.remove(temp_raw)
                return out_path
        except Exception as e:
            print(f"Notice: Article image download: {e}")

    # 2. No photos or videos available: use logo centered on white background
    print("🎨 No photo or video available: using official logo centered on white background.")
    return create_white_logo_canvas(out_path)
