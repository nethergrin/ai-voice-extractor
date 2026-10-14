from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    database_url: str = "sqlite:///./app.db"
    audio_storage_path: str = "./audio_storage"
    debug: bool = True
    transcript_mode: str = "batch"  # "batch" or "stream"
    whisper_model: str = "base"
    diarization_api_url: str = "http://diarization-worker:8002"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
