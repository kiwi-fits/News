#!/usr/bin/env python3
import sys
import argparse
from pipeline import run_automated_news_cycle

def main():
    parser = argparse.ArgumentParser(description="AI Tamil News Reels Automation CLI")
    parser.add_argument("--once", action="store_true", help="Execute one newsroom cycle and exit")
    parser.add_argument("--dry-run", action="store_true", help="Generate reel without uploading to Facebook")
    args = parser.parse_args()

    auto_publish = not args.dry_run
    print(f"🎬 Starting AI Tamil News Reels Runner (Auto-Publish: {auto_publish})...")

    try:
        result = run_automated_news_cycle(auto_publish=auto_publish)
        print("Cycle Execution Result:", result)
        if result.get("processed"):
            print("🎉 Successfully processed and published a new Reel story!")
        else:
            print(f"ℹ️ {result.get('message', 'No new unseen stories.')}")
        return 0
    except Exception as e:
        print(f"❌ Error during automation cycle: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
