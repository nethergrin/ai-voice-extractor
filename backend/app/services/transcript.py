from sqlalchemy.orm import Session
from app.database.models import Transcript
from datetime import datetime
import json


class TranscriptService:
    @staticmethod
    def create_transcript(db: Session, session_id: str, audio_file_id: str) -> Transcript:
        """Create a new transcript record."""
        transcript = Transcript(
            session_id=session_id,
            audio_file_id=audio_file_id,
            status="pending"
        )
        db.add(transcript)
        db.commit()
        db.refresh(transcript)
        return transcript

    @staticmethod
    def get_transcript(db: Session, session_id: str) -> Transcript:
        """Get transcript for a session."""
        return db.query(Transcript).filter(Transcript.session_id == session_id).first()

    @staticmethod
    def update_transcript(db: Session, session_id: str, text: str, language: str, segments: list, status: str = "completed"):
        """Update transcript with results."""
        transcript = db.query(Transcript).filter(Transcript.session_id == session_id).first()
        if transcript:
            transcript.text = text
            transcript.language = language
            transcript.segments = json.dumps(segments)
            transcript.status = status
            transcript.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(transcript)
        return transcript

    @staticmethod
    def update_transcript_status(db: Session, session_id: str, status: str):
        """Update transcript status (for streaming mode)."""
        transcript = db.query(Transcript).filter(Transcript.session_id == session_id).first()
        if transcript:
            transcript.status = status
            transcript.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(transcript)
        return transcript

    @staticmethod
    def update_transcript_text(db: Session, session_id: str, text: str, segments: list = None):
        """Update transcript text (for streaming mode)."""
        transcript = db.query(Transcript).filter(Transcript.session_id == session_id).first()
        if transcript:
            transcript.text = text
            if segments:
                transcript.segments = json.dumps(segments)
            transcript.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(transcript)
        return transcript
