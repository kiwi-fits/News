import os
import math
import time
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

    # 2. Lower Scrim (Feathered cosine ease from Y=1000 down to 1920)
    fade_start = 1000
    fade_peak = 1200
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

    # 5. Bold Tamil Headline (Y = 1240, 240px safe zone on right side)
    title_font = get_tamil_font(size=52)
    max_text_width = width - 240
    wrapped_lines = wrap_text(headline, title_font, max_text_width, draw)[:4]

    line_height = 74
    start_y = 1240

    for line in wrapped_lines:
        for ox, oy in [(2, 2), (-2, 2), (2, -2), (-2, -2), (0, 3)]:
            draw.text((60 + ox, start_y + oy), line, font=title_font, fill=(0, 0, 0, 255))
        draw.text((60, start_y), line, font=title_font, fill=(255, 255, 255, 255))
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

def compose_ai_news_reel(visual_path, voice_audio_path, voice_duration, headline, category="breaking"):
    """
    Composes the full 9:16 vertical Reel video using FFmpeg:
    - Supports both video clips (.mp4, .mov, etc.) and still images (.jpg, .png)
    - If video: Dual-layer ambient vertical crop + centered video clip
    - If image: Subtle Ken Burns slow cinematic zoom
    - Input 1: Transparent 1080x1920 overlay PNG
    - Input 2: AI Tamil Voiceover MP3
    - Input 3: Background News Audio (ducked at 9% volume)
    Returns: output_video_path
    """
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_video = os.path.join(OUTPUT_DIR, f"reel_{int(time.time())}.mp4")

    # Add 1.5s padding so audio ends gracefully
    total_duration = max(8.0, voice_duration + 1.5)

    overlay_png = create_reel_overlay_card(headline, category)

    fps = 25
    total_frames = int(total_duration * fps)
    is_video = bool(visual_path and visual_path.lower().endswith(('.mp4', '.mov', '.webm', '.mkv', '.m4v')))

    if is_video:
        input_args = ["-stream_loop", "-1", "-i", visual_path]
        filter_complex = (
            f"[0:v]trim=start=0:end={total_duration},setpts=PTS-STARTPTS,split=2[vbg_raw][vfg_raw];"
            f"[vbg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5,eq=brightness=-0.32:contrast=1.05[vbg];"
            f"[vfg_raw]scale=1080:-2,crop=1080:min(ih\\,680):0:(ih-out_h)/2[vfg];"
            f"[vbg][vfg]overlay=0:450[vcomp];"
            f"[vcomp][1:v]overlay=0:0[vout];"
            f"[2:a]volume=1.0[avoice];"
            f"[3:a]volume={BG_AUDIO_VOLUME},afade=t=out:st={total_duration - 2.0}:d=2.0[abg];"
            f"[avoice][abg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
    else:
        input_args = ["-loop", "1", "-i", visual_path]
        filter_complex = (
            f"[0:v]loop=loop=-1:size=1:start=0,"
            f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"zoompan=z='min(zoom+0.0008,1.10)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}[vzoomed];"
            f"[vzoomed][1:v]overlay=0:0[vout];"
            f"[2:a]volume=1.0[avoice];"
            f"[3:a]volume={BG_AUDIO_VOLUME},afade=t=out:st={total_duration - 2.0}:d=2.0[abg];"
            f"[avoice][abg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )

    cmd = [
        ffmpeg, "-y",
        *input_args,
        "-i", overlay_png,
        "-i", voice_audio_path,
        "-i", BG_AUDIO_PATH,
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
        print(f"🎬 Rendering 9:16 AI Reel with FFmpeg ({total_duration:.1f}s)...")
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if os.path.exists(overlay_png):
            try:
                os.remove(overlay_png)
            except Exception:
                pass
        print(f"🎉 9:16 AI Reel rendered successfully: {out_video}")
        return out_video
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr}")
        return None
