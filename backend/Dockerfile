FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# So the container is self-checking even outside docker-compose (e.g. a
# bare `docker run`, or a platform that reads the Dockerfile HEALTHCHECK
# directly). docker-compose.yml also defines a healthcheck for the `api`
# service, which takes precedence when running via Compose.
HEALTHCHECK --interval=5s --timeout=5s --start-period=20s --retries=10 \
    CMD curl -sf http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
