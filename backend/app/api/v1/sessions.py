from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.session import SessionService
from app.services.audio import AudioService
from app.services.transcription import TranscriptionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionCreateRequest(BaseModel):
    client_id: str
    mode: str  # "online" or "offline"


class SessionResponse(BaseModel):
    id: str
    client_id: str
    mode: str
    status: str
    audio_duration: float | None
    created_at: str
    closed_at: str | None


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]


@router.post("/", response_model=SessionResponse)
def create_session(request: SessionCreateRequest, db: Session = Depends(get_db)):
    if request.mode not in ["online", "offline"]:
        raise HTTPException(status_code=400, detail="Mode must be 'online' or 'offline'")

    session = SessionService.create_session(db, request.client_id, request.mode)
    print(f"[SESSION] Created new session: {session.id}, mode: {session.mode}, client: {request.client_id}")
    return session.to_dict()


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@router.get("/", response_model=SessionListResponse)
def get_all_sessions(db: Session = Depends(get_db)):
    sessions = SessionService.get_all_sessions(db)
    return {"sessions": [s.to_dict() for s in sessions]}


@router.post("/{session_id}/close", response_model=SessionResponse)
async def close_session(session_id: str, db: Session = Depends(get_db)):
    from app.config import settings

    session = SessionService.close_session(db, session_id)
    if not session:
        print(f"[SESSION] Failed to close session: {session_id} not found")
        raise HTTPException(status_code=404, detail="Session not found")
    print(f"[SESSION] Closed session: {session_id}")

    # Auto-transcribe only in batch mode (stream mode transcribes during recording)
    if settings.transcript_mode == "batch":
        try:
            audio_files = AudioService.get_audio_files_by_session(db, session_id)
            if audio_files:
                audio_file = audio_files[0]
                print(f"[SESSION] Auto-transcribing audio for session {session_id}...")

                result = await TranscriptionService.transcribe_audio(
                    file_path=audio_file.storage_path,
                    language=None,
                    model=settings.whisper_model,
                )

                AudioService.save_transcript(
                    session_id=session_id,
                    audio_filename=audio_file.filename,
                    transcript_data=result,
                )

                print(f"[SESSION] Auto-transcription complete for session {session_id}")
            else:
                print(f"[SESSION] No audio files found for session {session_id}, skipping transcription")

        except Exception as e:
            print(f"[SESSION] Auto-transcription failed for session {session_id}: {e}")
    else:
        print(f"[SESSION] Stream mode detected, skipping auto-transcription on close (transcribed during recording)")

    return session.to_dict()
