from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.session import SessionService
from app.services.audio import AudioService
from app.services.transcription import TranscriptionService
from app.utils.audio_utils import pcm_to_wav
from app.config import settings
import json
import asyncio
import os

router = APIRouter(prefix="/sessions", tags=["transcriptions"])


class TranscriptionRequest(BaseModel):
    language: str = None
    model: str = "base"


class TranscriptionSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    speaker: str | None = None


class TranscriptionResponse(BaseModel):
    session_id: str
    text: str
    language: str
    segments: list[TranscriptionSegment]


@router.get("/{session_id}/transcript", response_model=TranscriptionResponse)
def get_transcript(session_id: str, db: Session = Depends(get_db)):
    """Get transcript for a session from filesystem."""
    print(f"[API] Getting transcript for session: {session_id}")

    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get audio files to find transcript
    audio_files = AudioService.get_audio_files_by_session(db, session_id)
    if not audio_files:
        raise HTTPException(status_code=404, detail="No audio files found")

    # Look for transcript file next to audio
    from pathlib import Path
    audio_file = audio_files[0]
    audio_path = Path(audio_file.storage_path)
    transcript_path = audio_path.parent / f"{audio_path.stem}.transcript.json"

    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript not found")

    # Read transcript from file
    import json as json_lib
    with open(transcript_path, "r") as f:
        transcript_data = json_lib.load(f)

    return {
        "session_id": session_id,
        "text": transcript_data.get("text", ""),
        "language": transcript_data.get("language", "unknown"),
        "segments": transcript_data.get("segments", []),
    }


@router.get("/{session_id}/transcript/stream")
async def stream_transcript(session_id: str, db: Session = Depends(get_db)):
    """SSE endpoint for streaming transcript updates."""
    print(f"[API] Streaming transcript for session: {session_id}")

    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def generate():
        """Generate SSE events for transcript updates."""
        import json as json_lib
        from pathlib import Path
        import tempfile

        audio_files = AudioService.get_audio_files_by_session(db, session_id)
        audio_filename = audio_files[0].filename if audio_files else "audio.webm"
        last_text = ""
        max_polls = 300  # 5 minutes at 1 poll per second
        poll_count = 0

        print(f"[SSE] Starting stream for session {session_id}, transcript_mode: {settings.transcript_mode}")

        for poll_num in range(max_polls):
            poll_count += 1
            try:
                storage_path = Path(settings.audio_storage_path) / session_id
                transcript_path = storage_path / f"{Path(audio_filename).stem}.transcript.json"

                # Always check for new accumulated chunks in stream mode
                if settings.transcript_mode == "stream":
                    accumulated = AudioService.get_accumulated_audio(session_id)
                    if accumulated:
                        print(f"[SSE] Poll {poll_count}: Found {len(accumulated)} accumulated bytes, transcribing...")
                        try:
                            # Get audio format and convert PCM to WAV
                            audio_format = AudioService.get_audio_format(session_id)
                            if audio_format:
                                wav_data = pcm_to_wav(
                                    accumulated,
                                    audio_format["sample_rate"],
                                    audio_format["channels"],
                                    audio_format["bit_depth"]
                                )
                                print(f"[SSE] Poll {poll_count}: Converted PCM to WAV ({len(wav_data)} bytes)")
                            else:
                                wav_data = accumulated
                                print(f"[SSE] Poll {poll_count}: No audio format found, using raw data")

                            # Write to temp WAV file for transcription
                            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                                tmp.write(wav_data)
                                tmp_path = tmp.name

                            result = await TranscriptionService.transcribe_and_diarize(
                                file_path=tmp_path,
                                language=None,
                                model=settings.whisper_model,
                            )
                            result["status"] = "in_progress"

                            # Save partial transcript
                            AudioService.save_partial_transcript(
                                session_id=session_id,
                                audio_filename=audio_filename,
                                transcript_data=result,
                            )

                            current_text = result.get("text", "")
                            if current_text != last_text:
                                last_text = current_text
                                print(f"[SSE] Poll {poll_count}: Sending new transcript ({len(current_text)} chars)")
                                yield f"data: {json_lib.dumps(result)}\n\n"

                            # Cleanup
                            os.unlink(tmp_path)
                        except Exception as e:
                            print(f"[API] Error transcribing stream: {e}")
                            yield f"data: {json_lib.dumps({'error': str(e)})}\n\n"

                # Check existing transcript file for completion status
                if transcript_path.exists():
                    with open(transcript_path, "r") as f:
                        transcript_data = json_lib.load(f)

                    current_text = transcript_data.get("text", "")
                    if current_text != last_text:
                        last_text = current_text
                        print(f"[SSE] Poll {poll_count}: Sending transcript update ({len(current_text)} chars, status: {transcript_data.get('status')})")
                        yield f"data: {json_lib.dumps(transcript_data)}\n\n"

                    # Stop if completed
                    if transcript_data.get("status") == "completed":
                        print(f"[SSE] Poll {poll_count}: Transcript completed, closing stream")
                        break

                # Check if session is closed
                updated_session = SessionService.get_session(db, session_id)
                if updated_session and updated_session.status == "closed":
                    print(f"[SSE] Poll {poll_count}: Session closed, finalizing transcript stream")
                    # Wait a bit for final transcript if not already present
                    if not transcript_path.exists() and poll_num > 10:
                        print(f"[SSE] Poll {poll_count}: No transcript found after session closed, breaking")
                        break
                    elif transcript_path.exists():
                        with open(transcript_path, "r") as f:
                            final_data = json_lib.load(f)
                            final_data["status"] = "completed"
                            print(f"[SSE] Poll {poll_count}: Sending final transcript ({len(final_data.get('text', ''))} chars)")
                            yield f"data: {json_lib.dumps(final_data)}\n\n"
                        break
                else:
                    if poll_count % 10 == 0:
                        print(f"[SSE] Poll {poll_count}: Waiting for updates... (session still active)")

                await asyncio.sleep(1)

            except Exception as e:
                print(f"[API] Error streaming transcript: {e}")
                yield f"data: {json_lib.dumps({'error': str(e)})}\n\n"
                break

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/{session_id}/transcribe", response_model=TranscriptionResponse)
async def transcribe_session(
    session_id: str,
    request: TranscriptionRequest,
    db: Session = Depends(get_db)
):
    """Manually transcribe audio for a session."""
    print(f"[API] Transcription requested for session: {session_id}")

    session = SessionService.get_session(db, session_id)
    if not session:
        print(f"[API] Session {session_id} not found")
        raise HTTPException(status_code=404, detail="Session not found")

    # Get all audio files for this session
    audio_files = AudioService.get_audio_files_by_session(db, session_id)
    if not audio_files:
        print(f"[API] No audio files found for session {session_id}")
        raise HTTPException(status_code=404, detail="No audio files found for this session")

    # For now, transcribe the first (usually only) audio file
    audio_file = audio_files[0]
    print(f"[API] Transcribing audio file: {audio_file.filename}")

    try:
        result = await TranscriptionService.transcribe_and_diarize(
            file_path=audio_file.storage_path,
            language=request.language,
            model=request.model,
        )

        print(f"[API] Transcription successful for session {session_id}")
        return {
            "session_id": session_id,
            "text": result["text"],
            "language": result["language"],
            "segments": result["segments"],
        }

    except Exception as e:
        print(f"[API] Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
