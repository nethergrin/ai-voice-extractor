from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from pydantic import BaseModel
import whisper
import torch
import tempfile
import os
from pathlib import Path

app = FastAPI(title="Whisper Transcription Service")

# Determine device
def get_device():
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"  # Apple Metal Performance Shaders
    else:
        device = "cpu"
    print(f"[WHISPER] Using device: {device}")
    return device

DEVICE = get_device()

# Load model on startup
MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")
print(f"[WHISPER] Loading model: {MODEL_SIZE}")
try:
    whisper_model = whisper.load_model(MODEL_SIZE, device=DEVICE)
    print(f"[WHISPER] Model loaded successfully on {DEVICE}")
except Exception as e:
    print(f"[WHISPER] Error loading model: {e}")
    whisper_model = None


class TranscriptionRequest(BaseModel):
    model: str = MODEL_SIZE
    language: str = None


class TranscriptionResponse(BaseModel):
    text: str
    language: str
    segments: list


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "device": DEVICE,
        "model": MODEL_SIZE,
        "model_loaded": whisper_model is not None,
    }


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    file: UploadFile = File(...),
    model: str = Query(MODEL_SIZE),
    language: str = Query(None),
    format: str = Query(None),
):
    if not whisper_model:
        raise HTTPException(status_code=500, detail="Model not loaded")

    print(f"[WHISPER] Transcribing file: {file.filename}, model: {model}, language: {language}")

    try:
        # Save uploaded file to temporary location with correct format
        # Detect format from parameter or file extension
        if not format:
            if file.filename.endswith(".webm"):
                format = "webm"
            elif file.filename.endswith(".mp4") or file.filename.endswith(".m4a"):
                format = "m4a"
            else:
                format = "wav"

        suffix = f".{format}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            contents = await file.read()
            tmp_file.write(contents)
            tmp_path = tmp_file.name

        print(f"[WHISPER] Saved audio to: {tmp_path}, size: {len(contents)} bytes, format: {format}")

        # Transcribe
        print(f"[WHISPER] Starting transcription...")
        result = whisper_model.transcribe(
            tmp_path,
            language=language,
            verbose=False,
        )

        print(f"[WHISPER] Transcription complete. Text length: {len(result['text'])}")
        print(f"[WHISPER] Detected language: {result.get('language', 'unknown')}")

        # Clean up
        os.unlink(tmp_path)

        return {
            "text": result["text"],
            "language": result.get("language", "unknown"),
            "segments": result.get("segments", []),
        }

    except Exception as e:
        print(f"[WHISPER] Error during transcription: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
