FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app

RUN mkdir -p /app/var/images && useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Pre-bake the ChromaDB default embedding model (MiniLM-L6-v2, ~79 MB).
# Without this, the FIRST ChromaDB query in production (DEMO_MODE=false)
# triggers a multi-minute download inside the container and stalls the
# pipeline past its 30s timeout. Building it into the image makes review
# retrieval instant on every fresh container.
RUN python -c "from chromadb.utils import embedding_functions; embedding_functions.DefaultEmbeddingFunction()"

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
