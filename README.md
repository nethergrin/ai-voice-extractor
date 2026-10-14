# AI Voice Extractor

A multi-platform system for recording, extracting, and processing audio using transcription services.

## Project Structure

```
├── backend/           # Python FastAPI backend
│   ├── app/
│   │   ├── main.py              # FastAPI application entry
│   │   ├── config.py            # Configuration
│   │   ├── database/            # Database setup
│   │   ├── models/              # Data models
│   │   ├── services/            # Business logic
│   │   └── api/                 # API endpoints
│   ├── requirements.txt
│   └── README.md
│
├── clients/
│   ├── web/          # React web frontend
│   │   ├── src/
│   │   ├── public/
│   │   ├── package.json
│   │   └── README.md
│   │
│   └── android/      # Android native client (to be implemented)
│       └── README.md
│
└── README.md
```

## Quick Start

### Option 1: Docker Compose (Recommended)

**Production Build:**
```bash
docker-compose up --build
```

**Development Build (with hot reload):**
```bash
docker-compose -f docker-compose.dev.yml up --build
```

Services will be available at:
- Backend: `http://localhost:8000`
- Web Client: `http://localhost:3000`
- API Docs: `http://localhost:8000/docs`

### Option 2: Local Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will run at `http://localhost:8000`
API documentation: `http://localhost:8000/docs`

**Web Client:**
```bash
cd clients/web
npm install
npm start
```

Web client will open at `http://localhost:3000`

## Current Implementation

### MVP Phase 1 - Basic Audio Recording & Streaming ✅
- ✅ Session management (create, list, close)
- ✅ Audio upload (batch mode)
- ✅ Web client with session list and recording
- ✅ Microphone selection
- ✅ Online/Offline mode selection
- ❌ Streaming audio chunks (chunked upload)
- ❌ Transcription (Whisper)
- ❌ Workflow execution
- ❌ Android client

### Next Steps
1. Implement streaming audio chunk upload
2. Add Whisper transcription integration
3. Build workflow execution engine
4. Create admin panel for configuration
5. Develop Android client

## API Overview

### Sessions
```
POST   /api/v1/sessions              - Create new session
GET    /api/v1/sessions              - List all sessions
GET    /api/v1/sessions/{id}         - Get session details
POST   /api/v1/sessions/{id}/close   - Close session
```

### Audio
```
POST   /api/v1/sessions/{id}/audio   - Upload audio file
```

## Development

Both backend and frontend use hot reload during development.

For the backend, the server will automatically reload when you change Python files.
For the web client, the browser will refresh when you change React files.
