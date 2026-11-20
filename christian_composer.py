import os
import math
import time
import shutil
import tempfile
import subprocess
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
from config import OUTPUT_DIR, CHRISTIAN_BG_AUDIO_PATH, VIDEO_WIDTH, VIDEO_HEIGHT, BASE_DIR

FONT_PATHS = [
    os.path.join(BASE_DIR, "assets", "fonts", "NotoSansTamil-Bold.ttf"),
    "/System/Library/Fonts/Supplemental/Tamil Sangam MN.ttc",
    "/System/Library/Fonts/Supplemental/Tamil MN.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansTamil-Bold.ttf"
]

@lru_cache(maxsize=32)
def get_tamil_font(size):
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()

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

def create_christian_overlay_card(headline, verse_reference=None, category="promise", width=VIDEO_WIDTH, height=VIDEO_HEIGHT):
    """
    Creates the White & Gold Divine 9:16 vertical overlay card for 'Jesus Hears You':
    - Celestial Royal Midnight gradient scrims
    - Frosted pure white category badge with polished gold vector cross
    - 'Jesus Hears You' top branding with gold accent underline (NO AI, NO 24/7)
    - Luminous Sunburst Gold scripture title at Y=1090
    - Scripture reference in pure ivory white
    - Divine Gold Follow CTA pill: '✝ Follow • Jesus Hears You'
    - Clean fellowship footer watermark
    """
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 1. Top Bar Scrim (Celestial Royal gradient Y: 0 to 380)
    for y in range(0, 380):
        ratio = 1.0 - (y / 380.0)
        alpha = int(225 * (ratio ** 1.3))
        draw.line([(0, y), (width, y)], fill=(8, 12, 22, alpha))

    # 2. Lower Scrim (Feathered cosine ease from Y=870 to 1080, then solid royal base)
    fade_start = 870
    fade_peak = 1080
    for y in range(fade_start, fade_peak):
        progress = (y - fade_start) / (fade_peak - fade_start)
        alpha = int(248 * (0.5 * (1 - math.cos(progress * math.pi))))
        draw.line([(0, y), (width, y)], fill=(8, 12, 22, alpha))
    draw.rectangle([0, fade_peak, width, height], fill=(8, 12, 22, 248))

    # Fonts
    font_badge = get_tamil_font(28)
    font_brand = get_tamil_font(32)
    font_title = get_tamil_font(50)
    font_verse_ref = get_tamil_font(34)
    font_cta = get_tamil_font(28)
    font_footer = get_tamil_font(22)

    # Category Badge Text
    cat_badges = {
        "promise": "காலை வாக்குத்தத்தம்",
        "wisdom": "நடைமுறை வேத ஞானம்",
        "parable": "விசுவாச சாட்சி & உவமை",
        "mystery": "வேதாகம ஆச்சரியங்கள்",
        "prayer": "இரவு அமைதி ஜெபம்"
    }
    badge_text = cat_badges.get(category.lower(), "காலை வாக்குத்தத்தம்")
    badge_bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    bw = badge_bbox[2] - badge_bbox[0]
    bh = badge_bbox[3] - badge_bbox[1]

    bx, by = 60, 160
    cross_size = 20
    gap = 12
    pad_x, pad_y = 22, 10
    total_bw = bw + cross_size + gap + (pad_x * 2)

    # 3. Frosted Pure White Pill with 2px Polished Gold Border
    draw.rounded_rectangle(
        [bx, by, bx + total_bw, by + bh + (pad_y * 2)],
        radius=10,
        fill=(255, 255, 255, 245),
        outline=(230, 185, 60, 255),
        width=2
    )

    # Polished Gold Cross Icon inside the white pill
    cx = bx + pad_x + (cross_size // 2)
    cy = by + pad_y + (bh // 2)
    draw.line([(cx, cy - 10), (cx, cy + 10)], fill=(185, 135, 25, 255), width=3)
    draw.line([(cx - 7, cy - 4), (cx + 7, cy - 4)], fill=(185, 135, 25, 255), width=3)

    # Badge Text in Regal Deep Navy
    draw.text((cx + (cross_size // 2) + gap, by + pad_y - 2), badge_text, font=font_badge, fill=(14, 20, 36, 255))

    # 4. Top Right Brand: "Jesus Hears You" (NO AI, NO 24/7)
    brand_name = "Jesus Hears You"
    brand_bbox = draw.textbbox((0, 0), brand_name, font=font_brand)
    brand_w = brand_bbox[2] - brand_bbox[0]

    brand_x = width - 65 - brand_w
    brand_y = by + pad_y - 4
    draw.text((brand_x, brand_y), brand_name, font=font_brand, fill=(255, 255, 255, 255))
    draw.line([(brand_x, brand_y + 40), (brand_x + brand_w, brand_y + 40)], fill=(235, 195, 75, 230), width=2)

    # Elegant Golden Divider Lines framing the central divine visual area (Y: 440 to 1060)
    draw.line([(0, 440), (width, 440)], fill=(235, 195, 75, 140), width=2)
    draw.line([(0, 1060), (width, 1060)], fill=(235, 195, 75, 140), width=2)

    # 5. Main Title: Bold Scripture / Devotional Title (Lifted at Y=1090)
    start_y = 1090
    max_title_w = width - 240
    title_lines = wrap_text(headline, font_title, max_title_w, draw)[:3]

    for line in title_lines:
        for ox, oy in [(3, 3), (-3, 3), (3, -3), (-3, -3), (0, 4), (0, -4), (4, 0), (-4, 0)]:
            draw.text((60 + ox, start_y + oy), line, font=font_title, fill=(0, 0, 0, 255))
        # Radiant Luminous Divine Gold
        draw.text((60, start_y), line, font=font_title, fill=(255, 226, 88, 255))
        start_y += 72

    # Scripture Reference in Pure Ivory White
    if verse_reference:
        clean_ref = verse_reference.strip("— ")
        draw.text((60, start_y + 4), f"— {clean_ref}", font=font_verse_ref, fill=(255, 255, 255, 240))

    # 6. Follow CTA Pill (Y = 1600) - Polished Divine Gold with White Border
    cta_text = "Follow • Jesus Hears You"
    cta_bbox = draw.textbbox((0, 0), cta_text, font=font_cta)
    cta_w, cta_h = cta_bbox[2] - cta_bbox[0], cta_bbox[3] - cta_bbox[1]
    cta_bx, cta_by = 60, 1600
    cta_pad_x, cta_pad_y = 24, 12
    cta_total_w = cta_w + cross_size + gap + (cta_pad_x * 2)

    draw.rounded_rectangle(
        [cta_bx, cta_by, cta_bx + cta_total_w, cta_by + cta_h + (cta_pad_y * 2)],
        radius=24,
        fill=(235, 195, 75, 250),
        outline=(255, 255, 255, 220),
        width=2
    )

    # Cross icon in CTA pill
    pcx = cta_bx + cta_pad_x + (cross_size // 2)
    pcy = cta_by + cta_pad_y + (cta_h // 2)
    draw.line([(pcx, pcy - 9), (pcx, pcy + 9)], fill=(12, 18, 30, 255), width=3)
    draw.line([(pcx - 6, pcy - 3), (pcx + 6, pcy - 3)], fill=(12, 18, 30, 255), width=3)

    draw.text((pcx + (cross_size // 2) + gap, cta_by + cta_pad_y - 2), cta_text, font=font_cta, fill=(12, 18, 30, 255))

    # 7. Clean Divine Fellowship Footer (Y = 1715) - NO AI, NO 24/7
    footer_text = "Jesus Hears You • Tamil Christian Fellowship"
    draw.text((60, 1715), footer_text, font=font_footer, fill=(215, 228, 248, 190))

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

    font = get_tamil_font(36)
    dummy_img = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)

    max_text_width = width - 240
    line_h = 56
    pad_x = 28
    pad_y = 16
    pill_x = 60
    pill_y = 1390

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

        l1_w = dummy_draw.textbbox((0, 0), " ".join([x["text"] for x in page["line1"]]), font=font)[2] - dummy_draw.textbbox((0, 0), " ".join([x["text"] for x in page["line1"]]), font=font)[0]
        l2_w = (dummy_draw.textbbox((0, 0), " ".join([x["text"] for x in page["line2"]]), font=font)[2] - dummy_draw.textbbox((0, 0), " ".join([x["text"] for x in page["line2"]]), font=font)[0]) if page["line2"] else 0
        page_content_w = max(l1_w, l2_w)
        pill_w = max(380, min(max_text_width + (pad_x * 2), page_content_w + (pad_x * 2)))
        pill_h = (line_h * 2 + pad_y * 2) if page["line2"] else (line_h + pad_y * 2)

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

            # Deep Celestial Glass Capsule with Radiant Gold Rim
            draw.rounded_rectangle(
                [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
                radius=16,
                fill=(12, 18, 32, 240),
                outline=(235, 195, 75, 240),
                width=2
            )

            # Draw Line 1
            visible_l1 = [w for w in page["line1"] if page_words.index(w) <= k]
            tx = pill_x + pad_x
            ty = pill_y + pad_y - 2
            for w in visible_l1:
                is_active = (w == w_curr)
                w_color = (255, 226, 88, 255) if is_active else (255, 255, 255, 255)
                for ox, oy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
                    draw.text((tx + ox, ty + oy), w["text"], font=font, fill=(0, 0, 0, 240))
                draw.text((tx, ty), w["text"], font=font, fill=w_color)
                w_bbox = draw.textbbox((0, 0), w["text"] + " ", font=font)
                tx += (w_bbox[2] - w_bbox[0])

            # Draw Line 2
            visible_l2 = [w for w in page["line2"] if page_words.index(w) <= k]
            if visible_l2:
                tx = pill_x + pad_x
                ty = pill_y + pad_y + line_h - 2
                for w in visible_l2:
                    is_active = (w == w_curr)
                    w_color = (255, 226, 88, 255) if is_active else (235, 242, 255, 235)
                    for ox, oy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
                        draw.text((tx + ox, ty + oy), w["text"], font=font, fill=(0, 0, 0, 240))
                    draw.text((tx, ty), w["text"], font=font, fill=w_color)
                    w_bbox = draw.textbbox((0, 0), w["text"] + " ", font=font)
                    tx += (w_bbox[2] - w_bbox[0])

            frame_file = os.path.join(tmp_dir, f"frame_{p_idx:02d}_{k:03d}.png")
            frame_img.save(frame_file, "PNG")
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

    total_duration = max(8.0, voice_duration + 1.8)

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

    if is_multi_image:
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
            f"zoompan=z='min(zoom+0.0006,1.08)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}[vzoomed];"
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
        for f in files_to_clean:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        if sub_tmp_dir and os.path.exists(sub_tmp_dir):
            shutil.rmtree(sub_tmp_dir, ignore_errors=True)
        print(f"🎉 'Jesus Hears You' Reel rendered successfully: {out_video}")
        return out_video
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr}")
        for f in files_to_clean:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        if sub_tmp_dir and os.path.exists(sub_tmp_dir):
            shutil.rmtree(sub_tmp_dir, ignore_errors=True)
        return None
