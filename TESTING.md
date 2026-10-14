# Testing Guide

## Backend Unit Tests

Complete unit test suite for the AI Voice Extractor backend with real audio samples from Docker container.

### Quick Start

```bash
cd backend

# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_models.py -v

# Run tests matching pattern
pytest -k "test_create_session" -v
```

### Test Structure

```
backend/
├── tests/
│   ├── conftest.py              # Fixtures: db, client, audio samples
│   ├── test_models.py           # Model serialization (15 tests)
│   ├── test_services.py         # Service layer (20 tests)
│   ├── test_api_sessions.py     # Session endpoints (13 tests)
│   ├── test_api_audio.py        # Audio upload (12 tests)
│   ├── test_app.py              # App endpoints (8 tests)
│   ├── test_transcription.py    # Transcription + audio integration (11 tests)
│   ├── fixtures/
│   │   └── audio/               # Real audio samples (20 files, 6.5MB)
│   └── README.md
├── pytest.ini                   # Pytest configuration
├── requirements.txt             # Includes pytest deps
└── TESTING.md                   # This file
```

### Test Coverage

**~80+ unit tests** covering:
- ✅ Database models and serialization
- ✅ Service layer business logic
- ✅ API endpoint validation
- ✅ Audio file handling
- ✅ Streaming vs batch modes
- ✅ Error cases and edge cases
- ✅ Transcription integration (with real audio samples)

### Audio Test Samples

20 real audio recordings extracted from Docker container:
- Sizes: 18KB to 713KB
- Languages: Indonesian, English, mixed
- Formats: WebM
- Includes: Transcripts with segments and timestamps

#### Available Fixtures

```python
@pytest.fixture
def sample_audio_webm():
    """Path to first audio file"""

@pytest.fixture
def sample_audio_data():
    """Binary audio data"""

@pytest.fixture
def sample_audio_files():
    """Dict of all audio files by name"""

@pytest.fixture
def sample_transcript_data():
    """Parsed transcript JSON with segments"""
```

### Running Specific Tests

```bash
# Models
pytest tests/test_models.py -v

# Services
pytest tests/test_services.py::TestSessionService -v
pytest tests/test_services.py::TestAudioService -v

# API Endpoints
pytest tests/test_api_sessions.py -v
pytest tests/test_api_audio.py -v

# Audio Integration
pytest tests/test_transcription.py -v

# App/Health
pytest tests/test_app.py -v
```

### Fixtures Reference

#### Database
```python
def test_something(db_session):
    # Fresh in-memory SQLite for each test
    # Auto-cleaned after test
```

#### TestClient
```python
def test_api(client, db_session):
    # FastAPI TestClient with mocked DB
    # No actual network calls
```

#### Temp Directory
```python
def test_files(temp_audio_dir):
    # Temporary directory for file I/O
    # Auto-cleaned after test
```

#### Audio Samples
```python
def test_transcription(sample_audio_data, sample_transcript_data):
    # Real audio from Docker container
    # Full transcription metadata included
```

### Docker Audio Extraction

To update audio samples from running Docker containers:

```bash
docker exec ai-voice-extractor-backend find /data/audio_storage -name "*.webm" | \
  while IFS= read -r file; do
    session_id=$(basename "$(dirname "$file")")
    docker cp ai-voice-extractor-backend:"$file" \
      "backend/tests/fixtures/audio/${session_id}.webm"
  done
```

### Debugging Tests

```bash
# Show print statements
pytest -s tests/test_models.py

# Stop on first failure
pytest -x tests/

# Show local variables on failure
pytest -l tests/test_services.py

# Drop to debugger on failure
pytest --pdb tests/

# Verbose output with timing
pytest -v --durations=0
```

### CI/CD Integration

Add to your CI pipeline:

```bash
# Run tests with coverage
pytest --cov=app --cov-report=xml --junitxml=test-results.xml

# Fail on coverage below threshold
pytest --cov=app --cov-fail-under=80
```

### Notes

- Tests use in-memory SQLite for speed
- Each test gets fresh database state
- File I/O is isolated to temp directories
- API tests use TestClient (no real HTTP)
- Audio fixtures are automatically loaded from `tests/fixtures/audio/`
- Requires: pytest 7.4.3+, pytest-asyncio 0.21.1+
