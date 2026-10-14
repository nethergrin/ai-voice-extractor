from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.api.v1 import sessions, audio, transcriptions
from app.config import settings
from pydantic import BaseModel

app = FastAPI(title="AI Voice Extractor API")

class ConfigResponse(BaseModel):
    transcript_mode: str

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router, prefix="/api/v1")
app.include_router(audio.router, prefix="/api/v1")
app.include_router(transcriptions.router, prefix="/api/v1")


@app.on_event("startup")
def startup_event():
    init_db()
    print(f"\n{'='*60}")
    print(f"[SERVER] Starting AI Voice Extractor Backend")
    print(f"[SERVER] TRANSCRIPT_MODE: {settings.transcript_mode}")
    print(f"[SERVER] WHISPER_MODEL: {settings.whisper_model}")
    print(f"{'='*60}\n")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/config", response_model=ConfigResponse)
def get_config():
    return {"transcript_mode": settings.transcript_mode}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
