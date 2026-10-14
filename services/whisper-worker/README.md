# Whisper Transcription Service

Standalone FastAPI service for Whisper audio transcription with GPU support.

## Features

- **GPU Support**: CUDA, Apple Metal (MPS), CPU fallback
- **Multiple Models**: tiny, base, small, medium, large
- **Language Detection**: Auto-detects or specify language
- **RESTful API**: Simple POST endpoint for transcription

## Setup

### Local Development (with Apple GPU)

```bash
cd services/whisper-worker

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python app.py
```

The app will auto-detect and use Apple Metal (MPS) if available.

### Docker (CPU)

For Apple/Mac, Docker runs in a VM and cannot access GPU. Use local development instead.

```bash
docker build -t whisper-worker .
docker run -p 8001:8001 whisper-worker
```

### Docker (Linux with NVIDIA GPU)

```bash
docker build -t whisper-worker .
docker run --gpus all -p 8001:8001 whisper-worker
```

## Configuration

Set via environment variables:

- `WHISPER_MODEL`: Model size (default: `base`)
  - Options: `tiny`, `base`, `small`, `medium`, `large`
  - Larger = slower but more accurate

Example:
```bash
WHISPER_MODEL=small python app.py
```

## API

### Health Check

```bash
curl http://localhost:8001/health
```

Response:
```json
{
  "status": "ok",
  "device": "mps",
  "model": "base",
  "model_loaded": true
}
```

### Transcribe

```bash
curl -X POST http://localhost:8001/transcribe \
  -F "file=@audio.wav" \
  -F "language=en"
```

Parameters:
- `file`: Audio file (required)
- `model`: Model size (optional, defaults to env var)
- `language`: Language code (optional, auto-detect if not specified)

Response:
```json
{
  "text": "Hello world",
  "language": "en",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 1.5,
      "text": "Hello world"
    }
  ]
}
```

## Performance

On Apple M1/M2/M3:

| Model  | Time (seconds) | Memory (GB) |
|--------|----------------|-------------|
| tiny   | 0.5-1          | 1           |
| base   | 1-2            | 2           |
| small  | 3-5            | 2.5         |
| medium | 8-12           | 5           |
| large  | 15-25          | 10          |

CPU performance is much slower (10-100x).

## Troubleshooting

### Model Download Issues

Whisper downloads models on first use to `~/.cache/whisper/`. Ensure you have:
- Internet connection
- ~3GB disk space (for large model)
- Write permission to home directory

### Memory Issues

Use smaller models (tiny, base) for memory-constrained environments.

### Slow on CPU

If not using GPU, consider:
1. Running on a machine with GPU
2. Using smaller model (tiny)
3. Increasing timeout in caller service
