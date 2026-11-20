import os
import math
import time
import random
import shutil
import tempfile
import subprocess
from PIL import Image, ImageDraw, ImageFont
from config import OUTPUT_DIR, BG_AUDIO_PATH, BG_AUDIO_VOLUME, VIDEO_WIDTH, VIDEO_HEIGHT, BASE_DIR

FONT_PATHS = [
    os.path.join(BASE_DIR, "assets", "fonts", "NotoSansTamil-Bold.ttf"),
    "/System/Library/Fonts/Supplemental/Tamil Sangam MN.ttc",
    "/System/Library/Fonts/Supplemental/Tamil MN.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansTamil-Bold.ttf"
]

CATEGORY_THEMES = {
    "breaking": {"badge": "பிரேக்கிங் செய்தி", "bg": (225, 25, 35)},
    "local": {"badge": "இலங்கை செய்தி", "bg": (215, 60, 20)},
    "world": {"badge": "உலகச் செய்தி", "bg": (20, 110, 210)},
    "politics": {"badge": "அரசியல் களம்", "bg": (140, 30, 170)},
    "economy": {"badge": "பொருளாதாரம்", "bg": (195, 140, 10)},
    "sports": {"badge": "விளையாட்டு", "bg": (25, 150, 70)},
    "history": {"badge": "வரலாற்று மர்மம்", "bg": (180, 83, 9)},
    "gk": {"badge": "வியக்கவைக்கும் தகவல்", "bg": (14, 165, 233)},
    "science": {"badge": "அறிவியல் உலகம்", "bg": (99, 102, 241)},
    "story": {"badge": "ஞானச் சிறுகதை", "bg": (16, 185, 129)}
}

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

def create_reel_overlay_card(headline, category="breaking", width=VIDEO_WIDTH, height=VIDEO_HEIGHT):
    """
    Creates a transparent 1080x1920 broadcast PNG overlay:
    - Top safe-zone scrim & category badge
    - Lower obsidian glass cosine fade scrim
    - Bold 52px Tamil headline (with 240px right margin safe zone)
    - Follow CTA pill with vector plus icon
    - Branded footer watermark
    """
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 1. Top Bar Scrim (Y: 0 to 360)
    for y in range(0, 360):
        ratio = 1.0 - (y / 360.0)
        alpha = int(220 * (ratio ** 1.3))
        draw.line([(0, y), (width, y)], fill=(8, 10, 15, alpha))

    # 2. Lower Scrim (Feathered cosine ease from Y=900 down to 1920)
    fade_start = 900
    fade_peak = 1080
    for y in range(fade_start, height):
        if y < fade_peak:
            progress = (y - fade_start) / (fade_peak - fade_start)
            alpha = int(245 * (0.5 * (1 - math.cos(progress * math.pi))))
        else:
            alpha = 245
        draw.line([(0, y), (width, y)], fill=(8, 10, 15, alpha))

    # 3. Category Theme
    cat_info = CATEGORY_THEMES.get(category.lower(), CATEGORY_THEMES["breaking"])
    badge_label = cat_info["badge"]
    badge_color = cat_info["bg"]

    # 4. Top Category Badge (Y = 160)
    badge_font = get_tamil_font(size=28)
    bbox = draw.textbbox((0, 0), badge_label, font=badge_font)
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]

    bx, by = 60, 160
    pad_x, pad_y = 18, 10
    dot_radius = 6
    dot_gap = 10
    dot_width = (dot_radius * 2) + dot_gap
    total_badge_w = bw + (pad_x * 2) + dot_width

    draw.rounded_rectangle(
        [bx, by, bx + total_badge_w, by + bh + (pad_y * 2)],
        radius=8,
        fill=(*badge_color, 255)
    )

    # Glowing vector live circle (Pillow vector dot, 100% immune to emoji tofu)
    dot_cx = bx + pad_x + dot_radius
    dot_cy = by + pad_y + (bh // 2)
    draw.ellipse(
        [dot_cx - dot_radius, dot_cy - dot_radius, dot_cx + dot_radius, dot_cy + dot_radius],
        fill=(255, 255, 255, 255)
    )
    draw.text((dot_cx + dot_radius + dot_gap, by + pad_y - 2), badge_label, font=badge_font, fill=(255, 255, 255, 255))

    # Top Brand Watermark
    brand_font = get_tamil_font(size=30)
    brand_name = "செய்தி மையம் AI"
    brand_bbox = draw.textbbox((0, 0), brand_name, font=brand_font)
    brand_w = brand_bbox[2] - brand_bbox[0]
    draw.text((width - 65 - brand_w, by + pad_y - 2), brand_name, font=brand_font, fill=(255, 255, 255, 240))

    # 5. Bold Tamil Headline (Lifted up to Y=1090, 240px safe zone on right side, vibrant news yellow)
    title_font = get_tamil_font(size=52)
    max_text_width = width - 240
    wrapped_lines = wrap_text(headline, title_font, max_text_width, draw)[:4]

    line_height = 74
    start_y = 1090

    for line in wrapped_lines:
        for ox, oy in [(3, 3), (-3, 3), (3, -3), (-3, -3), (0, 4), (0, -4), (4, 0), (-4, 0)]:
            draw.text((60 + ox, start_y + oy), line, font=title_font, fill=(0, 0, 0, 255))
        # Radiant Broadcast Gold/Yellow Title
        draw.text((60, start_y), line, font=title_font, fill=(255, 222, 25, 255))
        start_y += line_height

    # 6. Follow CTA Pill with Vector Plus Icon (Y = 1600)
    cta_font = get_tamil_font(size=26)
    cta_text = "Follow • உடனுக்குடன் உண்மைச் செய்திகள்"
    cta_bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
    cta_w, cta_h = cta_bbox[2] - cta_bbox[0], cta_bbox[3] - cta_bbox[1]

    plus_size = 14
    plus_gap = 12
    cta_bx, cta_by = 60, 1600
    cta_pad_x, cta_pad_y = 22, 12

    total_pill_w = cta_w + plus_size + plus_gap + (cta_pad_x * 2)
    draw.rounded_rectangle(
        [cta_bx, cta_by, cta_bx + total_pill_w, cta_by + cta_h + (cta_pad_y * 2)],
        radius=22,
        fill=(255, 185, 0, 245)
    )

    # Vector plus icon
    plus_cx = cta_bx + cta_pad_x + (plus_size // 2)
    plus_cy = cta_by + cta_pad_y + (cta_h // 2)
    draw.line([(plus_cx - 7, plus_cy), (plus_cx + 7, plus_cy)], fill=(12, 16, 24, 255), width=3)
    draw.line([(plus_cx, plus_cy - 7), (plus_cx, plus_cy + 7)], fill=(12, 16, 24, 255), width=3)

    # CTA Text
    draw.text((plus_cx + (plus_size // 2) + plus_gap, cta_by + cta_pad_y - 2), cta_text, font=cta_font, fill=(12, 16, 24, 255))

    # 7. Clean Brand Footer Watermark
    footer_font = get_tamil_font(size=22)
    draw.text((60, 1700), "செய்தி மையம் • 24/7 Sri Lanka Tamil AI News", font=footer_font, fill=(180, 190, 205, 190))

    overlay_path = os.path.join(OUTPUT_DIR, f"overlay_{int(time.time())}.png")
    overlay.save(overlay_path, "PNG")
    return overlay_path

def create_word_by_word_subtitle_track(words, width=VIDEO_WIDTH, height=VIDEO_HEIGHT, total_duration=30.0):
    """
    Creates a dynamic, progressive 2-line word-by-word subtitle track:
    - Words appear one by one as they are spoken.
    - Maximum 2 lines per subtitle capsule/page.
    - Active spoken word is highlighted in radiant broadcast yellow.
    - When Line 2 is full and finished, clears both lines completely.
    - Next words start cleanly from Line 1 again, appearing one by one.
    - Returns: (playlist_path, list_of_temp_files, temp_directory)
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

    font = get_tamil_font(size=36)
    dummy_img = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)

    max_text_width = width - 240  # 840px max text width
    line_h = 56
    pad_x = 28
    pad_y = 16
    pill_x = 60
    pill_y = 1400

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
            # Line 2 is full! Finish this 2-line page and start fresh on Line 1
            pages.append({"line1": cur_l1, "line2": cur_l2})
            cur_l1 = [w]
            cur_l2 = []

    if cur_l1 or cur_l2:
        pages.append({"line1": cur_l1, "line2": cur_l2})

    tmp_dir = tempfile.mkdtemp(prefix="sub_frames_")
    created_files = []

    # Transparent blank frame
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
        # Clear screen with blank frame during silence before page starts
        if p_start > prev_time + 0.04:
            gap_dur = round(p_start - prev_time, 3)
            playlist_entries.append((blank_frame, gap_dur))
            prev_time = p_start

        # Measure page width for steady visual container
        l1_w = dummy_draw.textbbox((0, 0), " ".join([x["text"] for x in page["line1"]]), font=font)[2] - dummy_draw.textbbox((0, 0), " ".join([x["text"] for x in page["line1"]]), font=font)[0]
        l2_w = (dummy_draw.textbbox((0, 0), " ".join([x["text"] for x in page["line2"]]), font=font)[2] - dummy_draw.textbbox((0, 0), " ".join([x["text"] for x in page["line2"]]), font=font)[0]) if page["line2"] else 0
        page_content_w = max(l1_w, l2_w)
        pill_w = max(380, min(max_text_width + (pad_x * 2), page_content_w + (pad_x * 2)))
        pill_h = (line_h * 2 + pad_y * 2) if page["line2"] else (line_h + pad_y * 2)

        # Render word-by-word progressive reveals
        for k in range(len(page_words)):
            w_curr = page_words[k]
            step_start = max(prev_time, w_curr["start"])

            if k < len(page_words) - 1:
                step_end = max(step_start + 0.08, page_words[k + 1]["start"])
            else:
                # Last word of this 2-line page: clear before next page begins
                if p_idx < len(pages) - 1:
                    next_page_start = pages[p_idx + 1]["line1"][0]["start"]
                    step_end = min(max(step_start + 0.25, w_curr["end"] + 0.15), next_page_start)
                else:
                    step_end = max(step_start + 0.3, w_curr["end"] + 0.4)

            step_dur = max(0.06, round(step_end - step_start, 3))

            frame_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(frame_img)

            # High-contrast obsidian glass capsule
            draw.rounded_rectangle(
                [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
                radius=14,
                fill=(14, 18, 28, 235),
                outline=(255, 185, 0, 210),
                width=2
            )

            # Draw Line 1 words visible so far
            visible_l1 = [w for w in page["line1"] if page_words.index(w) <= k]
            tx = pill_x + pad_x
            ty = pill_y + pad_y - 2
            for w in visible_l1:
                is_active = (w == w_curr)
                w_color = (255, 222, 25, 255) if is_active else (255, 255, 255, 255)
                for ox, oy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
                    draw.text((tx + ox, ty + oy), w["text"], font=font, fill=(0, 0, 0, 240))
                draw.text((tx, ty), w["text"], font=font, fill=w_color)
                w_bbox = draw.textbbox((0, 0), w["text"] + " ", font=font)
                tx += (w_bbox[2] - w_bbox[0])

            # Draw Line 2 words visible so far
            visible_l2 = [w for w in page["line2"] if page_words.index(w) <= k]
            if visible_l2:
                tx = pill_x + pad_x
                ty = pill_y + pad_y + line_h - 2
                for w in visible_l2:
                    is_active = (w == w_curr)
                    w_color = (255, 222, 25, 255) if is_active else (255, 255, 255, 255)
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

def compose_ai_news_reel(visual_path, voice_audio_path, voice_duration, headline, category="breaking", subtitles=None):
    """
    Composes the full 9:16 vertical Reel video using FFmpeg:
    - Supports both video clips (.mp4, .mov, etc.) and still images (.jpg, .png)
    - If MULTIPLE images provided (list): cycles through images with Ken Burns zoom and smooth fade transitions!
    - Word-by-word synchronized 2-line progressive subtitles (with automatic line clearing when full)
    - Intelligent Audio Ducking: background music automatically dips when voice speaks and swells during breath pauses!
    - Video: Dual-layer ambient vertical crop + centered video clip
    - Returns: output_video_path
    """
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_video = os.path.join(OUTPUT_DIR, f"reel_{int(time.time())}.mp4")

    # Add 1.5s padding so audio ends gracefully
    total_duration = max(8.0, voice_duration + 1.5)

    overlay_png = create_reel_overlay_card(headline, category)
    files_to_clean = [overlay_png]

    # Generate progressive word-by-word subtitle track
    sub_playlist, sub_files, sub_tmp_dir = None, [], None
    if subtitles:
        sub_playlist, sub_files, sub_tmp_dir = create_word_by_word_subtitle_track(
            words=subtitles,
            width=VIDEO_WIDTH,
            height=VIDEO_HEIGHT,
            total_duration=total_duration
        )

    fps = 25
    total_frames = int(total_duration * fps)

    is_multi_image = isinstance(visual_path, (list, tuple)) and len(visual_path) > 1
    single_path = visual_path[0] if (isinstance(visual_path, (list, tuple)) and visual_path) else visual_path
    is_video = bool(not is_multi_image and single_path and str(single_path).lower().endswith(('.mp4', '.mov', '.webm', '.mkv', '.m4v')))

    extra_inputs = ["-i", overlay_png, "-i", voice_audio_path, "-i", BG_AUDIO_PATH]
    if sub_playlist:
        extra_inputs.extend(["-f", "concat", "-safe", "0", "-i", sub_playlist])

    if is_video:
        input_args = ["-stream_loop", "-1", "-i", single_path]
        overlay_idx = 1
        voice_idx = 2
        bg_audio_idx = 3
        sub_idx = 4

        base_v_filter = (
            f"[0:v]trim=start=0:end={total_duration},setpts=PTS-STARTPTS,split=2[vbg_raw][vfg_raw];"
            f"[vbg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5,eq=brightness=-0.32:contrast=1.05[vbg];"
            f"[vfg_raw]scale=1080:-2,crop=1080:min(ih\\,680):0:(ih-out_h)/2[vfg];"
            f"[vbg][vfg]overlay=0:450[vcomp];"
        )
        if sub_playlist:
            base_v_filter += f"[vcomp][{overlay_idx}:v]overlay=0:0[vwith_top];[vwith_top][{sub_idx}:v]overlay=0:0[vout];"
        else:
            base_v_filter += f"[vcomp][{overlay_idx}:v]overlay=0:0[vout];"

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
            zoom_expr = "min(zoom+0.0008,1.08)" if i % 2 == 0 else "max(1.08-0.0008*on,1.0)"
            fade_str = ",fade=t=in:st=0:d=0.35" if i > 0 else ""
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
            f"zoompan=z='min(zoom+0.0008,1.10)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}[vzoomed];"
        )
        if sub_playlist:
            base_v_filter += f"[vzoomed][{overlay_idx}:v]overlay=0:0[vwith_top];[vwith_top][{sub_idx}:v]overlay=0:0[vout];"
        else:
            base_v_filter += f"[vzoomed][{overlay_idx}:v]overlay=0:0[vout];"

    # Audio with intelligent sidechain ducking
    audio_filter = (
        f"[{voice_idx}:a]volume=1.0,asplit=2[avoice1][avoice2];"
        f"[{bg_audio_idx}:a]volume=0.12,afade=t=out:st={total_duration - 2.0}:d=2.0[abg];"
        f"[abg][avoice1]sidechaincompress=threshold=0.035:ratio=4.5:attack=60:release=350[ducked_bg];"
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
        num_sub_words = len(subtitles) if subtitles else 0
        print(f"🎬 Rendering 9:16 AI Reel with FFmpeg ({total_duration:.1f}s, {num_sub_words} word-synced subtitles)...")
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        for f in files_to_clean:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        if sub_tmp_dir and os.path.exists(sub_tmp_dir):
            shutil.rmtree(sub_tmp_dir, ignore_errors=True)
        print(f"🎉 9:16 AI Reel rendered successfully: {out_video}")
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
