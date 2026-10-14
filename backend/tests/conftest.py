import pytest
import os
import tempfile
import shutil
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.database.models import Base


@pytest.fixture(scope="function")
def temp_audio_dir():
    """Create a temporary directory for audio storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def db_engine(temp_audio_dir, monkeypatch):
    """Create an in-memory SQLite database for testing."""
    monkeypatch.setenv("AUDIO_STORAGE_PATH", temp_audio_dir)

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a new database session for each test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session, temp_audio_dir, monkeypatch):
    """Create a FastAPI test client with mocked dependencies."""
    monkeypatch.setenv("AUDIO_STORAGE_PATH", temp_audio_dir)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.clear()


def get_fixture_audio_files():
    """Get list of available audio fixture files."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "audio"
    if not fixtures_dir.exists():
        return []
    return sorted([f for f in fixtures_dir.glob("*.webm")])


@pytest.fixture
def sample_audio_files():
    """Fixture providing all available test audio samples."""
    audio_files = get_fixture_audio_files()
    return {f.stem: f for f in audio_files}


@pytest.fixture
def sample_audio_webm():
    """Single test audio file in webm format."""
    files = get_fixture_audio_files()
    if files:
        return files[0]
    return None


@pytest.fixture
def sample_audio_data():
    """Binary data of a sample audio file."""
    files = get_fixture_audio_files()
    if files:
        return files[0].read_bytes()
    return b"fake audio data"


@pytest.fixture
def sample_transcript_data():
    """Sample transcript data from a Docker container recording."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "audio"
    transcript_files = sorted(fixtures_dir.glob("*.transcript.json"))
    if transcript_files:
        with open(transcript_files[0], 'r') as f:
            return json.load(f)
    return {
        "text": "Test transcription",
        "language": "en",
        "segments": [
            {"start": 0.0, "end": 1.5, "text": "Test", "tokens": []}
        ]
    }
