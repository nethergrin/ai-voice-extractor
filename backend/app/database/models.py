from sqlalchemy import Column, String, DateTime, Float, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String(255), nullable=False, index=True)
    mode = Column(String(10), nullable=False)  # "online" or "offline"
    status = Column(String(20), nullable=False, default="active")  # "active", "closed", "processing"
    audio_duration = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "mode": self.mode,
            "status": self.status,
            "audio_duration": self.audio_duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }


class AudioFile(Base):
    __tablename__ = "audio_files"

    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(255), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    duration_seconds = Column(Float, nullable=True)
    storage_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "duration_seconds": self.duration_seconds,
            "storage_path": self.storage_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(255), nullable=False, index=True)
    audio_file_id = Column(String(255), nullable=False)
    text = Column(Text, nullable=False, default="")
    language = Column(String(10), nullable=True)
    segments = Column(Text, nullable=False, default="[]")  # JSON string
    storage_path = Column(String(512), nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending, in_progress, completed, failed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "session_id": self.session_id,
            "text": self.text,
            "language": self.language,
            "segments": json.loads(self.segments) if self.segments else [],
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
