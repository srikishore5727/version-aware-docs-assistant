# Production image for VADA. Render (and any Docker host) builds this file.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ANONYMIZED_TELEMETRY=False

WORKDIR /app

# Dependencies first so a code change does not reinstall the wheels.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Only what the server reads at runtime. Tests, docs and .env stay out.
COPY app ./app
COPY corpus ./corpus

# The container filesystem is ephemeral on free plans, so the index is written
# here at boot and rebuilt on the next deploy.
RUN mkdir -p data/index data/eval

EXPOSE 8000

# Build the index before serving, so the first question is not stuck behind 60
# embedding calls. A failure is not fatal: app.retriever.ensure_ready() rebuilds
# on the first request, and the app still refuses rather than guessing.
CMD ["sh", "-c", "python -m app.refresh || echo 'index build skipped - will rebuild on first request'; exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
