import os
import math
import time
import random
import shutil
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

def create_subtitle_overlay(text, width=VIDEO_WIDTH, height=VIDEO_HEIGHT):
    """
    Creates a transparent 1080x1920 PNG with a high-contrast subtitle pill
    at Y=1430 for sound-off mobile viewers.
    """
    if not text or not text.strip():
        return None
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = get_tamil_font(size=36)
    max_w = width - 180
    lines = wrap_text(text.strip(), font, max_w, draw)[:2]
    if not lines:
        return None

    line_h = 52
    total_text_h = len(lines) * line_h
    pad_x = 26
    pad_y = 14
    max_line_w = 0
    for l in lines:
        bbox = draw.textbbox((0, 0), l, font=font)
        max_line_w = max(max_line_w, bbox[2] - bbox[0])
    pill_w = max_line_w + (pad_x * 2)
    pill_h = total_text_h + (pad_y * 2)
    pill_x = 60
    pill_y = 1400
    draw.rounded_rectangle(
        [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
        radius=14,
        fill=(14, 18, 28, 235),
        outline=(255, 185, 0, 210),
        width=2
    )
    ty = pill_y + pad_y - 2
    for l in lines:
        for ox, oy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
            draw.text((pill_x + pad_x + ox, ty + oy), l, font=font, fill=(0, 0, 0, 240))
        draw.text((pill_x + pad_x, ty), l, font=font, fill=(255, 255, 255, 255))
        ty += line_h

    sub_path = os.path.join(OUTPUT_DIR, f"sub_{int(time.time()*1000)}_{random.randint(100,999)}.png")
    overlay.save(sub_path, "PNG")
    return sub_path

def compose_ai_news_reel(visual_path, voice_audio_path, voice_duration, headline, category="breaking", subtitles=None):
    """
    Composes the full 9:16 vertical Reel video using FFmpeg:
    - Supports both video clips (.mp4, .mov, etc.) and still images (.jpg, .png)
    - If MULTIPLE images provided (list): cycles through images with Ken Burns zoom and smooth fade transitions!
    - Dynamic On-Screen Synchronized Subtitles (for 70%+ sound-off mobile viewers)
    - Intelligent Audio Ducking: background music automatically dips when voice speaks and gently swells during breath pauses!
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

    sub_items = []
    if subtitles:
        for sub in subtitles:
            txt = sub.get("text", "").strip()
            st = max(0.0, float(sub.get("start", 0.0)))
            et = max(st + 0.3, float(sub.get("end", 0.0)))
            if txt:
                sp = create_subtitle_overlay(txt)
                if sp and os.path.exists(sp):
                    files_to_clean.append(sp)
                    sub_items.append({"file": sp, "start": st, "end": et})

    fps = 25
    total_frames = int(total_duration * fps)

    is_multi_image = isinstance(visual_path, (list, tuple)) and len(visual_path) > 1
    single_path = visual_path[0] if (isinstance(visual_path, (list, tuple)) and visual_path) else visual_path
    is_video = bool(not is_multi_image and single_path and str(single_path).lower().endswith(('.mp4', '.mov', '.webm', '.mkv', '.m4v')))

    extra_inputs = ["-i", overlay_png, "-i", voice_audio_path, "-i", BG_AUDIO_PATH]
    for s in sub_items:
        extra_inputs.extend(["-i", s["file"]])

    if is_video:
        input_args = ["-stream_loop", "-1", "-i", single_path]
        base_v_filter = (
            f"[0:v]trim=start=0:end={total_duration},setpts=PTS-STARTPTS,split=2[vbg_raw][vfg_raw];"
            f"[vbg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5,eq=brightness=-0.32:contrast=1.05[vbg];"
            f"[vfg_raw]scale=1080:-2,crop=1080:min(ih\\,680):0:(ih-out_h)/2[vfg];"
            f"[vbg][vfg]overlay=0:450[vcomp];"
            f"[vcomp][1:v]overlay=0:0[vsub_0];"
        )
        overlay_idx = 1
        voice_idx = 2
        bg_audio_idx = 3
        sub_start_idx = 4

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
        sub_start_idx = n + 3

        filter_parts.append(f"[vslides][{overlay_idx}:v]overlay=0:0[vsub_0];")
        base_v_filter = "".join(filter_parts)

    else:
        img_target = single_path
        input_args = ["-loop", "1", "-i", img_target]
        base_v_filter = (
            f"[0:v]loop=loop=-1:size=1:start=0,"
            f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"zoompan=z='min(zoom+0.0008,1.10)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}[vzoomed];"
            f"[vzoomed][1:v]overlay=0:0[vsub_0];"
        )
        overlay_idx = 1
        voice_idx = 2
        bg_audio_idx = 3
        sub_start_idx = 4

    # Build timed subtitle overlay chain
    sub_filter_chain = []
    if sub_items:
        for k, sub in enumerate(sub_items):
            cur_in = f"vsub_{k}"
            next_out = "vout" if k == len(sub_items) - 1 else f"vsub_{k+1}"
            sub_file_idx = sub_start_idx + k
            sub_filter_chain.append(
                f"[{cur_in}][{sub_file_idx}:v]overlay=0:0:enable='between(t,{sub['start']:.2f},{sub['end']:.2f})'[{next_out}];"
            )
    else:
        # No subtitles: rename vsub_0 to vout
        base_v_filter = base_v_filter.replace("[vsub_0];", "[vout];")

    # Audio with intelligent sidechain ducking (ducks background music when voice speaks, swells during gaps)
    audio_filter = (
        f"[{voice_idx}:a]volume=1.0,asplit=2[avoice1][avoice2];"
        f"[{bg_audio_idx}:a]volume=0.12,afade=t=out:st={total_duration - 2.0}:d=2.0[abg];"
        f"[abg][avoice1]sidechaincompress=threshold=0.035:ratio=4.5:attack=60:release=350[ducked_bg];"
        f"[avoice2][ducked_bg]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[aout]"
    )

    filter_complex = base_v_filter + "".join(sub_filter_chain) + audio_filter

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
        print(f"🎬 Rendering 9:16 AI Reel with FFmpeg ({total_duration:.1f}s, {len(sub_items)} subtitles)...")
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        for f in files_to_clean:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
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
        return None
