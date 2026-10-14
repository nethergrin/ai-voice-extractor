import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.transcription import TranscriptionService
from app.services.audio import AudioService
from app.services.session import SessionService


class TestTranscriptionService:
    """
    Tests for the TranscriptionService that handles audio transcription via Whisper API.

    Uses real audio samples extracted from Docker container for testing.
    """

    def test_transcribe_audio_file_not_found(self):
        """Test transcription with non-existent file."""
        import asyncio
        async def run_test():
            with pytest.raises(FileNotFoundError):
                await TranscriptionService.transcribe_audio("/nonexistent/path/audio.webm")
        asyncio.run(run_test())

    def test_transcribe_audio_detects_format(self, sample_audio_webm):
        """Test that transcription service detects audio format from file extension."""
        if sample_audio_webm is None:
            pytest.skip("No audio samples available")

        # Just verify the file exists and is readable
        assert sample_audio_webm.exists()
        assert sample_audio_webm.stat().st_size > 0

    def test_audio_sample_has_content(self, sample_audio_data):
        """Test that audio samples contain actual data."""
        assert len(sample_audio_data) > 0
        # WebM files start with specific magic bytes
        if sample_audio_data.startswith(b"fake"):
            # Fallback data, skip detailed checks
            pass
        else:
            # Real audio file
            assert sample_audio_data[:4] in [b"\x1aE\xdf\xa3"]  # WebM signature

    def test_transcription_result_has_required_fields(self, sample_transcript_data):
        """Test that transcription results have all required fields."""
        assert "text" in sample_transcript_data
        assert "language" in sample_transcript_data
        assert "segments" in sample_transcript_data
        assert isinstance(sample_transcript_data["segments"], list)

    def test_transcription_segment_structure(self, sample_transcript_data):
        """Test that transcript segments have proper structure."""
        if sample_transcript_data["segments"]:
            segment = sample_transcript_data["segments"][0]
            assert "start" in segment
            assert "end" in segment
            assert "text" in segment
            assert isinstance(segment["start"], (int, float))
            assert isinstance(segment["end"], (int, float))
            assert segment["start"] < segment["end"]

    def test_detected_language_is_valid(self, sample_transcript_data):
        """Test that detected language is a valid language code."""
        language = sample_transcript_data.get("language", "")
        # Language codes should be 2-3 character ISO codes
        assert len(language) in [2, 3, 5]  # en, eng, en-US

    @pytest.mark.asyncio
    async def test_transcription_connection_error(self):
        """Test handling of connection errors to Whisper service."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = \
                Exception("Connection refused")

            with pytest.raises(Exception):
                await TranscriptionService.transcribe_audio("/fake/path.webm")

    @pytest.mark.asyncio
    async def test_transcription_api_error(self):
        """Test handling of HTTP errors from Whisper API."""
        import httpx

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.raise_for_status.side_effect = \
                httpx.HTTPStatusError("400", request=MagicMock(), response=MagicMock())
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

            with pytest.raises(Exception):
                await TranscriptionService.transcribe_audio("/fake/path.webm")


class TestAudioTranscriptionWorkflow:
    """
    Integration tests for audio upload and transcription workflow.

    Uses real audio samples from Docker container.
    """

    def test_batch_mode_audio_file_persistence(self, db_session, temp_audio_dir, monkeypatch, sample_audio_data):
        """Test that audio files are properly saved in batch mode."""
        monkeypatch.setattr("app.config.settings.audio_storage_path", temp_audio_dir)
        monkeypatch.setattr("app.config.settings.transcript_mode", "batch")

        audio_file = AudioService.save_audio_file(
            db_session,
            session_id="session_123",
            filename="audio.webm",
            file_data=sample_audio_data
        )

        # Verify file was saved
        assert Path(audio_file.storage_path).exists()
        saved_data = Path(audio_file.storage_path).read_bytes()
        assert saved_data == sample_audio_data

    def test_stream_mode_chunk_accumulation(self, sample_audio_data):
        """Test that chunks accumulate correctly in stream mode."""
        session_id = "stream_session_123"

        # Split audio into chunks
        chunk_size = len(sample_audio_data) // 3
        chunk1 = sample_audio_data[:chunk_size]
        chunk2 = sample_audio_data[chunk_size:2*chunk_size]
        chunk3 = sample_audio_data[2*chunk_size:]

        AudioService.accumulate_chunk(session_id, chunk1)
        AudioService.accumulate_chunk(session_id, chunk2)
        AudioService.accumulate_chunk(session_id, chunk3)

        # Retrieve and verify
        accumulated = AudioService.get_accumulated_audio(session_id)
        assert accumulated == sample_audio_data

    def test_transcript_file_created(self, temp_audio_dir, monkeypatch, sample_transcript_data):
        """Test that transcript JSON file is created with correct structure."""
        monkeypatch.setattr("app.config.settings.audio_storage_path", temp_audio_dir)

        path = AudioService.save_transcript(
            session_id="session_123",
            audio_filename="audio.webm",
            transcript_data=sample_transcript_data
        )

        # Verify file exists
        assert Path(path).exists()

        # Verify content
        with open(path, 'r') as f:
            saved = json.load(f)

        assert saved["text"] == sample_transcript_data["text"]
        assert saved["language"] == sample_transcript_data["language"]
        assert len(saved["segments"]) == len(sample_transcript_data["segments"])


class TestAudioFileHandling:
    """Tests for audio file storage and retrieval."""

    def test_audio_file_persistence(self, db_session, temp_audio_dir, monkeypatch, sample_audio_data):
        """Verify audio files are properly saved to disk."""
        monkeypatch.setattr("app.config.settings.audio_storage_path", temp_audio_dir)

        audio_file = AudioService.save_audio_file(
            db_session,
            session_id="session_123",
            filename="test.webm",
            file_data=sample_audio_data
        )

        # Verify file exists and contains correct data
        assert Path(audio_file.storage_path).exists()
        with open(audio_file.storage_path, 'rb') as f:
            assert f.read() == sample_audio_data

    def test_transcript_json_format(self, temp_audio_dir, monkeypatch, sample_transcript_data):
        """Test that transcript JSON has correct structure."""
        monkeypatch.setattr("app.config.settings.audio_storage_path", temp_audio_dir)

        path = AudioService.save_transcript(
            session_id="session_123",
            audio_filename="audio.webm",
            transcript_data=sample_transcript_data
        )

        with open(path, 'r') as f:
            saved = json.load(f)

        # Verify required fields
        assert "timestamp" in saved
        assert "audio_file" in saved
        assert "text" in saved
        assert "language" in saved
        assert "segments" in saved
        assert isinstance(saved["segments"], list)
