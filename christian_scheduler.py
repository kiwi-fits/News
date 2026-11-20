import os
import time
import datetime
import threading
from config import CHRISTIAN_FB_PAGE_ID, CHRISTIAN_FB_ACCESS_TOKEN
from christian_content_engine import CHRISTIAN_CATEGORIES, get_scheduled_christian_category
from christian_pipeline import run_automated_christian_cycle, load_christian_history

# Exact Daily Schedule for "Jesus Hears You"
# Times in 24h format (HH, MM)
DAILY_SLOTS = [
    {"id": "promise", "hour": 6,  "minute": 0,  "name": "காலை வாக்குத்தத்தம்", "time_str": "06:00 AM"},
    {"id": "wisdom",  "hour": 12, "minute": 30, "name": "நடைமுறை வேத ஞானம்", "time_str": "12:30 PM"},
    {"id": "parable", "hour": 16, "minute": 30, "name": "விசுவாச சாட்சி & உவமை", "time_str": "04:30 PM"},
    {"id": "mystery", "hour": 19, "minute": 30, "name": "வேதாகம ஆச்சரியங்கள்", "time_str": "07:30 PM"},
    {"id": "prayer",  "hour": 21, "minute": 30, "name": "இரவு அமைதி ஜெபம்",   "time_str": "09:30 PM"},
]

class ChristianReelScheduler:
    def __init__(self):
        self.running = False
        self.is_processing = False
        self.last_run_time = None
        self.last_posted_slot_day = {}  # Tracks (slot_id, "YYYY-MM-DD") to prevent duplicate posts on same day
        self.logs = []
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._init_history_state()

    def _init_history_state(self):
        """Pre-populate posted slots from today's history so restart doesn't re-fire."""
        try:
            history = load_christian_history()
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            for item in history:
                ts = item.get("timestamp", "")
                cat_id = item.get("category_id")
                if ts.startswith(today_str) and cat_id:
                    self.last_posted_slot_day[cat_id] = today_str
        except Exception:
            pass

    def log(self, message):
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{now_str}] {message}"
        print(f"✝️ Christian Scheduler: {entry}")
        with self._lock:
            self.logs.insert(0, entry)
            self.logs = self.logs[:30]

    def get_next_slot(self):
        """Returns the upcoming slot info and seconds remaining."""
        now = datetime.datetime.now()
        today = now.date()
        upcoming = []

        for slot in DAILY_SLOTS:
            slot_time = datetime.datetime(today.year, today.month, today.day, slot["hour"], slot["minute"], 0)
            if slot_time <= now:
                # If slot was today in the past, consider tomorrow's slot
                slot_time += datetime.timedelta(days=1)
            delta_sec = (slot_time - now).total_seconds()
            upcoming.append((delta_sec, slot, slot_time))

        upcoming.sort(key=lambda x: x[0])
        next_delta, next_slot, next_time = upcoming[0]
        return {
            "slot": next_slot,
            "target_time": next_time.strftime("%Y-%m-%d %I:%M %p"),
            "seconds_remaining": max(0, int(next_delta)),
            "time_str": next_slot["time_str"],
            "name": next_slot["name"],
            "category_id": next_slot["id"]
        }

    def start(self):
        with self._lock:
            if self.running:
                return False
            self.running = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True, name="ChristianSchedulerThread")
            self._thread.start()
            self.log("Jesus Hears You automated devotional scheduler started.")
            return True

    def stop(self):
        with self._lock:
            if not self.running:
                return False
            self.running = False
            self._stop_event.set()
            self.is_processing = False
        self.log("Jesus Hears You devotional scheduler stopped.")
        return True

    def run_cycle_now(self, category_id=None, auto_publish=True):
        """Manually trigger a devotional generation cycle."""
        with self._lock:
            if self.is_processing:
                return {"success": False, "error": "Devotional cycle is already in progress."}
            self.is_processing = True

        def _worker():
            try:
                self.log(f"Manual devotional cycle triggered (Category: {category_id or 'auto'})...")
                res = run_automated_christian_cycle(category_id=category_id, auto_publish=auto_publish)
                if res.get("success"):
                    reel = res.get("reel", {})
                    self.log(f"Devotional successfully created: '{reel.get('badge_tag')}'")
                else:
                    self.log(f"Devotional generation failed: {res.get('error')}")
            except Exception as e:
                self.log(f"Error during manual cycle: {e}")
            finally:
                with self._lock:
                    self.is_processing = False

        threading.Thread(target=_worker, daemon=True).start()
        return {"success": True, "message": "Devotional generation started."}

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                now = datetime.datetime.now()
                today_str = now.strftime("%Y-%m-%d")

                # Check each slot against current time
                for slot in DAILY_SLOTS:
                    slot_target = datetime.datetime(now.year, now.month, now.day, slot["hour"], slot["minute"], 0)
                    diff_seconds = (now - slot_target).total_seconds()

                    # Trigger if current time is within 0 to 90 seconds after the scheduled time
                    if 0 <= diff_seconds <= 90:
                        slot_key = slot["id"]
                        if self.last_posted_slot_day.get(slot_key) != today_str:
                            with self._lock:
                                if self.is_processing:
                                    break
                                self.is_processing = True

                            self.log(f"🔔 Reached scheduled slot {slot['time_str']} ({slot['name']})! Publishing Devotional Reel...")
                            try:
                                res = run_automated_christian_cycle(category_id=slot_key, auto_publish=True)
                                if res.get("success"):
                                    self.last_posted_slot_day[slot_key] = today_str
                                    reel = res.get("reel", {})
                                    self.log(f"🎉 Devotional reel published for {slot['name']}: {reel.get('headline')[:40]}")
                                else:
                                    self.log(f"Devotional run failed: {res.get('error')}")
                            except Exception as ex:
                                self.log(f"Error executing slot {slot['name']}: {ex}")
                            finally:
                                with self._lock:
                                    self.is_processing = False

            except Exception as e:
                self.log(f"Scheduler loop error: {e}")

            # Sleep 15 seconds before next check
            self._stop_event.wait(15)

    def get_status(self):
        next_info = self.get_next_slot()
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        posted_today = [k for k, v in self.last_posted_slot_day.items() if v == today_str]

        return {
            "running": self.running,
            "is_processing": self.is_processing,
            "next_slot": next_info,
            "posted_today_count": len(posted_today),
            "posted_slots_today": posted_today,
            "total_slots": len(DAILY_SLOTS),
            "logs": self.logs[:10]
        }

christian_scheduler = ChristianReelScheduler()
