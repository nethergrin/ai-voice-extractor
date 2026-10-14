import pytest
import json
from datetime import datetime
from app.database.models import Session, AudioFile, Transcript


class TestSessionModel:
    def test_session_creation(self):
        session = Session(
            id="test_session_123",
            client_id="client_1",
            mode="online",
            status="active"
        )
        assert session.id == "test_session_123"
        assert session.client_id == "client_1"
        assert session.mode == "online"
        assert session.status == "active"

    def test_session_to_dict(self):
        now = datetime.utcnow()
        session = Session(
            id="test_session_123",
            client_id="client_1",
            mode="online",
            status="active",
            audio_duration=10.5,
            created_at=now,
            closed_at=None
        )
        result = session.to_dict()

        assert result["id"] == "test_session_123"
        assert result["client_id"] == "client_1"
        assert result["mode"] == "online"
        assert result["status"] == "active"
        assert result["audio_duration"] == 10.5
        assert result["created_at"] == now.isoformat()
        assert result["closed_at"] is None

    def test_session_to_dict_with_closed_time(self):
        now = datetime.utcnow()
        closed_time = datetime.utcnow()
        session = Session(
            id="test_session_123",
            client_id="client_1",
            mode="offline",
            status="closed",
            closed_at=closed_time,
            created_at=now
        )
        result = session.to_dict()

        assert result["status"] == "closed"
        assert result["closed_at"] == closed_time.isoformat()


class TestAudioFileModel:
    def test_audio_file_creation(self):
        audio_file = AudioFile(
            id="audio_123",
            session_id="session_123",
            filename="test.webm",
            size_bytes=5000,
            duration_seconds=10.5,
            storage_path="/path/to/audio.webm"
        )
        assert audio_file.id == "audio_123"
        assert audio_file.session_id == "session_123"
        assert audio_file.filename == "test.webm"
        assert audio_file.size_bytes == 5000
        assert audio_file.duration_seconds == 10.5

    def test_audio_file_to_dict(self):
        now = datetime.utcnow()
        audio_file = AudioFile(
            id="audio_123",
            session_id="session_123",
            filename="test.webm",
            size_bytes=5000,
            duration_seconds=10.5,
            storage_path="/path/to/audio.webm",
            created_at=now
        )
        result = audio_file.to_dict()

        assert result["id"] == "audio_123"
        assert result["session_id"] == "session_123"
        assert result["filename"] == "test.webm"
        assert result["size_bytes"] == 5000
        assert result["duration_seconds"] == 10.5
        assert result["storage_path"] == "/path/to/audio.webm"
        assert result["created_at"] == now.isoformat()


class TestTranscriptModel:
    def test_transcript_creation(self):
        transcript = Transcript(
            id="transcript_123",
            session_id="session_123",
            audio_file_id="audio_123",
            text="Hello world",
            language="en",
            status="completed"
        )
        assert transcript.id == "transcript_123"
        assert transcript.session_id == "session_123"
        assert transcript.text == "Hello world"
        assert transcript.language == "en"
        assert transcript.status == "completed"

    def test_transcript_to_dict(self):
        now = datetime.utcnow()
        segments = [
            {"start": 0.0, "end": 1.5, "text": "Hello"},
            {"start": 1.5, "end": 3.0, "text": "world"}
        ]
        transcript = Transcript(
            id="transcript_123",
            session_id="session_123",
            audio_file_id="audio_123",
            text="Hello world",
            language="en",
            segments=json.dumps(segments),
            status="completed",
            created_at=now,
            updated_at=now
        )
        result = transcript.to_dict()

        assert result["id"] == "transcript_123"
        assert result["session_id"] == "session_123"
        assert result["text"] == "Hello world"
        assert result["language"] == "en"
        assert result["status"] == "completed"
        assert result["segments"] == segments
        assert result["created_at"] == now.isoformat()

    def test_transcript_to_dict_empty_segments(self):
        transcript = Transcript(
            id="transcript_123",
            session_id="session_123",
            audio_file_id="audio_123",
            text="",
            status="pending"
        )
        result = transcript.to_dict()

        assert result["segments"] == []

    def test_transcript_default_status(self):
        transcript = Transcript(
            id="transcript_123",
            session_id="session_123",
            audio_file_id="audio_123",
            text=""
        )
        assert transcript.status == "pending"
