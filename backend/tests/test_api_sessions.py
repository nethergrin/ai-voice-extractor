import pytest
from app.services.session import SessionService


class TestSessionEndpoints:
    def test_create_session_online(self, client):
        response = client.post("/api/v1/sessions/", json={
            "client_id": "client_1",
            "mode": "online"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["client_id"] == "client_1"
        assert data["mode"] == "online"
        assert data["status"] == "active"
        assert "id" in data
        assert data["id"].startswith("client_1_")

    def test_create_session_offline(self, client):
        response = client.post("/api/v1/sessions/", json={
            "client_id": "client_1",
            "mode": "offline"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "offline"

    def test_create_session_invalid_mode(self, client):
        response = client.post("/api/v1/sessions/", json={
            "client_id": "client_1",
            "mode": "invalid_mode"
        })

        assert response.status_code == 400
        assert "Mode must be" in response.json()["detail"]

    def test_create_session_missing_client_id(self, client):
        response = client.post("/api/v1/sessions/", json={
            "mode": "online"
        })

        assert response.status_code == 422

    def test_create_session_missing_mode(self, client):
        response = client.post("/api/v1/sessions/", json={
            "client_id": "client_1"
        })

        assert response.status_code == 422

    def test_get_session(self, client, db_session):
        # Create a session
        created = SessionService.create_session(db_session, "client_1", "online")

        response = client.get(f"/api/v1/sessions/{created.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created.id
        assert data["client_id"] == "client_1"
        assert data["status"] == "active"

    def test_get_session_not_found(self, client):
        response = client.get("/api/v1/sessions/nonexistent_id")

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]

    def test_get_all_sessions(self, client, db_session):
        session1 = SessionService.create_session(db_session, "client_1", "online")
        session2 = SessionService.create_session(db_session, "client_2", "offline")

        response = client.get("/api/v1/sessions/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2
        session_ids = {s["id"] for s in data["sessions"]}
        assert session_ids == {session1.id, session2.id}

    def test_get_all_sessions_empty(self, client):
        response = client.get("/api/v1/sessions/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 0

    def test_close_session(self, client, db_session):
        created = SessionService.create_session(db_session, "client_1", "online")

        response = client.post(f"/api/v1/sessions/{created.id}/close")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closed"
        assert data["closed_at"] is not None

    def test_close_session_not_found(self, client):
        response = client.post("/api/v1/sessions/nonexistent_id/close")

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]

    def test_session_response_format(self, client, db_session):
        # Verify all expected fields are in the response
        created = SessionService.create_session(db_session, "client_1", "online")

        response = client.get(f"/api/v1/sessions/{created.id}")

        data = response.json()
        expected_fields = {"id", "client_id", "mode", "status", "audio_duration", "created_at", "closed_at"}
        assert set(data.keys()) == expected_fields

    def test_create_session_generates_unique_ids(self, client):
        # Create multiple sessions and verify IDs are unique
        response1 = client.post("/api/v1/sessions/", json={"client_id": "client_1", "mode": "online"})
        response2 = client.post("/api/v1/sessions/", json={"client_id": "client_1", "mode": "online"})

        id1 = response1.json()["id"]
        id2 = response2.json()["id"]

        assert id1 != id2
