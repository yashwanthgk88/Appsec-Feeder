FROM python:3.12-slim
WORKDIR /app
COPY backend/ ./
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
# API server; run pipeline.py separately via cron/scheduler (see crontab.txt)
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
