import os
import json
import time
import datetime
import threading
from pipeline import run_automated_news_cycle, run_automated_evergreen_cycle
from config import AUTO_POST_INTERVAL_MINUTES, AUTO_POSTING_ENABLED, FB_PAGE_ID, FB_ACCESS_TOKEN

class AutoReelScheduler:
    def __init__(self):
        self.running = False
        self.interval_minutes = max(1, AUTO_POST_INTERVAL_MINUTES)
        self.auto_publish_fb = bool(FB_PAGE_ID and FB_ACCESS_TOKEN)
        self.last_run_time = None
        self.next_run_time = None
        self.next_run_timestamp = None
        self.last_post_timestamp = time.time()
        self.is_processing = False
        self.logs = []
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._init_last_post_time()

    def _init_last_post_time(self):
        """Reads timestamp of last posted reel to prevent unnecessary idle delays."""
        try:
            h_file = os.path.join(os.path.dirname(__file__), "reels_history.json")
            if os.path.exists(h_file):
                with open(h_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    if history and isinstance(history, list) and len(history) > 0:
                        ts_str = history[0].get("timestamp")
                        if ts_str:
                            dt = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                            self.last_post_timestamp = dt.timestamp()
        except Exception:
            pass

    def log(self, message):
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{now_str}] {message}"
        print(f"⏰ Scheduler: {entry}")
        with self._lock:
            self.logs.insert(0, entry)
            self.logs = self.logs[:30]

    def start(self):
        with self._lock:
            if self.running:
                return False
            self.running = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True, name="AutoReelScheduler")
            self._thread.start()
            self.log(f"Scheduler started. Default cycle: every {self.interval_minutes} minutes.")
            return True

    def stop(self):
        with self._lock:
            if not self.running:
                return False
            self.running = False
            self._stop_event.set()
            self.next_run_time = None
            self.next_run_timestamp = None
            self.is_processing = False
        self.log("Scheduler stopped.")
        return True

    def set_interval(self, minutes):
        with self._lock:
            self.interval_minutes = max(1, int(minutes))
            self.log(f"Interval updated to {self.interval_minutes} minutes.")
            if self.running:
                next_dt = datetime.datetime.now() + datetime.timedelta(minutes=self.interval_minutes)
                self.next_run_time = next_dt.strftime("%Y-%m-%d %H:%M:%S")
                self.next_run_timestamp = time.time() + (self.interval_minutes * 60)

    def run_cycle_now(self):
        """Triggers a cycle immediately in a separate worker thread."""
        def worker():
            self.is_processing = True
            self.log("Automation cycle started. Scanning for latest unseen breaking news...")
            try:
                res = run_automated_news_cycle(auto_publish=self.auto_publish_fb)
                if res.get("processed"):
                    self.last_post_timestamp = time.time()
                    reel = res.get("reel", {})
                    self.log(f"Generated Reel: {reel.get('headline', '')[:40]}... (Status: {reel.get('status')})")
                else:
                    self.log(res.get("message", "No new stories found."))
                    now = time.time()
                    mins_idle = (now - self.last_post_timestamp) / 60
                    if mins_idle >= 30:
                        self.log(f"No news for {int(mins_idle)}m. Triggering Evergreen Fallback Reel...")
                        ev_res = run_automated_evergreen_cycle(auto_publish=self.auto_publish_fb)
                        if ev_res.get("processed"):
                            self.last_post_timestamp = time.time()
                            reel = ev_res.get("reel", {})
                            self.log(f"Generated Evergreen Reel: {reel.get('headline', '')[:40]}... (Status: {reel.get('status')})")
            except Exception as e:
                self.log(f"Cycle execution error: {e}")
            finally:
                self.is_processing = False
            self.last_run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.next_run_timestamp = time.time() + (self.interval_minutes * 60)
            next_dt = datetime.datetime.now() + datetime.timedelta(minutes=self.interval_minutes)
            self.next_run_time = next_dt.strftime("%Y-%m-%d %H:%M:%S")

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return True

    def _loop(self):
        # 8-second initial warmup
        self.next_run_timestamp = time.time() + 8
        self.next_run_time = (datetime.datetime.now() + datetime.timedelta(seconds=8)).strftime("%Y-%m-%d %H:%M:%S")
        self._stop_event.wait(8)

        while self.running and not self._stop_event.is_set():
            self.is_processing = True
            self.next_run_timestamp = None
            self.log("Running scheduled news-to-reel automation cycle...")
            try:
                res = run_automated_news_cycle(auto_publish=self.auto_publish_fb)
                if res.get("processed"):
                    self.last_post_timestamp = time.time()
                    reel = res.get("reel", {})
                    self.log(f"Reel Created: {reel.get('headline', '')[:40]}... Status: {reel.get('status')}")
                else:
                    self.log(res.get("message", "Feeds checked: all up to date."))
                    now = time.time()
                    mins_idle = (now - self.last_post_timestamp) / 60
                    if mins_idle >= 30:
                        self.log(f"Quiet news period ({int(mins_idle)}m with no new posts). Triggering Evergreen Fallback (History/GK/Science/Story)...")
                        ev_res = run_automated_evergreen_cycle(auto_publish=self.auto_publish_fb)
                        if ev_res.get("processed"):
                            self.last_post_timestamp = time.time()
                            reel = ev_res.get("reel", {})
                            self.log(f"Evergreen Reel Published: {reel.get('headline', '')[:40]}... Status: {reel.get('status')}")
                        else:
                            self.log(f"Evergreen notice: {ev_res.get('error', 'Failed')}")
                    else:
                        remaining = max(1, int(30 - mins_idle))
                        self.log(f"News quiet ({int(mins_idle)}m since last post). Evergreen fallback triggers in {remaining}m if no news.")
            except Exception as e:
                self.log(f"Scheduled error: {e}")
            finally:
                self.is_processing = False

            self.last_run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sleep_seconds = self.interval_minutes * 60
            self.next_run_timestamp = time.time() + sleep_seconds
            next_dt = datetime.datetime.now() + datetime.timedelta(seconds=sleep_seconds)
            self.next_run_time = next_dt.strftime("%Y-%m-%d %H:%M:%S")

            self._stop_event.wait(sleep_seconds)

    def get_status(self):
        with self._lock:
            now = time.time()
            if self.is_processing:
                seconds_remaining = 0
            elif self.next_run_timestamp and self.next_run_timestamp > now:
                seconds_remaining = max(0, int(self.next_run_timestamp - now))
            else:
                seconds_remaining = 0

            mins_since_last_post = int(max(0, (now - self.last_post_timestamp) / 60))

            return {
                "running": self.running,
                "interval_minutes": self.interval_minutes,
                "auto_publish_fb": self.auto_publish_fb,
                "last_run": self.last_run_time or "Never",
                "next_run": self.next_run_time or ("Pending" if self.running else "Stopped"),
                "next_run_timestamp": self.next_run_timestamp,
                "seconds_remaining": seconds_remaining,
                "last_post_timestamp": self.last_post_timestamp,
                "mins_since_last_post": mins_since_last_post,
                "is_processing": self.is_processing,
                "logs": list(self.logs)
            }

# Global singleton instance
scheduler = AutoReelScheduler()
