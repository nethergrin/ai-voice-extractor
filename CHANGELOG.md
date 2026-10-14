# Changelog

## [0.1.0] - 2026-10-05

### MVP Phase 1: Core Audio Recording & Streaming

#### Backend
- ✅ FastAPI server with session management (create, list, close)
- ✅ SQLite database with Session and AudioFile models
- ✅ Audio file upload endpoint supporting both batch and streaming modes
- ✅ CORS enabled for cross-origin requests
- ✅ Health check endpoint
- ✅ Configurable audio storage path

#### Web Client (React)
- ✅ Session list displaying all recordings with timestamps
- ✅ Start/Stop recording UI
- ✅ Microphone selection dropdown (auto-detects available devices)
- ✅ Recording mode selection (Online/Offline)
- ✅ Permission-based microphone access (auto-requests on load)
- ✅ Responsive UI with dark header and session table
- ✅ Empty states and status indicators

#### Offline Support
- ✅ Offline mode: records and stores audio locally in browser (localStorage)
- ✅ Offline mode: stores session metadata (client_id, mode, MIME type)
- ✅ Auto-sync UI showing pending offline recordings
- ✅ Manual "Sync to Server" button to upload pending recordings
- ✅ Automatic cleanup from localStorage after successful upload
- ✅ Auto-session creation if backend session missing (for offline sync)

#### Database & Persistence
- ✅ Named Docker volume for persistent data storage
- ✅ Database survives container restarts
- ✅ Audio files stored in persistent volume

### Whisper Transcription Service

#### Separate Whisper Worker
- ✅ Standalone FastAPI service for transcription
- ✅ GPU support detection (CUDA, Apple Metal/MPS, CPU fallback)
- ✅ Configurable model sizes (tiny, base, small, medium, large)
- ✅ Model auto-download on first use to ~/.cache/whisper/
- ✅ Health check endpoint showing device and model status
- ✅ Language auto-detection and optional language override
- ✅ Docker support with ffmpeg dependency
- ✅ Fast inference on Apple Silicon with Metal acceleration

#### Backend Integration
- ✅ TranscriptionService for communicating with Whisper worker
- ✅ Auto-transcription on session close (batch mode)
- ✅ Transcript saved as JSON file next to audio file
- ✅ Metadata in transcript: timestamp, audio_file, language, segments

#### Frontend Transcript Viewing
- ✅ "View Transcript" button for closed sessions
- ✅ Transcript modal displaying:
  - Full transcribed text
  - Detected language
  - Individual segments with start/end times
  - Clickable segments showing timeline
- ✅ Clean, styled modal with close button
- ✅ SSE-ready for streaming transcript updates (endpoints prepared)

### Configuration & Environment
- ✅ TRANSCRIPT_MODE config (batch/stream - framework ready)
- ✅ WHISPER_MODEL config (default: base)
- ✅ Backend environment variables via .env
- ✅ Docker environment configuration in docker-compose files
- ✅ Apple GPU support for local Whisper service development

### Docker & Deployment
- ✅ Docker Compose for orchestration (production build)
- ✅ Docker Compose dev config with hot reload
- ✅ Multi-stage builds for web client optimization
- ✅ Persistent volumes for data
- ✅ Health checks for all services
- ✅ Internal service networking
- ✅ Support for local Whisper service on Mac (via host.docker.internal)

### Documentation
- ✅ README with quick start guide
- ✅ DOCKER.md with detailed Docker setup
- ✅ WHISPER_SETUP.md with GPU and model configuration
- ✅ Backend README with API documentation
- ✅ Web client README with feature list
- ✅ .env.example with all configuration options

### Known Limitations / Future Work
- ⏳ Streaming transcription mode (endpoints ready, implementation pending)
- ⏳ Diarization (speaker identification)
- ⏳ Workflow/extraction system
- ⏳ Admin panel for configuration
- ⏳ Android client
- ⏳ Database for transcript metadata (currently files only)
- ⏳ Real-time transcript streaming via WebSocket/SSE (framework ready)

### Test Instructions

**Local Setup (Mac with Apple GPU):**
```bash
# Terminal 1: Backend & Web
docker-compose -f docker-compose.dev.yml up backend web

# Terminal 2: Whisper with Metal GPU
cd services/whisper-worker
python app.py
```

**Test Flow:**
1. Record audio (online or offline mode)
2. Stop recording
3. Session auto-transcribes (3-5 seconds for base model)
4. Refresh browser
5. Click "View Transcript" to see results

### Architecture
- Backend: Python FastAPI + SQLite
- Frontend: React 18 + Axios
- Transcription: Separate FastAPI service with Whisper
- Storage: Local filesystem + Docker named volumes
- Communication: REST API + SSE (ready for streaming)

### Performance
- Base model: ~1-2 seconds per minute of audio (M1/M2 with Metal)
- Model size: 139MB
- Recording: Supports any microphone with browser permission
- Offline: Unlimited recordings (limited by browser storage)
