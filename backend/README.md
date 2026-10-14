# AI Voice Extractor - Backend

Python FastAPI backend for the AI Voice Extractor system.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file from `.env.example`:
```bash
cp .env.example .env
```

4. Run the server:
```bash
bash run.sh
# or
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at `http://localhost:8000`

## API Endpoints

### Sessions
- `POST /api/v1/sessions` - Create a new session
- `GET /api/v1/sessions` - List all sessions
- `GET /api/v1/sessions/{session_id}` - Get session details
- `POST /api/v1/sessions/{session_id}/close` - Close a session

### Audio
- `POST /api/v1/sessions/{session_id}/audio` - Upload audio file

## Database

By default, SQLite is used (file: `app.db`). For production, configure PostgreSQL in `.env`:
```
DATABASE_URL=postgresql://user:password@localhost/dbname
```

## Audio Storage

Audio files are stored in the directory specified by `AUDIO_STORAGE_PATH` (default: `./audio_storage`).
