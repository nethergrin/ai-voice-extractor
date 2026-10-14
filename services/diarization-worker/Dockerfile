FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ARG HF_TOKEN
ENV HF_TOKEN=$HF_TOKEN

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8002/health')"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]
