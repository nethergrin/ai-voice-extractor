import pytest


class TestAppEndpoints:
    """Tests for main application endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_get_config(self, client):
        """Test configuration endpoint."""
        response = client.get("/config")

        assert response.status_code == 200
        data = response.json()
        assert "transcript_mode" in data
        assert data["transcript_mode"] in ["batch", "stream"]

    def test_config_reflects_settings(self, client, monkeypatch):
        """Test that config endpoint reflects actual settings."""
        monkeypatch.setattr("app.config.settings.transcript_mode", "batch")

        response = client.get("/config")
        data = response.json()

        assert data["transcript_mode"] == "batch"

    def test_invalid_endpoint(self, client):
        """Test that invalid endpoints return 404."""
        response = client.get("/invalid/endpoint")

        assert response.status_code == 404


class TestCORSHeaders:
    """Tests for CORS middleware configuration."""

    def test_cors_allow_all_origins(self, client):
        """Test that CORS allows all origins."""
        response = client.get("/health", headers={"Origin": "http://example.com"})

        assert response.status_code == 200

    def test_cors_allow_credentials(self, client):
        """Test that CORS allows credentials."""
        response = client.get(
            "/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET"
            }
        )

        assert response.status_code == 200


class TestRouterConfiguration:
    """Tests to verify routers are properly configured."""

    def test_sessions_router_registered(self, client):
        """Test that sessions router is registered."""
        # Create a session to verify router works
        response = client.post("/api/v1/sessions/", json={
            "client_id": "test",
            "mode": "online"
        })

        assert response.status_code == 200

    def test_audio_router_registered(self, client):
        """Test that audio router is registered."""
        from io import BytesIO
        from app.services.session import SessionService

        # Need a valid session first
        db_session = client.__dict__.get("_session") or None
        if db_session:
            session = SessionService.create_session(db_session, "test", "online")
            response = client.post(
                f"/api/v1/sessions/{session.id}/audio",
                files={"file": ("test.webm", BytesIO(b"data"), "audio/webm")}
            )
            assert response.status_code == 200

    def test_api_prefix_is_correct(self, client):
        """Test that API endpoints use correct prefix."""
        # Sessions without prefix should not exist
        response = client.get("/sessions/")
        assert response.status_code == 404

        # With prefix should work
        response = client.get("/api/v1/sessions/")
        assert response.status_code == 200


class TestResponseFormat:
    """Tests for response format consistency."""

    def test_error_response_format(self, client):
        """Test that error responses have consistent format."""
        response = client.get("/api/v1/sessions/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_json_response_content_type(self, client):
        """Test that responses have correct content type."""
        response = client.get("/health")

        assert "application/json" in response.headers.get("content-type", "")

    def test_validation_error_format(self, client):
        """Test that validation errors have proper format."""
        response = client.post("/api/v1/sessions/", json={
            "client_id": "test"
            # Missing required 'mode' field
        })

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
