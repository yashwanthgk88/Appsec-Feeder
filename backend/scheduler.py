"""In-container scheduler: runs the pipeline daily at PIPELINE_TIME (HH:MM, IST).
Keeps the whole stack self-contained — no host cron needed.

Time is pinned to Asia/Kolkata via zoneinfo (tzdata ships in requirements) so
the schedule is IST regardless of the container's system timezone (UTC on Railway).
"""
import os, time, datetime
from zoneinfo import ZoneInfo
import pipeline

RUN_AT = os.getenv("PIPELINE_TIME", "07:00")
TZ = ZoneInfo(os.getenv("APP_TZ", "Asia/Kolkata"))

def main():
    print(f"[scheduler] daily pipeline at {RUN_AT} {TZ.key}")
    last_run_day = None
    while True:
        now = datetime.datetime.now(TZ)
        if now.strftime("%H:%M") >= RUN_AT and last_run_day != now.date():
            try:
                pipeline.run()
            except Exception as exc:
                print(f"[scheduler] pipeline failed: {exc}")
            last_run_day = now.date()
        time.sleep(60)

if __name__ == "__main__":
    main()
