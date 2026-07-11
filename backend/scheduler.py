"""In-container scheduler: runs the pipeline daily at PIPELINE_TIME (HH:MM, server tz).
Keeps the whole stack self-contained — no host cron needed."""
import os, time, datetime
import pipeline

RUN_AT = os.getenv("PIPELINE_TIME", "07:00")

def main():
    print(f"[scheduler] daily pipeline at {RUN_AT}")
    last_run_day = None
    while True:
        now = datetime.datetime.now()
        if now.strftime("%H:%M") >= RUN_AT and last_run_day != now.date():
            try:
                pipeline.run()
            except Exception as exc:
                print(f"[scheduler] pipeline failed: {exc}")
            last_run_day = now.date()
        time.sleep(60)

if __name__ == "__main__":
    main()
