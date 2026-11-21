import os
import math
import time
import shutil
import tempfile
import subprocess
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
from config import OUTPUT_DIR, CHRISTIAN_BG_AUDIO_PATH, VIDEO_WIDTH, VIDEO_HEIGHT, BASE_DIR

SERIF_BOLD_FONTS = [
    # macOS
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
    "/System/Library/Fonts/Supplemental/Baskerville.ttc",
    "/System/Library/Fonts/Supplemental/Palatino.ttc",
    "/Library/Fonts/Georgia Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    # Linux / Ubuntu (GitHub Actions)
    "/usr/share/fonts/truetype/msttcorefonts/georgiab.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Georgia_Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSerif-Bold.otf",
]

SERIF_REGULAR_FONTS = [
    # macOS
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/System/Library/Fonts/Supplemental/Baskerville.ttc",
    "/System/Library/Fonts/Supplemental/Palatino.ttc",
    "/Library/Fonts/Georgia.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    # Linux / Ubuntu (GitHub Actions)
    "/usr/share/fonts/truetype/msttcorefonts/georgia.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Georgia.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSerif-Regular.otf",
]

@lru_cache(maxsize=32)
def get_devotional_font(size, bold=True):
    fonts = SERIF_BOLD_FONTS if bold else SERIF_REGULAR_FONTS
    for fp in fonts:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()

# Backwards compatibility alias
get_tamil_font = get_devotional_font

def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    curr = ""
    for w in words:
        test = f"{curr} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            curr = test
        else:
            if curr:
                lines.append(curr)
            curr = w
    if curr:
        lines.append(curr)
    return lines

_CACHED_SCRIM = None
_CACHED_CTA_IMG = None
_CACHED_CTA_MASK = None

def get_christian_scrim(width=VIDEO_WIDTH, height=VIDEO_HEIGHT):
    """
    Returns a cached copy of the Royal Purple & Flower Garden Vignette Scrim
    avoiding repetitive 1,440-line rendering loops.
    """
    global _CACHED_SCRIM
    if _CACHED_SCRIM is not None and _CACHED_SCRIM.size == (width, height):
        return _CACHED_SCRIM.copy()

    scrim = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(scrim)

    # 1. Top Bar Scrim (Y: 0 to 260) - subtle protection for status bar & top navigation
    for y in range(0, 260):
        ratio = 1.0 - (y / 260.0)
        alpha = int(170 * (ratio ** 1.3))
        draw.line([(0, y), (width, y)], fill=(12, 4, 18, alpha))

    # 2. Lower Flower Garden Purple Scrim (Y: 860 to 1920)
    fade_start = 860
    fade_peak = 1140
    for y in range(fade_start, height):
        if y < fade_peak:
            prog = (y - fade_start) / float(fade_peak - fade_start)
            factor = 0.5 * (1.0 - math.cos(prog * math.pi))
            alpha = int(225 * factor)
            r, g, b = 38, 8, 52
        else:
            prog2 = (y - fade_peak) / float(height - fade_peak)
            alpha = int(225 + 25 * prog2)
            r = int(38 * (1 - prog2) + 24 * prog2)
            g = int(8 * (1 - prog2) + 5 * prog2)
            b = int(52 * (1 - prog2) + 36 * prog2)
        draw.line([(0, y), (width, y)], fill=(r, g, b, alpha))

    # Subtle lateral vignette at side edges in lower third
    for x in range(0, 120):
        ratio = 1.0 - (x / 120.0)
        alpha_edge = int(120 * ratio)
        draw.line([(x, fade_start), (x, height)], fill=(18, 4, 25, alpha_edge))
        draw.line([(width - 1 - x, fade_start), (width - 1 - x, height)], fill=(18, 4, 25, alpha_edge))

    _CACHED_SCRIM = scrim
    return _CACHED_SCRIM.copy()

def get_christian_cta_pill():
    """
    Returns cached 3D Metallic Gold CTA button and rounded mask.
    """
    global _CACHED_CTA_IMG, _CACHED_CTA_MASK
    if _CACHED_CTA_IMG is not None and _CACHED_CTA_MASK is not None:
        return _CACHED_CTA_IMG, _CACHED_CTA_MASK

    font_cta = get_devotional_font(30, bold=True)
    cta_w = 640
    cta_h = 90
    cta_r = cta_h // 2

    cta_mask = Image.new("L", (cta_w, cta_h), 0)
    draw_mask = ImageDraw.Draw(cta_mask)
    draw_mask.rounded_rectangle([0, 0, cta_w, cta_h], radius=cta_r, fill=255)

    cta_img = Image.new("RGBA", (cta_w, cta_h))
    draw_cta = ImageDraw.Draw(cta_img)
    for cy_idx in range(cta_h):
        frac = cy_idx / float(cta_h)
        if frac < 0.20:
            rf = int(255 * (1 - frac) + 248 * frac)
            gf = int(245 * (1 - frac) + 215 * frac)
            bf = int(160 * (1 - frac) + 95 * frac)
        else:
            norm = (frac - 0.20) / 0.80
            rf = int(248 * (1 - norm) + 205 * norm)
            gf = int(215 * (1 - norm) + 145 * norm)
            bf = int(95 * (1 - norm) + 30 * norm)
        draw_cta.line([(0, cy_idx), (cta_w, cy_idx)], fill=(rf, gf, bf, 255))

    draw_cta.line([(cta_r, 2), (cta_w - cta_r, 2)], fill=(255, 255, 220, 190), width=2)
    draw_cta.rounded_rectangle([0, 0, cta_w - 1, cta_h - 1], radius=cta_r, outline=(255, 235, 140, 220), width=1)

    cta_txt = "Follow • Jesus Hears You"
    cta_bb = draw_cta.textbbox((0, 0), cta_txt, font=font_cta)
    cta_tw = cta_bb[2] - cta_bb[0]
    cta_th = cta_bb[3] - cta_bb[1]

    cw_total = 20 + 12 + cta_tw
    start_cx = (cta_w - cw_total) // 2
    mid_cy = cta_h // 2

    cross_x = start_cx + 8
    draw_cta.line([(cross_x, mid_cy - 10), (cross_x, mid_cy + 10)], fill=(38, 18, 5, 255), width=4)
    draw_cta.line([(cross_x - 7, mid_cy - 3), (cross_x + 7, mid_cy - 3)], fill=(38, 18, 5, 255), width=4)
    draw_cta.text((start_cx + 26, (cta_h - cta_th) // 2 - 3), cta_txt, font=font_cta, fill=(38, 18, 5, 255))

    _CACHED_CTA_IMG = cta_img
    _CACHED_CTA_MASK = cta_mask
    return _CACHED_CTA_IMG, _CACHED_CTA_MASK

def create_christian_overlay_card(headline, verse_reference=None, category="promise", width=VIDEO_WIDTH, height=VIDEO_HEIGHT):
    """
    Creates the Royal Purple & 3D Metallic Gold 9:16 vertical overlay card for 'Jesus Hears You'
    strictly tuned for Facebook & Instagram Reels Safe Zones:
    - TOP SAFE ZONE (Y=190..250): Avoids phone status bar, camera notch, and platform header
    - CONTENT SAFE ZONE (Y=960..1560): Fully visible above the native caption & audio player
    - SIDE SAFE MARGINS: 100px left/right margins to guarantee 0% overlap with right-side action icons (Like, Comment, Share)
    - BOTTOM SAFE ZONE (Y=1580..1920): Intentionally left clear of text/buttons for native platform captions
    - Flower Garden Purple Blend: Soft organic plum vignette that preserves the colorful flower garden texture
    """
    overlay = get_christian_scrim(width, height)
    draw = ImageDraw.Draw(overlay)

    font_badge = get_devotional_font(26, bold=True)
    font_brand = get_devotional_font(36, bold=False)
    font_title = get_devotional_font(60, bold=True)
    font_verse = get_devotional_font(40, bold=False)
    font_footer = get_devotional_font(22, bold=False)

    # 3. TOP REELS SAFE ZONE (Y = 190): Category Badge & Brand
    top_y = 190
    cat_badges = {
        "promise": "MORNING PROMISE",
        "wisdom": "BIBLICAL WISDOM",
        "parable": "FAITH PARABLE",
        "mystery": "BIBLE WONDERS",
        "prayer": "BEDTIME PRAYER"
    }
    badge_text = cat_badges.get(category.lower(), "DAILY DEVOTIONAL")
    badge_bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    bw = badge_bbox[2] - badge_bbox[0]
    bh = badge_bbox[3] - badge_bbox[1]

    bx, by = 60, top_y
    cross_w = 18
    gap = 12
    pad_x, pad_y = 22, 11
    total_bw = bw + cross_w + gap + (pad_x * 2)
    total_bh = bh + (pad_y * 2)

    draw.rounded_rectangle(
        [bx, by, bx + total_bw, by + total_bh],
        radius=total_bh // 2,
        fill=(38, 8, 52, 235),
        outline=(235, 195, 85, 255),
        width=2
    )
    cx = bx + pad_x + (cross_w // 2)
    cy = by + (total_bh // 2)
    draw.line([(cx, cy - 9), (cx, cy + 9)], fill=(255, 226, 90, 255), width=3)
    draw.line([(cx - 6, cy - 3), (cx + 6, cy - 3)], fill=(255, 226, 90, 255), width=3)
    draw.text((bx + pad_x + cross_w + gap, by + pad_y - 2), badge_text, font=font_badge, fill=(255, 255, 255, 255))

    # Top-Right Brand (Y = 192)
    brand_name = "Jesus Hears You"
    brand_bbox = draw.textbbox((0, 0), brand_name, font=font_brand)
    brand_w = brand_bbox[2] - brand_bbox[0]
    brand_x = width - 60 - brand_w
    brand_y = top_y + 2
    draw.text((brand_x + 2, brand_y + 2), brand_name, font=font_brand, fill=(0, 0, 0, 180))
    draw.text((brand_x, brand_y), brand_name, font=font_brand, fill=(255, 255, 255, 255))
    arc_y = brand_y + 44
    draw.line([(brand_x + 8, arc_y), (brand_x + brand_w - 8, arc_y)], fill=(235, 195, 85, 220), width=2)

    # 4. SCRIPTURE HEADLINE (SAFE ZONE: Y = 945 to 1140, max width = 880 to clear right action buttons)
    max_title_w = 880
    chosen_fs = 62
    chosen_lh = 74
    for fs, lh in [(62, 74), (54, 64), (48, 58), (44, 52)]:
        font_t_test = get_devotional_font(fs, bold=True)
        t_lines = wrap_text(headline, font_t_test, max_title_w, draw)
        if len(t_lines) <= 2 or fs <= 48:
            chosen_fs, chosen_lh = fs, lh
            break

    font_title = get_devotional_font(chosen_fs, bold=True)
    title_lines = wrap_text(headline, font_title, max_title_w, draw)
    title_h = len(title_lines) * chosen_lh

    clean_ref = (verse_reference or "").strip("— ")
    ref_display = f"— {clean_ref} —" if clean_ref else ""
    verse_h = 38 if ref_display else 0
    gap1 = 12 if ref_display else 0
    gap2 = 20 if ref_display else 0
    div_h = 18 if ref_display else 0

    total_block_h = title_h + gap1 + verse_h + gap2 + div_h
    # Center block vertically in the upper safe-zone container (Y = 945..1240, height = 295)
    top_y = 945 + max(0, (295 - total_block_h) // 2)

    cur_y = top_y
    for line in title_lines:
        bb = draw.textbbox((0, 0), line, font=font_title)
        lw = bb[2] - bb[0]
        lx = (width - lw) // 2

        # Deep drop shadow
        for ox, oy in [(3, 3), (-3, 3), (3, -3), (-3, -3), (0, 4), (0, -4), (4, 0), (-4, 0), (0, 6)]:
            draw.text((lx + ox, cur_y + oy), line, font=font_title, fill=(15, 4, 20, 255))
        # Warm amber bevel glow
        for ox, oy in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)]:
            draw.text((lx + ox, cur_y + oy), line, font=font_title, fill=(210, 160, 40, 255))
        # Radiant gold face
        draw.text((lx, cur_y), line, font=font_title, fill=(255, 230, 95, 255))
        cur_y += chosen_lh

    # 5. CENTERED VERSE REFERENCE (SAFE ZONE: Y ≈ 1135..1175)
    if ref_display:
        vbb = draw.textbbox((0, 0), ref_display, font=font_verse)
        vw = vbb[2] - vbb[0]
        vx = (width - vw) // 2
        vy = cur_y + gap1
        draw.text((vx + 2, vy + 2), ref_display, font=font_verse, fill=(15, 4, 20, 220))
        draw.text((vx, vy), ref_display, font=font_verse, fill=(255, 255, 245, 255))

        # 6. ORNAMENTAL GOLDEN CROSS DIVIDER (SAFE ZONE: Y ≈ 1195..1225)
        div_y = vy + verse_h + gap2
        div_cx = width // 2
        draw.line([(div_cx - 130, div_y), (div_cx - 22, div_y)], fill=(235, 195, 85, 220), width=2)
        draw.line([(div_cx + 22, div_y), (div_cx + 130, div_y)], fill=(235, 195, 85, 220), width=2)
        draw.line([(div_cx, div_y - 9), (div_cx, div_y + 9)], fill=(255, 226, 90, 255), width=3)
        draw.line([(div_cx - 6, div_y - 3), (div_cx + 6, div_y - 3)], fill=(255, 226, 90, 255), width=3)

    # 7. 3D METALLIC GOLD CTA BUTTON (SAFE ZONE: Y = 1430 to 1520, Width = 640)
    # Positioned safely above Y=1580, completely avoiding Reels caption text and audio pills
    cta_img, cta_mask = get_christian_cta_pill()
    cta_w, cta_h = cta_img.size
    cta_x1 = (width - cta_w) // 2
    cta_y1 = 1430
    overlay.paste(cta_img, (cta_x1, cta_y1), cta_mask)

    # 8. DEVOTIONAL FOOTER (SAFE ZONE: Y = 1545 to 1575)
    foot_txt = "Jesus Hears You • Daily Christian Inspiration"
    f_bb = draw.textbbox((0, 0), foot_txt, font=font_footer)
    f_w = f_bb[2] - f_bb[0]
    f_x = (width - f_w) // 2
    f_y = 1548

    draw.line([(80, f_y + 12), (f_x - 20, f_y + 12)], fill=(215, 185, 95, 160), width=1)
    draw.line([(f_x + f_w + 20, f_y + 12), (width - 80, f_y + 12)], fill=(215, 185, 95, 160), width=1)
    draw.text((f_x, f_y), foot_txt, font=font_footer, fill=(235, 225, 215, 210))

    # BOTTOM ZONE (Y = 1580 to 1920): Left free for native Reels interface & captions!
    overlay_path = os.path.join(OUTPUT_DIR, f"christian_overlay_{int(time.time()*1000)}.png")
    overlay.save(overlay_path, "PNG")
    return overlay_path

def create_christian_word_subtitles(words, width=VIDEO_WIDTH, height=VIDEO_HEIGHT, total_duration=30.0):
    """
    Creates dynamic, progressive 2-line word-by-word subtitles for 'Jesus Hears You':
    - Words appear one by one.
    - Active word glows in radiant divine gold (255, 226, 88).
    - Maximum 2 lines per capsule.
    - When Line 2 is full and finished, clears completely and restarts on Line 1.
    - Deep celestial glass capsule with golden 2px border.
    """
    if not words:
        return None, [], None

    valid_words = []
    for w in words:
        txt = (w.get("text") or "").strip()
        st = float(w.get("start", 0.0))
        et = float(w.get("end", st + 0.2))
        if txt:
            valid_words.append({"text": txt, "start": max(0.0, st), "end": max(st + 0.08, et)})

    if not valid_words:
        return None, [], None

    valid_words.sort(key=lambda x: x["start"])

    font = get_devotional_font(34, bold=False)
    dummy_img = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)

    max_text_width = 820
    line_h = 54
    pill_w = 880
    pill_h = 140
    pill_x = (width - pill_w) // 2
    pill_y = 1260

    # 1. Group words into 2-line pages
    pages = []
    cur_l1 = []
    cur_l2 = []

    for w in valid_words:
        txt = w["text"]
        if not cur_l2:
            test_l1 = " ".join([x["text"] for x in cur_l1] + [txt])
            bbox1 = dummy_draw.textbbox((0, 0), test_l1, font=font)
            if (bbox1[2] - bbox1[0]) <= max_text_width:
                cur_l1.append(w)
                continue
        # Line 1 is full, test Line 2
        test_l2 = " ".join([x["text"] for x in cur_l2] + [txt])
        bbox2 = dummy_draw.textbbox((0, 0), test_l2, font=font)
        if (bbox2[2] - bbox2[0]) <= max_text_width:
            cur_l2.append(w)
        else:
            # Line 2 full! Finish page and restart on Line 1
            pages.append({"line1": cur_l1, "line2": cur_l2})
            cur_l1 = [w]
            cur_l2 = []

    if cur_l1 or cur_l2:
        pages.append({"line1": cur_l1, "line2": cur_l2})

    tmp_dir = tempfile.mkdtemp(prefix="christian_subs_")
    created_files = []

    blank_frame = os.path.join(tmp_dir, "blank.png")
    Image.new("RGBA", (width, height), (0, 0, 0, 0)).save(blank_frame, "PNG")
    created_files.append(blank_frame)

    playlist_entries = []
    prev_time = 0.0

    for p_idx, page in enumerate(pages):
        page_words = page["line1"] + page["line2"]
        if not page_words:
            continue

        p_start = page_words[0]["start"]
        if p_start > prev_time + 0.04:
            gap_dur = round(p_start - prev_time, 3)
            playlist_entries.append((blank_frame, gap_dur))
            prev_time = p_start

        # Calculate centered line offsets
        l1_w_list = [dummy_draw.textbbox((0, 0), x["text"] + " ", font=font)[2] - dummy_draw.textbbox((0, 0), x["text"] + " ", font=font)[0] for x in page["line1"]]
        l1_total_w = sum(l1_w_list)
        l1_start_x = (width - l1_total_w) // 2

        l2_w_list = [dummy_draw.textbbox((0, 0), x["text"] + " ", font=font)[2] - dummy_draw.textbbox((0, 0), x["text"] + " ", font=font)[0] for x in page["line2"]] if page["line2"] else []
        l2_total_w = sum(l2_w_list) if l2_w_list else 0
        l2_start_x = (width - l2_total_w) // 2

        for k in range(len(page_words)):
            w_curr = page_words[k]
            step_start = max(prev_time, w_curr["start"])

            if k < len(page_words) - 1:
                step_end = max(step_start + 0.08, page_words[k + 1]["start"])
            else:
                if p_idx < len(pages) - 1:
                    next_page_start = pages[p_idx + 1]["line1"][0]["start"]
                    step_end = min(max(step_start + 0.25, w_curr["end"] + 0.15), next_page_start)
                else:
                    step_end = max(step_start + 0.3, w_curr["end"] + 0.4)

            step_dur = max(0.06, round(step_end - step_start, 3))

            frame_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(frame_img)

            # Deep Royal Purple Glass Pill with 2px Radiant Gold Border (Safe Zone Y=1260..1400)
            draw.rounded_rectangle(
                [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
                radius=20,
                fill=(26, 7, 36, 235),
                outline=(235, 195, 85, 240),
                width=2
            )

            # Draw Centered Line 1
            visible_l1 = [w for w in page["line1"] if page_words.index(w) <= k]
            is_single_line = len(page["line2"]) == 0
            tx = l1_start_x
            ty = pill_y + 49 if is_single_line else pill_y + 20
            for w in visible_l1:
                is_active = (w == w_curr)
                w_color = (255, 226, 90, 255) if is_active else (255, 255, 255, 255)
                for ox, oy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
                    draw.text((tx + ox, ty + oy), w["text"], font=font, fill=(0, 0, 0, 240))
                draw.text((tx, ty), w["text"], font=font, fill=w_color)
                w_bbox = draw.textbbox((0, 0), w["text"] + " ", font=font)
                tx += (w_bbox[2] - w_bbox[0])

            # Draw Centered Line 2
            visible_l2 = [w for w in page["line2"] if page_words.index(w) <= k]
            if visible_l2:
                tx = l2_start_x
                ty = pill_y + 74
                for w in visible_l2:
                    is_active = (w == w_curr)
                    w_color = (255, 226, 90, 255) if is_active else (255, 255, 255, 235)
                    for ox, oy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
                        draw.text((tx + ox, ty + oy), w["text"], font=font, fill=(0, 0, 0, 240))
                    draw.text((tx, ty), w["text"], font=font, fill=w_color)
                    w_bbox = draw.textbbox((0, 0), w["text"] + " ", font=font)
                    tx += (w_bbox[2] - w_bbox[0])

            frame_file = os.path.join(tmp_dir, f"frame_{p_idx:02d}_{k:03d}.png")
            frame_img.save(frame_file, "PNG", compress_level=1)
            created_files.append(frame_file)

            playlist_entries.append((frame_file, step_dur))
            prev_time = step_end

    if not playlist_entries:
        return None, created_files, tmp_dir

    if prev_time < total_duration:
        rem_dur = round(total_duration - prev_time, 3)
        playlist_entries.append((blank_frame, rem_dur))

    playlist_path = os.path.join(tmp_dir, "sub_playlist.txt")
    with open(playlist_path, "w", encoding="utf-8") as f:
        for fpath, dur in playlist_entries:
            f.write(f"file '{fpath}'\n")
            f.write(f"duration {dur}\n")
        last_f = playlist_entries[-1][0]
        f.write(f"file '{last_f}'\n")

    created_files.append(playlist_path)
    return playlist_path, created_files, tmp_dir

def compose_christian_reel(visual_path, voice_audio_path, voice_duration, headline, verse_reference=None, category="promise", subtitles=None):
    """
    Composes a broadcast-quality 9:16 vertical Reel for 'Jesus Hears You':
    - Supports multiple scene images with Ken Burns zoom & smooth transitions
    - White & Gold Divine UI
    - Word-by-word synchronized subtitles with automatic line clearing
    - Gentle acoustic/piano sidechain ducking
    - Returns: output_video_path
    """
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_video = os.path.join(OUTPUT_DIR, f"christian_reel_{int(time.time())}.mp4")

    # Seamless infinite loop: tight 0.35s tail so reel loops instantly without awkward pause
    total_duration = max(6.0, voice_duration + 0.35)

    overlay_png = create_christian_overlay_card(headline, verse_reference, category)
    files_to_clean = [overlay_png]

    sub_playlist, sub_files, sub_tmp_dir = None, [], None
    if subtitles:
        sub_playlist, sub_files, sub_tmp_dir = create_christian_word_subtitles(
            words=subtitles,
            width=VIDEO_WIDTH,
            height=VIDEO_HEIGHT,
            total_duration=total_duration
        )

    fps = 25
    total_frames = int(total_duration * fps)

    is_multi_image = isinstance(visual_path, (list, tuple)) and len(visual_path) > 1
    single_path = visual_path[0] if (isinstance(visual_path, (list, tuple)) and visual_path) else visual_path

    # Ensure background devotional audio exists
    bg_music = CHRISTIAN_BG_AUDIO_PATH if os.path.exists(CHRISTIAN_BG_AUDIO_PATH) else os.path.join(BASE_DIR, "assets", "audio", "news_bg.mp3")

    extra_inputs = ["-i", overlay_png, "-i", voice_audio_path, "-i", bg_music]
    if sub_playlist:
        extra_inputs.extend(["-f", "concat", "-safe", "0", "-i", sub_playlist])

    is_video_bg = bool(single_path and str(single_path).lower().endswith(('.mp4', '.mov', '.mkv', '.webm')))

    if is_video_bg:
        # Full dynamic motion video background (Pixabay Video)
        input_args = ["-stream_loop", "-1", "-i", single_path]
        overlay_idx = 1
        voice_idx = 2
        bg_audio_idx = 3
        sub_idx = 4

        base_v_filter = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"fps={fps},setsar=1[vbg];"
        )
        if sub_playlist:
            base_v_filter += f"[vbg][{overlay_idx}:v]overlay=0:0[vwith_top];[vwith_top][{sub_idx}:v]overlay=0:0[vout];"
        else:
            base_v_filter += f"[vbg][{overlay_idx}:v]overlay=0:0[vout];"

    elif is_multi_image:
        valid_images = [p for p in visual_path if p and os.path.exists(p)]
        if not valid_images:
            valid_images = [single_path] if single_path else []

        n = len(valid_images)
        slide_dur = total_duration / max(1, n)
        slide_frames = int(slide_dur * fps)

        input_args = []
        filter_parts = []
        concat_inputs = ""

        for i, img in enumerate(valid_images):
            input_args.extend(["-loop", "1", "-t", f"{slide_dur:.2f}", "-i", img])
            zoom_expr = "min(zoom+0.0006,1.06)" if i % 2 == 0 else "max(1.06-0.0006*on,1.0)"
            fade_str = ",fade=t=in:st=0:d=0.4" if i > 0 else ""
            filter_parts.append(
                f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                f"zoompan=z='{zoom_expr}':d={slide_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}{fade_str}[v{i}];"
            )
            concat_inputs += f"[v{i}]"

        filter_parts.append(f"{concat_inputs}concat=n={n}:v=1:a=0[vslides];")
        overlay_idx = n
        voice_idx = n + 1
        bg_audio_idx = n + 2
        sub_idx = n + 3

        if sub_playlist:
            filter_parts.append(f"[vslides][{overlay_idx}:v]overlay=0:0[vwith_top];[vwith_top][{sub_idx}:v]overlay=0:0[vout];")
        else:
            filter_parts.append(f"[vslides][{overlay_idx}:v]overlay=0:0[vout];")
        base_v_filter = "".join(filter_parts)

    else:
        img_target = single_path
        input_args = ["-loop", "1", "-i", img_target]
        overlay_idx = 1
        voice_idx = 2
        bg_audio_idx = 3
        sub_idx = 4

        base_v_filter = (
            f"[0:v]loop=loop=-1:size=1:start=0,"
            f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"zoompan=z='min(zoom+0.00025,1.05)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}[vzoomed];"
        )
        if sub_playlist:
            base_v_filter += f"[vzoomed][{overlay_idx}:v]overlay=0:0[vwith_top];[vwith_top][{sub_idx}:v]overlay=0:0[vout];"
        else:
            base_v_filter += f"[vzoomed][{overlay_idx}:v]overlay=0:0[vout];"

    # Peaceful sidechain ducking: background piano softly dips when voiceover speaks
    audio_filter = (
        f"[{voice_idx}:a]volume=1.0,asplit=2[avoice1][avoice2];"
        f"[{bg_audio_idx}:a]volume=0.08,afade=t=out:st={total_duration - 2.0}:d=2.0[abg];"
        f"[abg][avoice1]sidechaincompress=threshold=0.035:ratio=4.0:attack=80:release=400[ducked_bg];"
        f"[avoice2][ducked_bg]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[aout]"
    )

    filter_complex = base_v_filter + audio_filter

    cmd = [
        ffmpeg, "-y",
        "-threads", "0",
        *input_args,
        *extra_inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", str(total_duration),
        "-movflags", "+faststart",
        out_video
    ]

    try:
        print(f"🎬 Rendering 'Jesus Hears You' Reel with FFmpeg ({total_duration:.1f}s)...")
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"🎉 'Jesus Hears You' Reel rendered successfully: {out_video}")
        return out_video
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr}")
        return None
    finally:
        for f in files_to_clean:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        if sub_tmp_dir and os.path.exists(sub_tmp_dir):
            shutil.rmtree(sub_tmp_dir, ignore_errors=True)
