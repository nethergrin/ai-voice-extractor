# AI Voice Extractor

A multi-platform system for recording, streaming, and transcribing audio using Whisper.

## Project Structure

```
├── backend/                    # Python FastAPI backend (port 8000)
├── clients/
│   ├── web/                    # React web frontend (port 3000)
│   └── android/                # Android client (planned)
└── services/
    ├── whisper-worker/         # Whisper transcription service (port 8001)
    └── diarization-worker/     # Speaker diarization service (port 8002, optional)
```

## Quick Start

### Docker Compose (Recommended)

```bash
# Production
docker-compose up --build

# Development (hot reload)
docker-compose -f docker-compose.dev.yml up --build
```

Services:
- Backend: `http://localhost:8000`
- Web Client: `http://localhost:3000`
- API Docs: `http://localhost:8000/docs`

### Local Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Whisper Worker:**
```bash
cd services/whisper-worker
pip install -r requirements.txt
python app.py  # runs on port 8001
```

**Web Client:**
```bash
cd clients/web
npm install
npm start
```

## Current Status

### Done
- ✅ Session management (create, list, close, online/offline modes)
- ✅ Whisper transcription (via dedicated worker service)
- ✅ Streaming audio — client sends PCM chunks every 5s, transcript updates via SSE
- ✅ Batch audio — upload full recording, transcribe on session close
- ✅ Offline recording with localStorage + sync when back online
- ✅ Speaker diarization (optional, fails gracefully if worker unavailable)
- ✅ GPU auto-detection: CUDA → Apple MPS → CPU

### In Progress / Partial
- ⚠️ Streaming transcription works but is best-effort (partial segments, not word-level)
- ⚠️ Transcript persistence is JSON files (no database yet)

### Planned
- ❌ Workflow/extraction engine
- ❌ Admin config UI
- ❌ Android client

## API

### Sessions
```
POST   /api/v1/sessions/                      Create session
GET    /api/v1/sessions/                      List sessions
GET    /api/v1/sessions/{id}                  Get session
POST   /api/v1/sessions/{id}/close            Close session
```

### Audio
```
POST   /api/v1/sessions/{id}/audio            Upload audio chunk or full file
                                              ?is_final=true|false
                                              ?mode=stream|batch
```

### Transcriptions
```
GET    /api/v1/sessions/{id}/transcript        Get stored transcript (JSON)
GET    /api/v1/sessions/{id}/transcript/stream Live updates via SSE
POST   /api/v1/sessions/{id}/transcribe        Trigger manual transcription
```

## Whisper Worker

Runs as a standalone FastAPI service. Model is configurable via `WHISPER_MODEL` env var (default: `base`). Accepts `webm`, `mp4`, `m4a`, `wav` audio files.

```bash
WHISPER_MODEL=small python app.py
```

## Development

Backend and frontend both support hot reload. See `WHISPER_SETUP.md` for GPU/model setup and `DOCKER.md` for container details.
