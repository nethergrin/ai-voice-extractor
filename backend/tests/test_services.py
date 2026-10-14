import pytest
import tempfile
import json
import os
from pathlib import Path
from datetime import datetime
from app.services.session import SessionService
from app.services.audio import AudioService
from app.database.models import Session, AudioFile, Transcript


class TestSessionService:
    def test_create_session(self, db_session):
        session = SessionService.create_session(
            db_session,
            client_id="client_1",
            mode="online"
        )

        assert session is not None
        assert session.client_id == "client_1"
        assert session.mode == "online"
        assert session.status == "active"
        assert session.id.startswith("client_1_")

    def test_get_session(self, db_session):
        # Create a session first
        created = SessionService.create_session(db_session, "client_1", "online")

        # Retrieve it
        retrieved = SessionService.get_session(db_session, created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.client_id == "client_1"

    def test_get_session_not_found(self, db_session):
        result = SessionService.get_session(db_session, "nonexistent_id")
        assert result is None

    def test_get_sessions_by_client(self, db_session):
        # Create multiple sessions for same client
        session1 = SessionService.create_session(db_session, "client_1", "online")
        session2 = SessionService.create_session(db_session, "client_1", "offline")
        session3 = SessionService.create_session(db_session, "client_2", "online")

        sessions = SessionService.get_sessions_by_client(db_session, "client_1")

        assert len(sessions) == 2
        assert all(s.client_id == "client_1" for s in sessions)
        assert {s.id for s in sessions} == {session1.id, session2.id}

    def test_get_sessions_by_client_empty(self, db_session):
        sessions = SessionService.get_sessions_by_client(db_session, "nonexistent_client")
        assert len(sessions) == 0

    def test_close_session(self, db_session):
        session = SessionService.create_session(db_session, "client_1", "online")
        assert session.status == "active"
        assert session.closed_at is None

        closed = SessionService.close_session(db_session, session.id)

        assert closed is not None
        assert closed.status == "closed"
        assert closed.closed_at is not None

    def test_close_nonexistent_session(self, db_session):
        result = SessionService.close_session(db_session, "nonexistent_id")
        assert result is None

    def test_get_all_sessions(self, db_session):
        session1 = SessionService.create_session(db_session, "client_1", "online")
        session2 = SessionService.create_session(db_session, "client_2", "offline")

        all_sessions = SessionService.get_all_sessions(db_session)

        assert len(all_sessions) == 2
        assert {s.id for s in all_sessions} == {session1.id, session2.id}

    def test_get_all_sessions_empty(self, db_session):
        sessions = SessionService.get_all_sessions(db_session)
        assert len(sessions) == 0

    def test_sessions_ordered_by_created_at_desc(self, db_session):
        # Create sessions and check they're ordered by created_at descending
        session1 = SessionService.create_session(db_session, "client_1", "online")
        session2 = SessionService.create_session(db_session, "client_1", "online")

        sessions = SessionService.get_sessions_by_client(db_session, "client_1")

        assert sessions[0].id == session2.id  # Most recent first
        assert sessions[1].id == session1.id


class TestAudioService:
    def test_save_audio_file(self, db_session, temp_audio_dir, monkeypatch):
        monkeypatch.setattr("app.config.settings.audio_storage_path", temp_audio_dir)

        audio_data = b"fake audio data"
        audio_file = AudioService.save_audio_file(
            db_session,
            session_id="session_123",
            filename="test.webm",
            file_data=audio_data
        )

        assert audio_file is not None
        assert audio_file.session_id == "session_123"
        assert audio_file.filename == "test.webm"
        assert audio_file.size_bytes == len(audio_data)
        assert os.path.exists(audio_file.storage_path)

    def test_save_audio_file_creates_directory(self, db_session, temp_audio_dir, monkeypatch):
        monkeypatch.setattr("app.config.settings.audio_storage_path", temp_audio_dir)

        audio_data = b"test data"
        session_id = "session_123"

        AudioService.save_audio_file(db_session, session_id, "test.webm", audio_data)

        expected_dir = Path(temp_audio_dir) / session_id
        assert expected_dir.exists()
        assert expected_dir.is_dir()

    def test_get_audio_files_by_session(self, db_session, temp_audio_dir, monkeypatch):
        monkeypatch.setattr("app.config.settings.audio_storage_path", temp_audio_dir)

        session_id = "session_123"
        file1 = AudioService.save_audio_file(db_session, session_id, "file1.webm", b"data1")
        file2 = AudioService.save_audio_file(db_session, session_id, "file2.webm", b"data2")
        AudioService.save_audio_file(db_session, "other_session", "file3.webm", b"data3")

        files = AudioService.get_audio_files_by_session(db_session, session_id)

        assert len(files) == 2
        assert {f.id for f in files} == {file1.id, file2.id}

    def test_delete_audio_file(self, temp_audio_dir):
        # Create a temp file
        test_file = Path(temp_audio_dir) / "test_audio.webm"
        test_file.write_bytes(b"test data")
        assert test_file.exists()

        # Delete it
        AudioService.delete_audio_file(str(test_file))

        assert not test_file.exists()

    def test_delete_audio_file_not_found(self):
        # Should not raise an error
        AudioService.delete_audio_file("/nonexistent/path/file.webm")

    def test_save_transcript(self, temp_audio_dir, monkeypatch):
        monkeypatch.setattr("app.config.settings.audio_storage_path", temp_audio_dir)

        transcript_data = {
            "text": "Hello world",
            "language": "en",
            "segments": [{"start": 0, "end": 1, "text": "Hello"}]
        }

        path = AudioService.save_transcript(
            session_id="session_123",
            audio_filename="audio.webm",
            transcript_data=transcript_data
        )

        assert os.path.exists(path)
        with open(path, 'r') as f:
            saved = json.load(f)

        assert saved["text"] == "Hello world"
        assert saved["language"] == "en"
        assert saved["audio_file"] == "audio.webm"
        assert "timestamp" in saved

    def test_accumulate_chunk(self):
        AudioService.accumulate_chunk("session_123", b"chunk1")
        AudioService.accumulate_chunk("session_123", b"chunk2")

        accumulated = AudioService.get_accumulated_audio("session_123")
        assert accumulated == b"chunk1chunk2"

    def test_get_accumulated_audio_clears_buffer(self):
        AudioService.accumulate_chunk("session_123", b"chunk1")
        AudioService.get_accumulated_audio("session_123")

        # Second call should return empty
        accumulated = AudioService.get_accumulated_audio("session_123")
        assert accumulated == b""

    def test_get_accumulated_audio_empty_session(self):
        accumulated = AudioService.get_accumulated_audio("nonexistent_session")
        assert accumulated == b""

    def test_save_partial_transcript(self, temp_audio_dir, monkeypatch):
        monkeypatch.setattr("app.config.settings.audio_storage_path", temp_audio_dir)

        transcript_data = {
            "text": "Hello",
            "language": "en",
            "segments": [],
            "status": "in_progress"
        }

        path = AudioService.save_partial_transcript(
            session_id="session_123",
            audio_filename="audio.webm",
            transcript_data=transcript_data
        )

        assert os.path.exists(path)
        with open(path, 'r') as f:
            saved = json.load(f)

        assert saved["status"] == "in_progress"
        assert saved["text"] == "Hello"
