FROM python:3.13-slim

WORKDIR /app

# Install deps first so they cache across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code (see .dockerignore for what's excluded, e.g. .env and data/).
COPY bot ./bot

# SQLite state lives here; mount it as a volume so it survives restarts.
VOLUME ["/app/data"]

CMD ["python", "-m", "bot.main"]
