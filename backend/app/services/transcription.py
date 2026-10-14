import httpx
import os
import asyncio
from pathlib import Path

WHISPER_API_URL = os.getenv("WHISPER_API_URL", "http://whisper-worker:8001")
DIARIZATION_API_URL = os.getenv("DIARIZATION_API_URL", "http://diarization-worker:8002")


def _assign_speaker(segment_start: float, segment_end: float, speaker_turns: list) -> str | None:
    best_speaker = None
    best_overlap = 0.0
    for turn in speaker_turns:
        overlap = min(segment_end, turn["end"]) - max(segment_start, turn["start"])
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = turn["speaker"]
    return best_speaker


def _merge_speakers(transcript: dict, diarization: dict) -> dict:
    speaker_turns = diarization.get("speakers", [])
    for segment in transcript.get("segments", []):
        segment["speaker"] = _assign_speaker(segment["start"], segment["end"], speaker_turns)
    return transcript


class TranscriptionService:
    @staticmethod
    async def transcribe_audio(file_path: str, language: str = None, model: str = "base") -> dict:
        print(f"[TRANSCRIPTION] Transcribing file: {file_path}, language: {language}, model: {model}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        try:
            file_ext = Path(file_path).suffix.lower().lstrip(".")
            if file_ext in ["webm", "mp4", "m4a"]:
                audio_format = file_ext
                mime_type = f"audio/{file_ext}"
            else:
                audio_format = "wav"
                mime_type = "audio/wav"

            async with httpx.AsyncClient(timeout=300.0) as client:
                with open(file_path, "rb") as f:
                    files = {"file": (Path(file_path).name, f, mime_type)}
                    params = {"model": model, "format": audio_format}
                    if language:
                        params["language"] = language

                    print(f"[TRANSCRIPTION] Calling Whisper API at {WHISPER_API_URL}/transcribe (format: {audio_format})")
                    response = await client.post(
                        f"{WHISPER_API_URL}/transcribe",
                        files=files,
                        params=params,
                    )

                    response.raise_for_status()
                    result = response.json()

                    print(f"[TRANSCRIPTION] Transcription complete. Text length: {len(result['text'])}")
                    return result

        except httpx.HTTPStatusError as e:
            print(f"[TRANSCRIPTION] Whisper API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Transcription service error: {e.response.text}")
        except httpx.ConnectError as e:
            print(f"[TRANSCRIPTION] Failed to connect to Whisper service at {WHISPER_API_URL}")
            raise Exception(f"Transcription service unavailable: {str(e)}")
        except Exception as e:
            print(f"[TRANSCRIPTION] Error during transcription: {e}")
            raise

    @staticmethod
    async def diarize_audio(file_path: str) -> dict | None:
        print(f"[DIARIZATION] Diarizing file: {file_path}")

        try:
            file_ext = Path(file_path).suffix.lower().lstrip(".")
            if file_ext in ["webm", "mp4", "m4a"]:
                mime_type = f"audio/{file_ext}"
            else:
                mime_type = "audio/wav"

            async with httpx.AsyncClient(timeout=300.0) as client:
                with open(file_path, "rb") as f:
                    files = {"file": (Path(file_path).name, f, mime_type)}
                    response = await client.post(
                        f"{DIARIZATION_API_URL}/diarize",
                        files=files,
                    )
                    response.raise_for_status()
                    result = response.json()
                    print(f"[DIARIZATION] Complete. Speakers: {len(set(s['speaker'] for s in result.get('speakers', [])))}")
                    return result

        except httpx.ConnectError:
            print(f"[DIARIZATION] Service unavailable at {DIARIZATION_API_URL}, skipping")
            return None
        except httpx.HTTPStatusError as e:
            print(f"[DIARIZATION] Error {e.response.status_code}: {e.response.text}, skipping")
            return None
        except Exception as e:
            print(f"[DIARIZATION] Unexpected error: {e}, skipping")
            return None

    @staticmethod
    async def transcribe_and_diarize(file_path: str, language: str = None, model: str = "base") -> dict:
        transcript_task = TranscriptionService.transcribe_audio(file_path, language, model)
        diarization_task = TranscriptionService.diarize_audio(file_path)

        transcript, diarization = await asyncio.gather(transcript_task, diarization_task, return_exceptions=True)

        if isinstance(transcript, Exception):
            raise transcript

        if diarization and not isinstance(diarization, Exception):
            transcript = _merge_speakers(transcript, diarization)

        return transcript
