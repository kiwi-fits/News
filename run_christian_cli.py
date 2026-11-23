#!/usr/bin/env python3
import os
import sys
import argparse
from christian_pipeline import run_automated_christian_cycle, get_today_christian_post_count
from config import OUTPUT_DIR, CHRISTIAN_DAILY_TARGET

def cleanup_stale_christian_media():
    """Cleans up temporary intermediate audio/video/image files."""
    if os.path.exists(OUTPUT_DIR):
        for f in os.listdir(OUTPUT_DIR):
            if f.startswith("temp_") or f.endswith(".tmp"):
                try:
                    os.remove(os.path.join(OUTPUT_DIR, f))
                except Exception:
                    pass

def main():
    parser = argparse.ArgumentParser(description="Jesus Hears You - Christian Devotional Reels Runner")
    parser.add_argument(
        "--category",
        choices=["auto", "promise", "wisdom", "parable", "mystery", "prayer"],
        default="auto",
        help="Specify the devotional category or auto-detect by current time"
    )
    parser.add_argument("--dry-run", action="store_true", help="Generate devotional reel without publishing to Facebook")
    parser.add_argument("--youtube", action="store_true", help="Publish directly to YouTube Shorts alongside Facebook")
    parser.add_argument("--force", action="store_true", help="Force cycle execution even if daily target is reached")
    args = parser.parse_args()

    cleanup_stale_christian_media()

    auto_publish = not args.dry_run
    publish_youtube = args.youtube
    target_category = None if args.category == "auto" else args.category

    # Check daily target (40 reels/day) unless --force is passed
    if auto_publish and not args.force:
        today_count = get_today_christian_post_count()
        if today_count >= CHRISTIAN_DAILY_TARGET:
            print(f"✝️ Target of {CHRISTIAN_DAILY_TARGET} devotional reels already reached for today ({today_count}/{CHRISTIAN_DAILY_TARGET}). Skipping cycle.")
            return 0
        print(f"✝️ Today's Devotional Progress: {today_count}/{CHRISTIAN_DAILY_TARGET} posted.")

    print(f"✝️ Starting 'Jesus Hears You' Devotional Automation CLI (Category: {args.category}, Auto-Publish: {auto_publish}, YouTube: {publish_youtube})...")

    try:
        res = run_automated_christian_cycle(category_id=target_category, auto_publish=auto_publish, publish_to_youtube=publish_youtube)
        print("✝️ Devotional Execution Result:", res)
        if res.get("success"):
            reel = res.get("reel", {})
            today_count = get_today_christian_post_count()
            print(f"🎉 Successfully completed devotional cycle for '{reel.get('badge_tag')}'! (Daily count: {today_count}/{CHRISTIAN_DAILY_TARGET})")

            # Run AI comment sync on Facebook to reply to viewer comments
            if auto_publish:
                try:
                    print("💬 Running AI Comment Bot on 'Jesus Hears You' Facebook page...")
                    from fb_comment_bot import run_christian_comment_reply_cycle
                    comment_res = run_christian_comment_reply_cycle(send_private_dms=False)
                    print(f"💬 AI Comment Bot completed: {comment_res.get('replied_count', 0)} comments answered.")
                except Exception as ce:
                    print(f"Notice: AI Comment sync notice: {ce}")

            return 0
        else:
            print(f"❌ Cycle failed: {res.get('error')}")
            return 1
    except Exception as e:
        print(f"❌ Devotional runner exception: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
