import datetime
import threading
import time
from config import CHRISTIAN_POST_INTERVAL_MINUTES, CHRISTIAN_DAILY_TARGET
from christian_pipeline import run_automated_christian_cycle, load_christian_history, get_today_christian_post_count

# Programmatically build exactly 40 daily devotional broadcast slots across 24 hours.
# Spacing: 1440 minutes / 40 posts = exactly 36 minutes per slot.
# Category cycle rotates through 5 devotional themes (8 broadcasts per theme daily).
def build_40_daily_slots():
    slots = []
    cat_cycle = ["promise", "wisdom", "parable", "mystery", "prayer"]
    cat_names = {
        "promise": "Morning Promise & Grace",
        "wisdom": "Biblical Wisdom & Guidance",
        "parable": "Faith Story & Gospel Parable",
        "mystery": "Bible Wonders & History",
        "prayer": "Night Prayer & Peace"
    }
    interval = max(5, CHRISTIAN_POST_INTERVAL_MINUTES)
    for i in range(CHRISTIAN_DAILY_TARGET):
        total_mins = i * interval
        h = (total_mins // 60) % 24
        m = total_mins % 60
        cat_id = cat_cycle[i % len(cat_cycle)]
        period = "AM" if h < 12 else "PM"
        disp_h = h % 12
        if disp_h == 0:
            disp_h = 12
        time_str = f"{disp_h:02d}:{m:02d} {period}"
        slots.append({
            "slot_num": i + 1,
            "id": cat_id,
            "hour": h,
            "minute": m,
            "name": f"Devotional #{i+1}: {cat_names[cat_id]}",
            "time_str": time_str
        })
    return slots

DAILY_SLOTS = build_40_daily_slots()

class ChristianReelScheduler:
    def __init__(self):
        self.running = False
        self.is_processing = False
        self.last_run_time = None
        self.last_posted_slot_day = {}  # Tracks ("slot_X_YYYY-MM-DD") to prevent duplicate slot fires
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
            today_items = [h for h in history if str(h.get("timestamp", "")).startswith(today_str)]
            # Mark corresponding slot numbers as posted today
            for idx in range(min(len(today_items), len(DAILY_SLOTS))):
                slot_key = f"slot_{idx+1}_{today_str}"
                self.last_posted_slot_day[slot_key] = today_str
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
                # If slot was today in the past, calculate for tomorrow
                slot_time += datetime.timedelta(days=1)
            delta_sec = (slot_time - now).total_seconds()
            upcoming.append((delta_sec, slot, slot_time))

        upcoming.sort(key=lambda x: x[0])
        next_delta, next_slot, next_time = upcoming[0]
        return {
            "slot": next_slot,
            "slot_num": next_slot.get("slot_num", 1),
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
            self.log(f"Jesus Hears You automated scheduler active: {len(DAILY_SLOTS)} reels/day target (1 every {CHRISTIAN_POST_INTERVAL_MINUTES}m).")
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

                # Check each slot against current clock time
                for slot in DAILY_SLOTS:
                    slot_target = datetime.datetime(now.year, now.month, now.day, slot["hour"], slot["minute"], 0)
                    diff_seconds = (now - slot_target).total_seconds()

                    # Trigger if current time is within 0 to 120 seconds after the scheduled slot
                    if 0 <= diff_seconds <= 120:
                        slot_key = f"slot_{slot['slot_num']}_{today_str}"
                        if slot_key not in self.last_posted_slot_day:
                            with self._lock:
                                if self.is_processing:
                                    break
                                self.is_processing = True

                            self.log(f"🔔 Reached Slot #{slot['slot_num']} ({slot['time_str']} - {slot['name']})! Publishing Devotional Reel...")
                            try:
                                res = run_automated_christian_cycle(category_id=slot["id"], auto_publish=True)
                                if res.get("success"):
                                    self.last_posted_slot_day[slot_key] = today_str
                                    reel = res.get("reel", {})
                                    self.log(f"🎉 Devotional reel #{slot['slot_num']} published: {reel.get('headline', '')[:40]}")
                                else:
                                    self.log(f"Devotional run failed: {res.get('error')}")
                            except Exception as ex:
                                self.log(f"Error executing slot #{slot['slot_num']}: {ex}")
                            finally:
                                with self._lock:
                                    self.is_processing = False

            except Exception as e:
                self.log(f"Scheduler loop error: {e}")

            # Sleep 15 seconds before next evaluation
            self._stop_event.wait(15)

    def get_status(self):
        next_info = self.get_next_slot()
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        try:
            posted_today_count = get_today_christian_post_count()
        except Exception:
            posted_today_count = len([k for k, v in self.last_posted_slot_day.items() if v == today_str])

        return {
            "running": self.running,
            "is_processing": self.is_processing,
            "next_slot": next_info,
            "posted_today_count": posted_today_count,
            "total_slots": len(DAILY_SLOTS),
            "daily_target": CHRISTIAN_DAILY_TARGET,
            "interval_minutes": CHRISTIAN_POST_INTERVAL_MINUTES,
            "logs": self.logs[:10]
        }

christian_scheduler = ChristianReelScheduler()
