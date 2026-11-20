import os
import json
import time
import datetime
import threading
from pipeline import run_automated_news_cycle, run_automated_evergreen_cycle
from config import AUTO_POST_INTERVAL_SECONDS, AUTO_POST_INTERVAL_MINUTES, FB_PAGE_ID, FB_ACCESS_TOKEN

class AutoReelScheduler:
    def __init__(self):
        self.running = False
        # Allow testing with 10 seconds or configured interval
        self.interval_seconds = max(5, AUTO_POST_INTERVAL_SECONDS if AUTO_POST_INTERVAL_SECONDS > 0 else (AUTO_POST_INTERVAL_MINUTES * 60))
        self.interval_minutes = round(self.interval_seconds / 60.0, 2)
        self.auto_publish_fb = bool(FB_PAGE_ID and FB_ACCESS_TOKEN)
        self.last_run_time = None
        self.next_run_time = None
        self.next_run_timestamp = None
        self.last_post_timestamp = time.time()
        self.last_evergreen_timestamp = 0
        self.evergreen_min_interval = int(os.getenv("EVERGREEN_MIN_INTERVAL_SECONDS", "7200"))  # At most one evergreen reel every 2 hours
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
                                    ts_val = dt.timestamp()
                                    if not self.last_post_timestamp or ts_val > self.last_post_timestamp:
                                        self.last_post_timestamp = ts_val
                                    # Track last evergreen post
                                    if "evergreen" in str(item.get("visual_file", "")) or item.get("source") in ["🏛️ வரலாற்று மர்மம்", "💡 வியக்கவைக்கும் தகவல்", "🔬 அறிவியல் உலகம்", "✨ ஞானச் சிறுகதை"]:
                                        if not self.last_evergreen_timestamp or ts_val > self.last_evergreen_timestamp:
                                            self.last_evergreen_timestamp = ts_val
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
            self.next_run_timestamp = time.time() + self.interval_seconds
            next_dt = datetime.datetime.now() + datetime.timedelta(seconds=self.interval_seconds)
            self.next_run_time = next_dt.strftime("%Y-%m-%d %H:%M:%S")

    def record_post_event(self, headline=""):
        """Called whenever a reel is posted (auto, manual, or evergreen) to reset cycle."""
        with self._lock:
            self.last_post_timestamp = time.time()
            self.reset_countdown()
            desc = f"{self.interval_seconds}s" if self.interval_seconds < 60 else f"{int(self.interval_seconds / 60)}m"
            if headline:
                self.log(f"Post recorded: '{headline[:35]}...' | Resetting {desc} countdown.")

    def start(self):
        with self._lock:
            if self.running:
                return False
            self.running = True
            self._stop_event.clear()
            self.reset_countdown()
            self._thread = threading.Thread(target=self._loop, daemon=True, name="AutoReelScheduler")
            self._thread.start()
            desc = f"{self.interval_seconds}s" if self.interval_seconds < 60 else f"{int(self.interval_seconds / 60)}m"
            self.log(f"Scheduler active: cycle={desc} | monitoring feeds continuously.")
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

    def set_interval(self, minutes_or_seconds):
        with self._lock:
            val = float(minutes_or_seconds)
            if val < 1:  # treated as seconds if fractional or small
                self.interval_seconds = max(5, int(val * 60))
            elif val <= 60 and val == int(val) and val <= 10:  # e.g. 10 sec test
                self.interval_seconds = int(val)
            else:
                self.interval_seconds = max(5, int(val * 60))
            self.interval_minutes = round(self.interval_seconds / 60.0, 2)
            self.reset_countdown()
            desc = f"{self.interval_seconds}s" if self.interval_seconds < 60 else f"{int(self.interval_seconds / 60)}m"
            self.log(f"Interval updated to {desc}. Countdown reset.")

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
                    secs_idle = now - self.last_post_timestamp
                    secs_since_evergreen = now - self.last_evergreen_timestamp
                    quiet_threshold = max(1800, self.interval_seconds * 3)  # Minimum 30 mins quiet period
                    if secs_idle >= quiet_threshold and secs_since_evergreen >= self.evergreen_min_interval:
                        self.log(f"Quiet news period ({int(secs_idle/60)}m no posts, {int(secs_since_evergreen/60)}m since evergreen). Triggering Evergreen Fallback...")
                        ev_res = run_automated_evergreen_cycle(auto_publish=self.auto_publish_fb)
                        if ev_res.get("processed"):
                            self.last_evergreen_timestamp = time.time()
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
        poll_sleep = 30 if self.interval_seconds >= 60 else min(5, max(2, int(self.interval_seconds / 2)))
        self._stop_event.wait(3)

        while self.running and not self._stop_event.is_set():
            self._stop_event.wait(poll_sleep)
            if self._stop_event.is_set() or not self.running:
                break

            if self.is_processing:
                continue

            now = time.time()
            secs_idle = now - self.last_post_timestamp
            quiet_threshold = max(20, self.interval_seconds * 2) if self.interval_seconds < 60 else 30 * 60

            # -------------------------------------------------------------
            # 1. IMMEDIATE BREAKING NEWS CHECK
            # -------------------------------------------------------------
            try:
                res = run_automated_news_cycle(auto_publish=self.auto_publish_fb)
                if res and res.get("processed"):
                    reel = res.get("reel", {})
                    headline = reel.get("headline", "")
                    self.record_post_event(headline)
                    desc = f"{self.interval_seconds}s" if self.interval_seconds < 60 else f"{int(self.interval_seconds / 60)}m"
                    self.log(f"🚨 Breaking News Reel Published: {headline[:35]}! Countdown reset to {desc}.")
                    self.last_run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    continue
            except Exception as e:
                print(f"Notice: News check error: {e}")

            # Re-evaluate idle time after the news check
            now = time.time()
            secs_idle = now - self.last_post_timestamp

            # -------------------------------------------------------------
            # 2. QUIET FALLBACK (Evergreen Reel - Controlled Cadence)
            # -------------------------------------------------------------
            secs_since_evergreen = now - self.last_evergreen_timestamp
            quiet_threshold = max(1800, self.interval_seconds * 3)  # Minimum 30 mins quiet period

            if secs_idle >= quiet_threshold and secs_since_evergreen >= self.evergreen_min_interval:
                idle_desc = f"{int(secs_idle / 60)}m"
                ev_desc = f"{int(secs_since_evergreen / 60)}m"
                self.log(f"Quiet news period ({idle_desc} no new posts, {ev_desc} since last evergreen). Triggering Evergreen Fallback...")
                try:
                    self.is_processing = True
                    ev_res = run_automated_evergreen_cycle(auto_publish=self.auto_publish_fb)
                    if ev_res and ev_res.get("processed"):
                        self.last_evergreen_timestamp = time.time()
                        reel = ev_res.get("reel", {})
                        headline = reel.get("headline", "")
                        self.record_post_event(headline)
                        desc = f"{self.interval_seconds}s" if self.interval_seconds < 60 else f"{int(self.interval_seconds / 60)}m"
                        self.log(f"🏛️ Evergreen Reel Published: {headline[:35]}! Countdown reset to {desc}.")
                    else:
                        self.log(f"Evergreen notice: {ev_res.get('error', 'Skipped')}")
                except Exception as e:
                    self.log(f"Evergreen execution error: {e}")
                finally:
                    self.is_processing = False
                    self.last_run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                continue

            # -------------------------------------------------------------
            # 3. CYCLE ROLLOVER (When timer expires and no news)
            # -------------------------------------------------------------
            if self.next_run_timestamp and now >= self.next_run_timestamp:
                self.reset_countdown()
                remaining = max(1, int(quiet_threshold - secs_idle))
                rem_desc = f"{remaining}s" if remaining < 120 else f"{int(remaining / 60)}m"
                desc = f"{self.interval_seconds}s" if self.interval_seconds < 60 else f"{int(self.interval_seconds / 60)}m"
                self.log(f"⏱️ {desc} timer elapsed with no fresh news. Rolling over. (Evergreen in {rem_desc} if quiet).")
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

            secs_since_last_post = int(max(0, now - self.last_post_timestamp))
            mins_since_last_post = int(secs_since_last_post / 60)

            return {
                "running": self.running,
                "interval_seconds": self.interval_seconds,
                "interval_minutes": self.interval_minutes,
                "auto_publish_fb": self.auto_publish_fb,
                "last_run": self.last_run_time or "Never",
                "next_run": self.next_run_time or ("Pending" if self.running else "Stopped"),
                "next_run_timestamp": self.next_run_timestamp,
                "seconds_remaining": seconds_remaining,
                "last_post_timestamp": self.last_post_timestamp,
                "secs_since_last_post": secs_since_last_post,
                "mins_since_last_post": mins_since_last_post,
                "is_processing": self.is_processing,
                "logs": list(self.logs)
            }

# Global singleton instance
scheduler = AutoReelScheduler()
