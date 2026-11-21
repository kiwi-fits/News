#!/usr/bin/env python3
import os
import sys
import argparse
from christian_pipeline import run_automated_christian_cycle
from config import OUTPUT_DIR

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
    args = parser.parse_args()

    cleanup_stale_christian_media()

    auto_publish = not args.dry_run
    target_category = None if args.category == "auto" else args.category

    print(f"✝️ Starting 'Jesus Hears You' Devotional Automation CLI (Category: {args.category}, Auto-Publish: {auto_publish})...")

    try:
        res = run_automated_christian_cycle(category_id=target_category, auto_publish=auto_publish)
        print("✝️ Devotional Execution Result:", res)
        if res.get("success"):
            reel = res.get("reel", {})
            print(f"🎉 Successfully completed devotional cycle for '{reel.get('badge_tag')}'!")
            return 0
        else:
            print(f"❌ Cycle failed: {res.get('error')}")
            return 1
    except Exception as e:
        print(f"❌ Devotional runner exception: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
