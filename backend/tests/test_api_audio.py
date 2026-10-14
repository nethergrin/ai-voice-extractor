import pytest
from io import BytesIO
from app.services.session import SessionService


class TestAudioEndpoints:
    def test_upload_audio_to_existing_session(self, client, db_session):
        # Create session first
        session = SessionService.create_session(db_session, "client_1", "online")

        # Upload audio
        file_content = b"fake audio data"
        response = client.post(
            f"/api/v1/sessions/{session.id}/audio",
            files={"file": ("test.webm", BytesIO(file_content), "audio/webm")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session.id
        assert data["filename"] == "test.webm"
        assert data["size_bytes"] == len(file_content)
        assert "file_id" in data
        assert "received_at" in data

    def test_upload_audio_creates_session_if_not_exists(self, client, db_session):
        # Upload audio with client_id but no existing session
        file_content = b"fake audio data"
        session_id = "new_session_123"

        response = client.post(
            f"/api/v1/sessions/{session_id}/audio",
            files={"file": ("test.webm", BytesIO(file_content), "audio/webm")},
            params={"client_id": "client_1", "mode": "online"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["size_bytes"] == len(file_content)

    def test_upload_audio_missing_session_no_client_id(self, client):
        # Try to upload without session or client_id
        file_content = b"fake audio data"

        response = client.post(
            "/api/v1/sessions/nonexistent_session/audio",
            files={"file": ("test.webm", BytesIO(file_content), "audio/webm")}
        )

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]

    def test_upload_multiple_files_same_session(self, client, db_session):
        session = SessionService.create_session(db_session, "client_1", "online")

        # Upload first file
        response1 = client.post(
            f"/api/v1/sessions/{session.id}/audio",
            files={"file": ("file1.webm", BytesIO(b"data1"), "audio/webm")}
        )
        assert response1.status_code == 200

        # Upload second file
        response2 = client.post(
            f"/api/v1/sessions/{session.id}/audio",
            files={"file": ("file2.webm", BytesIO(b"data2"), "audio/webm")}
        )
        assert response2.status_code == 200

        # Verify both files are associated with session
        data1 = response1.json()
        data2 = response2.json()
        assert data1["file_id"] != data2["file_id"]

    def test_upload_large_audio_file(self, client, db_session):
        session = SessionService.create_session(db_session, "client_1", "online")

        # Create larger audio file
        large_data = b"x" * (5 * 1024 * 1024)  # 5MB

        response = client.post(
            f"/api/v1/sessions/{session.id}/audio",
            files={"file": ("large.webm", BytesIO(large_data), "audio/webm")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["size_bytes"] == len(large_data)

    def test_upload_audio_different_formats(self, client, db_session):
        session = SessionService.create_session(db_session, "client_1", "online")

        formats = [
            ("test.webm", "audio/webm"),
            ("test.mp4", "audio/mp4"),
            ("test.m4a", "audio/m4a"),
            ("test.wav", "audio/wav"),
        ]

        for filename, mime_type in formats:
            response = client.post(
                f"/api/v1/sessions/{session.id}/audio",
                files={"file": (filename, BytesIO(b"audio data"), mime_type)}
            )
            assert response.status_code == 200
            assert response.json()["filename"] == filename

    def test_stream_mode_accumulates_chunks(self, client, db_session, monkeypatch):
        # Set transcript mode to stream
        monkeypatch.setattr("app.config.settings.transcript_mode", "stream")

        session = SessionService.create_session(db_session, "client_1", "online")

        # Upload first chunk (not final)
        response1 = client.post(
            f"/api/v1/sessions/{session.id}/audio",
            files={"file": ("test.webm", BytesIO(b"chunk1"), "audio/webm")},
            params={"is_final": False}
        )
        assert response1.status_code == 200
        assert "chunk_" in response1.json()["file_id"]

        # Upload second chunk (not final)
        response2 = client.post(
            f"/api/v1/sessions/{session.id}/audio",
            files={"file": ("test.webm", BytesIO(b"chunk2"), "audio/webm")},
            params={"is_final": False}
        )
        assert response2.status_code == 200

    def test_batch_mode_saves_immediately(self, client, db_session, monkeypatch):
        monkeypatch.setattr("app.config.settings.transcript_mode", "batch")

        session = SessionService.create_session(db_session, "client_1", "online")

        response = client.post(
            f"/api/v1/sessions/{session.id}/audio",
            files={"file": ("test.webm", BytesIO(b"audio data"), "audio/webm")}
        )

        assert response.status_code == 200
        # In batch mode, file_id should be a real audio file ID, not a chunk ID
        assert "chunk_" not in response.json()["file_id"]

    def test_upload_audio_response_has_timestamp(self, client, db_session):
        session = SessionService.create_session(db_session, "client_1", "online")

        response = client.post(
            f"/api/v1/sessions/{session.id}/audio",
            files={"file": ("test.webm", BytesIO(b"data"), "audio/webm")}
        )

        data = response.json()
        assert "received_at" in data
        # Verify it's a valid ISO timestamp
        from datetime import datetime
        datetime.fromisoformat(data["received_at"])

    def test_upload_empty_file(self, client, db_session):
        session = SessionService.create_session(db_session, "client_1", "online")

        response = client.post(
            f"/api/v1/sessions/{session.id}/audio",
            files={"file": ("test.webm", BytesIO(b""), "audio/webm")}
        )

        assert response.status_code == 200
        assert response.json()["size_bytes"] == 0

    def test_upload_without_file(self, client, db_session):
        session = SessionService.create_session(db_session, "client_1", "online")

        response = client.post(
            f"/api/v1/sessions/{session.id}/audio"
        )

        assert response.status_code == 422
