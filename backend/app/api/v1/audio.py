from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.session import SessionService
from app.services.audio import AudioService
from app.services.transcription import TranscriptionService
from app.config import settings
from app.utils.audio_utils import pcm_to_wav
from datetime import datetime

router = APIRouter(prefix="/sessions", tags=["audio"])


class AudioUploadResponse(BaseModel):
    file_id: str
    session_id: str
    filename: str
    size_bytes: int
    received_at: str


@router.post("/{session_id}/audio", response_model=AudioUploadResponse)
async def upload_audio(
    session_id: str,
    file: UploadFile = File(...),
    client_id: str = Query(None),
    mode: str = Query("online"),
    is_final: bool = Query(False),
    sample_rate: int = Query(None),
    channels: int = Query(None),
    bit_depth: int = Query(None),
    db: Session = Depends(get_db)
):
    print(f"[AUDIO] Received upload request for session: {session_id}, filename: {file.filename}, content_type: {file.content_type}, is_final: {is_final}")

    session = SessionService.get_session(db, session_id)
    if not session:
        if client_id:
            print(f"[AUDIO] Session {session_id} not found. Creating new session with client_id: {client_id}, mode: {mode}")
            session = SessionService.create_session(db, client_id, mode)
            print(f"[AUDIO] Auto-created session: {session_id}")
        else:
            print(f"[AUDIO] Session {session_id} not found and no client_id provided")
            raise HTTPException(status_code=404, detail="Session not found")

    print(f"[AUDIO] Session {session_id} status: {session.status}")

    file_data = await file.read()
    print(f"[AUDIO] Read {len(file_data)} bytes from file")
    print(f"[AUDIO] Format params received: sample_rate={sample_rate}, channels={channels}, bit_depth={bit_depth}")

    # Store audio format metadata for PCM reconstruction
    if sample_rate and channels and bit_depth:
        AudioService.store_audio_format(session_id, sample_rate, channels, bit_depth)
        print(f"[AUDIO] Stored format: {sample_rate}Hz, {channels}ch, {bit_depth}bit")
    else:
        print(f"[AUDIO] Format params incomplete or missing")

    # In stream mode with active session, accumulate chunks
    if settings.transcript_mode == "stream" and session.status == "active" and not is_final:
        print(f"[AUDIO] Stream mode: accumulating {len(file_data)} bytes chunk for session {session_id}")
        AudioService.accumulate_chunk(session_id, file_data)
        print(f"[AUDIO] Chunk accumulated successfully for {session_id}")
        return {
            "file_id": f"chunk_{session_id}",
            "session_id": session_id,
            "filename": file.filename,
            "size_bytes": len(file_data),
            "received_at": datetime.utcnow().isoformat()
        }

    # Final chunk or batch mode: save complete file
    # In stream mode with final chunk, combine accumulated chunks with final chunk
    if settings.transcript_mode == "stream" and is_final:
        accumulated = AudioService.get_accumulated_audio(session_id)
        if accumulated:
            print(f"[AUDIO] Combining {len(accumulated)} bytes accumulated + {len(file_data)} bytes final for {session_id}")
            file_data = accumulated + file_data

    # If PCM data, convert to WAV using stored format
    if file.filename.endswith(".pcm") or file.content_type == "application/octet-stream":
        audio_format = AudioService.get_audio_format(session_id)
        print(f"[AUDIO] PCM file detected. Format from session: {audio_format}")
        if audio_format:
            sample_rate = audio_format["sample_rate"]
            channels = audio_format["channels"]
            bit_depth = audio_format["bit_depth"]
            print(f"[AUDIO] Converting PCM to WAV: {len(file_data)} bytes → ({sample_rate}Hz, {channels}ch, {bit_depth}bit)")
            file_data = pcm_to_wav(file_data, sample_rate, channels, bit_depth)
            print(f"[AUDIO] WAV file created: {len(file_data)} bytes")
            filename = "audio.wav"
        else:
            print(f"[AUDIO] Warning: PCM data but no format metadata for {session_id}")
            filename = file.filename
    else:
        filename = file.filename

    audio_file = AudioService.save_audio_file(db, session_id, filename, file_data)
    print(f"[AUDIO] Audio file saved: {audio_file.id}, path: {audio_file.storage_path}")

    # For batch mode or final chunk in stream mode: auto-transcribe immediately
    if settings.transcript_mode == "batch" or is_final:
        print(f"[AUDIO] Transcribing audio for session {session_id}...")
        try:
            result = await TranscriptionService.transcribe_and_diarize(
                file_path=audio_file.storage_path,
                language=None,
                model=settings.whisper_model,
            )
            AudioService.save_transcript(
                session_id=session_id,
                audio_filename=audio_file.filename,
                transcript_data=result,
            )
            print(f"[AUDIO] Auto-transcription complete for session {session_id}")
        except Exception as e:
            print(f"[AUDIO] Auto-transcription failed for session {session_id}: {e}")

    return {
        "file_id": audio_file.id,
        "session_id": audio_file.session_id,
        "filename": audio_file.filename,
        "size_bytes": audio_file.size_bytes,
        "received_at": datetime.utcnow().isoformat()
    }
