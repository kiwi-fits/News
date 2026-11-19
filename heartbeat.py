import os
import json
import time
import datetime
import threading
import subprocess

MAC_HEARTBEAT_FILE = os.path.join(os.path.dirname(__file__), "mac_heartbeat.json")
_heartbeat_thread = None
_stop_heartbeat = threading.Event()

def record_heartbeat(status="online", push_to_git=False):
    """
    Records local Mac heartbeat status and timestamp.
    If push_to_git is True, commits and pushes to GitHub so Cloud runner knows Mac state.
    """
    now_utc = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    hb = {
        "status": status,
        "last_heartbeat": now_utc if status == "online" else 0,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "local_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(MAC_HEARTBEAT_FILE, "w", encoding="utf-8") as f:
            json.dump(hb, f, indent=2)
    except Exception as e:
        print(f"Notice: Failed to write heartbeat: {e}")

    if push_to_git:
        sync_heartbeat_to_git()

def sync_heartbeat_to_git(is_offline_handover=False):
    """Commits and pushes mac_heartbeat.json and history to GitHub."""
    try:
        subprocess.run(["git", "add", "mac_heartbeat.json", "seen_articles.json", "reels_history.json", "evergreen_state.json", "rejected_articles.json"], timeout=10, capture_output=True)
        res_diff = subprocess.run(["git", "diff", "--staged", "--quiet"], timeout=6)
        if res_diff.returncode != 0:
            commit_msg = "Handover: Local Mac offline - Cloud Runner start" if is_offline_handover else "Sync Mac heartbeat [skip ci]"
            subprocess.run(["git", "commit", "-m", commit_msg], timeout=10, capture_output=True)
            push_res = subprocess.run(["git", "push", "origin", "main", "--quiet"], timeout=18, capture_output=True)
            if push_res.returncode != 0:
                subprocess.run(["git", "pull", "--rebase", "-X", "ours", "origin", "main", "--quiet"], timeout=18, capture_output=True)
                subprocess.run(["git", "push", "origin", "main", "--quiet"], timeout=18, capture_output=True)
    except Exception as e:
        print(f"Notice: Git sync heartbeat error: {e}")

def mark_offline_and_sync():
    """Called on stop to immediately yield control to cloud."""
    print("📡 Handing control over to Cloud Runner...")
    now_utc = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    hb = {
        "status": "offline",
        "last_heartbeat": 0,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "local_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(MAC_HEARTBEAT_FILE, "w", encoding="utf-8") as f:
            json.dump(hb, f, indent=2)
    except Exception as e:
        print(f"Notice: Failed to write heartbeat: {e}")

    sync_heartbeat_to_git(is_offline_handover=True)

def start_heartbeat_loop(interval_seconds=240):
    """Starts a daemon thread that periodically refreshes heartbeat while local server runs."""
    global _heartbeat_thread, _stop_heartbeat
    if _heartbeat_thread and _heartbeat_thread.is_alive():
        return

    _stop_heartbeat.clear()

    def _loop():
        # First heartbeat immediately
        record_heartbeat(status="online", push_to_git=True)
        while not _stop_heartbeat.is_set():
            _stop_heartbeat.wait(interval_seconds)
            if not _stop_heartbeat.is_set():
                record_heartbeat(status="online", push_to_git=True)

    _heartbeat_thread = threading.Thread(target=_loop, daemon=True, name="MacHeartbeatThread")
    _heartbeat_thread.start()

def stop_heartbeat_loop():
    global _stop_heartbeat
    _stop_heartbeat.set()
    mark_offline_and_sync()
