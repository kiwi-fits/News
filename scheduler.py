import os
import json
import time
import datetime
import threading
from pipeline import run_automated_news_cycle, run_automated_evergreen_cycle
from config import AUTO_POST_INTERVAL_MINUTES, AUTO_POSTING_ENABLED, FB_PAGE_ID, FB_ACCESS_TOKEN

POLL_INTERVAL_SECONDS = 30  # Fast, lightweight breaking news monitor interval

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
        self.reset_countdown()

    def _init_last_post_time(self):
        """Reads timestamp of last posted reel to prevent unnecessary idle delays."""
        try:
            h_file = os.path.join(os.path.dirname(__file__), "reels_history.json")
            if os.path.exists(h_file):
                with open(h_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    if history and isinstance(history, list):
                        for item in history:
                            if item.get("status") == "Published to Facebook" or item.get("fb_video_id"):
                                ts_str = item.get("timestamp")
                                if ts_str:
                                    dt = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                                    self.last_post_timestamp = dt.timestamp()
                                    break
        except Exception:
            pass

    def log(self, message):
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{now_str}] {message}"
        print(f"⏰ Scheduler: {entry}")
        with self._lock:
            self.logs.insert(0, entry)
            self.logs = self.logs[:30]

    def reset_countdown(self):
        """Resets the timer countdown to full interval from current moment."""
        with self._lock:
            self.next_run_timestamp = time.time() + (self.interval_minutes * 60)
            next_dt = datetime.datetime.now() + datetime.timedelta(minutes=self.interval_minutes)
            self.next_run_time = next_dt.strftime("%Y-%m-%d %H:%M:%S")

    def record_post_event(self, headline=""):
        """Called whenever a reel is posted (auto, manual, or evergreen) to reset cycle."""
        with self._lock:
            self.last_post_timestamp = time.time()
            self.reset_countdown()
            if headline:
                self.log(f"Post recorded: '{headline[:35]}...' | Resetting {self.interval_minutes}m countdown.")

    def start(self):
        with self._lock:
            if self.running:
                return False
            self.running = True
            self._stop_event.clear()
            self.reset_countdown()
            self._thread = threading.Thread(target=self._loop, daemon=True, name="AutoReelScheduler")
            self._thread.start()
            self.log(f"Scheduler active: checking feeds every {POLL_INTERVAL_SECONDS}s | cycle: {self.interval_minutes}m | evergreen fallback: 30m idle.")
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
            self.reset_countdown()
            self.log(f"Interval updated to {self.interval_minutes} minutes. Countdown reset.")

    def run_cycle_now(self):
        """Triggers a cycle immediately in a separate worker thread."""
        def worker():
            with self._lock:
                if self.is_processing:
                    self.log("Automation cycle already running, please wait...")
                    return
                self.is_processing = True

            self.log("Manual automation scan triggered. Checking feeds for unseen breaking news...")
            try:
                res = run_automated_news_cycle(auto_publish=self.auto_publish_fb)
                if res.get("processed"):
                    reel = res.get("reel", {})
                    headline = reel.get("headline", "")
                    self.record_post_event(headline)
                    self.log(f"Generated Breaking Reel: {headline[:40]}... (Status: {reel.get('status')})")
                else:
                    self.log(res.get("message", "No new stories found."))
                    now = time.time()
                    mins_idle = (now - self.last_post_timestamp) / 60
                    if mins_idle >= 30:
                        self.log(f"No news for {int(mins_idle)}m. Triggering Evergreen Fallback Reel...")
                        ev_res = run_automated_evergreen_cycle(auto_publish=self.auto_publish_fb)
                        if ev_res.get("processed"):
                            reel = ev_res.get("reel", {})
                            headline = reel.get("headline", "")
                            self.record_post_event(headline)
                            self.log(f"Generated Evergreen Reel: {headline[:40]}... (Status: {reel.get('status')})")
            except Exception as e:
                self.log(f"Cycle execution error: {e}")
            finally:
                self.is_processing = False
                self.last_run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return True

    def _loop(self):
        # Initial warmup delay
        self.reset_countdown()
        self._stop_event.wait(6)

        while self.running and not self._stop_event.is_set():
            # Wait for next poll interval (30 seconds)
            self._stop_event.wait(POLL_INTERVAL_SECONDS)
            if self._stop_event.is_set() or not self.running:
                break

            # If already processing a video in worker thread, skip this poll
            if self.is_processing:
                continue

            now = time.time()
            mins_idle = (now - self.last_post_timestamp) / 60

            # -------------------------------------------------------------
            # 1. IMMEDIATE BREAKING NEWS CHECK (Every 30s)
            # -------------------------------------------------------------
            try:
                res = run_automated_news_cycle(auto_publish=self.auto_publish_fb)
                if res and res.get("processed"):
                    reel = res.get("reel", {})
                    headline = reel.get("headline", "")
                    self.record_post_event(headline)
                    self.log(f"🚨 Breaking News Reel Published: {headline[:35]}! Countdown reset to {self.interval_minutes}m.")
                    self.last_run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    continue
            except Exception as e:
                print(f"Notice: Periodic news check error: {e}")

            # Re-evaluate idle time after the news check
            now = time.time()
            mins_idle = (now - self.last_post_timestamp) / 60

            # -------------------------------------------------------------
            # 2. 30-MINUTE QUIET FALLBACK (Evergreen Reel)
            # If 30+ minutes pass with zero posts, post Evergreen Fallback
            # -------------------------------------------------------------
            if mins_idle >= 30:
                self.log(f"Quiet news period ({int(mins_idle)}m with no new posts). Triggering Evergreen Fallback (History/GK/Science/Story)...")
                try:
                    self.is_processing = True
                    ev_res = run_automated_evergreen_cycle(auto_publish=self.auto_publish_fb)
                    if ev_res and ev_res.get("processed"):
                        reel = ev_res.get("reel", {})
                        headline = reel.get("headline", "")
                        self.record_post_event(headline)
                        self.log(f"🏛️ Evergreen Reel Published: {headline[:35]}! Countdown reset to {self.interval_minutes}m.")
                    else:
                        self.log(f"Evergreen generation notice: {ev_res.get('error', 'Skipped')}")
                except Exception as e:
                    self.log(f"Evergreen execution error: {e}")
                finally:
                    self.is_processing = False
                    self.last_run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                continue

            # -------------------------------------------------------------
            # 3. 15-MINUTE CYCLE ROLLOVER (When timer expires and no news)
            # -------------------------------------------------------------
            if self.next_run_timestamp and now >= self.next_run_timestamp:
                self.reset_countdown()
                remaining_to_evergreen = max(1, int(30 - mins_idle))
                self.log(f"⏱️ {self.interval_minutes}m timer elapsed with no fresh news. Rolling to next {self.interval_minutes}m cycle. (Evergreen in {remaining_to_evergreen}m if quiet).")
                self.last_run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
