# Backend Unit Tests

Unit test suite for the AI Voice Extractor backend.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Shared fixtures (database, client, temp directories)
├── test_models.py             # Database model serialization tests
├── test_services.py           # Service layer business logic tests
├── test_api_sessions.py       # Session endpoint tests
├── test_api_audio.py          # Audio upload endpoint tests
├── test_transcription.py      # Transcription service tests (placeholder for audio samples)
├── pytest.ini                 # Pytest configuration
└── README.md                  # This file
```

## Coverage

### Models (`test_models.py`)
- **Session**: Creation, serialization, datetime handling
- **AudioFile**: Creation, serialization, path handling
- **Transcript**: Creation, serialization, segments parsing, status defaults

### Services (`test_services.py`)
- **SessionService**:
  - Create, retrieve, list, close sessions
  - Client-specific queries
  - Session state management
  - Unique ID generation

- **AudioService**:
  - File persistence and storage
  - Directory creation
  - Chunk accumulation (streaming)
  - Transcript file creation
  - Partial transcript handling

### API Endpoints (`test_api_sessions.py`, `test_api_audio.py`)
- **Sessions**:
  - Create session (online/offline modes)
  - Get single session
  - List all sessions
  - Close session
  - Error cases (invalid mode, not found, missing fields)

- **Audio**:
  - Upload to existing session
  - Auto-create session on upload
  - Multiple file uploads
  - Different audio formats (webm, mp4, m4a, wav)
  - Stream mode chunk accumulation
  - Batch mode immediate save
  - Empty files, missing files, validation

### Transcription (`test_transcription.py`)
- Placeholder tests ready for audio samples
- Tests for different audio formats
- Language detection
- Error handling (connection errors, API errors, timeouts)
- Integration workflow tests (batch and stream modes)
- Transcript file structure validation

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/test_models.py
```

### Run specific test class
```bash
pytest tests/test_services.py::TestSessionService
```

### Run specific test
```bash
pytest tests/test_api_sessions.py::TestSessionEndpoints::test_create_session_online
```

### Run with verbose output
```bash
pytest -v
```

### Run with coverage report
```bash
pytest --cov=app --cov-report=html
```

### Run only async tests
```bash
pytest -m asyncio
```

### Run without async tests
```bash
pytest -m "not asyncio"
```

## Fixtures

### `db_engine`
Creates an in-memory SQLite database for testing. Tables are created fresh for each test.

### `db_session`
Provides a database session for a single test. Automatically cleaned up after test.

### `client`
FastAPI TestClient with dependency overrides for database access. Uses in-memory DB and temp directory.

### `temp_audio_dir`
Temporary directory for audio file storage. Automatically cleaned up after test.

## Adding New Tests

1. **Model tests**: Add to `test_models.py` - test serialization and defaults
2. **Service tests**: Add to `test_services.py` - test business logic in isolation
3. **API tests**: Add to appropriate `test_api_*.py` - test endpoints with mocked DB
4. **Transcription tests**: Add to `test_transcription.py` - will integrate audio samples

### Example test structure
```python
def test_something(self, client, db_session):
    # Arrange - set up test data
    session = SessionService.create_session(db_session, "client_1", "online")
    
    # Act - perform action
    response = client.post(f"/api/v1/sessions/{session.id}/audio", ...)
    
    # Assert - verify results
    assert response.status_code == 200
```

## Audio Sample Integration (Pending)

The following test files have placeholder sections for integration with real audio samples:

- `test_transcription.py`: Transcription service tests
  - Format compatibility (webm, mp4, m4a, wav)
  - Language detection
  - Segment accuracy
  - Error handling

Once audio samples are provided:
1. Add fixture functions in `conftest.py` or `test_transcription.py`
2. Implement the placeholder tests
3. Run full integration tests
4. Update CI/CD pipeline if needed

## Test Requirements

- `pytest==7.4.3`
- `pytest-asyncio==0.21.1`
- Dependencies from `requirements.txt` (FastAPI, SQLAlchemy, etc.)

## Notes

- Tests use in-memory SQLite for speed and isolation
- Each test gets a fresh database state
- File I/O tests use temporary directories auto-cleaned after test
- API tests use `TestClient` - no actual network calls
- Transcription tests mock the Whisper API until real audio samples are available
