from sqlalchemy.orm import Session
from app.database.models import AudioFile
from app.config import settings
from pathlib import Path
import os
import json
from datetime import datetime
from tempfile import NamedTemporaryFile


# In-memory storage for streaming audio chunks
_streaming_chunks = {}
# In-memory storage for audio format metadata
_audio_formats = {}


class AudioService:
    @staticmethod
    def save_audio_file(db: Session, session_id: str, filename: str, file_data: bytes) -> AudioFile:
        storage_path = Path(settings.audio_storage_path) / session_id
        storage_path.mkdir(parents=True, exist_ok=True)

        file_path = storage_path / filename
        with open(file_path, 'wb') as f:
            f.write(file_data)

        audio_file = AudioFile(
            session_id=session_id,
            filename=filename,
            size_bytes=len(file_data),
            storage_path=str(file_path)
        )
        db.add(audio_file)
        db.commit()
        db.refresh(audio_file)
        return audio_file

    @staticmethod
    def get_audio_files_by_session(db: Session, session_id: str) -> list[AudioFile]:
        return db.query(AudioFile).filter(AudioFile.session_id == session_id).all()

    @staticmethod
    def delete_audio_file(file_path: str):
        if os.path.exists(file_path):
            os.remove(file_path)

    @staticmethod
    def save_transcript(session_id: str, audio_filename: str, transcript_data: dict) -> str:
        """
        Save transcript as JSON file in the same folder as audio.

        Args:
            session_id: Session ID
            audio_filename: Name of audio file (e.g., "audio.webm")
            transcript_data: Dictionary with transcription result

        Returns:
            Path to saved transcript file
        """
        storage_path = Path(settings.audio_storage_path) / session_id
        storage_path.mkdir(parents=True, exist_ok=True)

        # Create transcript filename from audio filename
        audio_name = Path(audio_filename).stem  # Remove extension
        transcript_filename = f"{audio_name}.transcript.json"
        transcript_path = storage_path / transcript_filename

        # Save transcript with metadata
        transcript_with_metadata = {
            "timestamp": datetime.utcnow().isoformat(),
            "audio_file": audio_filename,
            "text": transcript_data.get("text", ""),
            "language": transcript_data.get("language", ""),
            "segments": transcript_data.get("segments", []),
        }

        with open(transcript_path, "w") as f:
            json.dump(transcript_with_metadata, f, indent=2)

        print(f"[AUDIO] Transcript saved: {transcript_path}")
        return str(transcript_path)

    @staticmethod
    def accumulate_chunk(session_id: str, chunk_data: bytes):
        """Accumulate audio chunk for streaming mode."""
        if session_id not in _streaming_chunks:
            _streaming_chunks[session_id] = []
        _streaming_chunks[session_id].append(chunk_data)
        print(f"[AUDIO] Accumulated chunk for {session_id}, total chunks: {len(_streaming_chunks[session_id])}")

    @staticmethod
    def get_accumulated_audio(session_id: str) -> bytes:
        """Get all accumulated chunks and clear the buffer."""
        if session_id in _streaming_chunks:
            chunks = _streaming_chunks[session_id]
            accumulated = b"".join(chunks)
            del _streaming_chunks[session_id]
            print(f"[AUDIO] Retrieved {len(accumulated)} bytes from {len(chunks)} chunks for {session_id}")
            return accumulated
        return b""

    @staticmethod
    def save_partial_transcript(session_id: str, audio_filename: str, transcript_data: dict) -> str:
        """Save partial transcript during streaming."""
        storage_path = Path(settings.audio_storage_path) / session_id
        storage_path.mkdir(parents=True, exist_ok=True)

        audio_name = Path(audio_filename).stem
        transcript_filename = f"{audio_name}.transcript.json"
        transcript_path = storage_path / transcript_filename

        transcript_with_metadata = {
            "timestamp": datetime.utcnow().isoformat(),
            "audio_file": audio_filename,
            "text": transcript_data.get("text", ""),
            "language": transcript_data.get("language", ""),
            "segments": transcript_data.get("segments", []),
            "status": transcript_data.get("status", "in_progress"),
        }

        with open(transcript_path, "w") as f:
            json.dump(transcript_with_metadata, f, indent=2)

        return str(transcript_path)

    @staticmethod
    def store_audio_format(session_id: str, sample_rate: int, channels: int, bit_depth: int):
        """Store audio format metadata for PCM to WAV conversion."""
        _audio_formats[session_id] = {
            "sample_rate": sample_rate,
            "channels": channels,
            "bit_depth": bit_depth,
        }

    @staticmethod
    def get_audio_format(session_id: str) -> dict:
        """Get stored audio format metadata."""
        return _audio_formats.get(session_id)

    @staticmethod
    def clear_audio_format(session_id: str):
        """Clear audio format metadata after use."""
        if session_id in _audio_formats:
            del _audio_formats[session_id]
