# Whisper Transcription Service Setup

This guide explains how to set up and run the Whisper transcription service, especially with Apple GPU support.

## Architecture

```
Frontend (React)
    ↓
Backend API (FastAPI) 
    ↓
Whisper Worker Service (separate process)
```

The Whisper service is decoupled from the main API, allowing independent scaling and GPU utilization.

## Local Setup (Recommended for Mac with Apple GPU)

For Mac with Apple GPU (M1/M2/M3), run the Whisper service **natively** (not in Docker) to access Metal acceleration.

### 1. Start Backend & Web with Docker

```bash
# From project root
docker-compose -f docker-compose.dev.yml up --build backend web
```

This starts:
- Backend API at `http://localhost:8000`
- Web client at `http://localhost:3000`

### 2. Run Whisper Service Locally (with Apple GPU)

In a separate terminal:

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

The service will:
- Auto-detect Apple Metal (MPS) GPU
- Start at `http://localhost:8001`

**Verify it's using GPU:**
```bash
curl http://localhost:8001/health
```

Response should show:
```json
{
  "status": "ok",
  "device": "mps",
  "model": "base",
  "model_loaded": true
}
```

## Docker Setup (Linux with NVIDIA GPU)

For Linux with NVIDIA GPU:

```bash
# Make sure NVIDIA Container Runtime is installed
docker-compose up --build
```

Docker will automatically:
- Pass GPU to Whisper service (--gpus all)
- Start all services (backend, web, whisper-worker)

## Configuration

### Model Size

Change the Whisper model by setting environment variable:

```bash
# Local
WHISPER_MODEL=small python app.py

# Docker
WHISPER_MODEL=small docker-compose up whisper-worker
```

Model options: `tiny`, `base` (default), `small`, `medium`, `large`

**Note:** Larger models are more accurate but slower and require more memory.

## Testing

### Test Whisper Service

```bash
# Check health
curl http://localhost:8001/health

# Test transcription
curl -X POST http://localhost:8001/transcribe \
  -F "file=@test_audio.wav" \
  -F "language=en"
```

### Test via Backend API

```bash
# After uploading audio to a session (session_id from earlier)
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/transcribe \
  -H "Content-Type: application/json" \
  -d '{"language": "en", "model": "base"}'
```

## Performance Benchmarks

### Apple M1/M2/M3 (with Metal GPU)

| Model  | Time | Memory |
|--------|------|--------|
| tiny   | 0.5s | 1GB    |
| base   | 1-2s | 2GB    |
| small  | 3-5s | 2.5GB  |

### CPU-only

Expect **10-100x slower** than GPU. Not recommended for production.

## Troubleshooting

### "Model not loaded" error

The model wasn't downloaded on startup. This happens on first run.

**Solution:** The service will download it automatically. Give it 5-10 minutes depending on model size and internet speed.

Check logs:
```bash
# Terminal where Whisper service is running
# You should see download progress
```

### "Failed to connect to Whisper service"

Backend can't reach the Whisper service. 

**Local setup:** Make sure you ran `python app.py` in the whisper-worker directory.

**Docker setup:** Make sure `docker-compose up` includes the `whisper-worker` service.

**Check:** `curl http://localhost:8001/health` should work.

### Out of memory

Reduce model size:
```bash
WHISPER_MODEL=tiny python app.py
```

## Integration with Backend

The backend automatically calls the Whisper service when you POST to `/sessions/{session_id}/transcribe`.

### API Endpoint

```
POST /api/v1/sessions/{session_id}/transcribe
Content-Type: application/json

{
  "language": "en",
  "model": "base"
}
```

### Response

```json
{
  "session_id": "web-client-v1_abc123",
  "text": "The transcribed text...",
  "language": "en",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 2.5,
      "text": "The transcribed text..."
    }
  ]
}
```

## Next Steps

1. Add transcription trigger to audio upload (auto-transcribe when audio finishes)
2. Store transcription results in database
3. Integrate into workflow system
4. Add language auto-detection UI option
5. Support multiple transcription services (Claude API, etc.)

## Advanced

### Using CPU-only in Docker

If GPU is not available:

```bash
docker-compose up whisper-worker
# Will use CPU automatically
```

### Custom Model Selection

Set via environment on startup:

**Local:**
```bash
WHISPER_MODEL=medium python app.py
```

**Docker:**
```yaml
# In docker-compose.yml
whisper-worker:
  environment:
    - WHISPER_MODEL=medium
```

### Monitoring

Check Whisper service health:
```bash
watch -n 1 'curl -s http://localhost:8001/health | jq'
```

### Logs

**Local:**
Look at the terminal where `python app.py` is running.

**Docker:**
```bash
docker-compose logs -f whisper-worker
```
