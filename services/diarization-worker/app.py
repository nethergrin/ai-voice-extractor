from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from pyannote.audio import Pipeline
import torch
import tempfile
import os

HF_TOKEN = os.getenv("HF_TOKEN")

def get_device():
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    return "cpu"

DEVICE = get_device()
pipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    if not HF_TOKEN:
        print("[DIARIZATION] HF_TOKEN not set, model will not be loaded")
    else:
        try:
            print(f"[DIARIZATION] Loading pipeline on {DEVICE}...")
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=HF_TOKEN,
            )
            if DEVICE != "cpu":
                pipeline = pipeline.to(torch.device(DEVICE))
            print("[DIARIZATION] Pipeline loaded successfully")
        except Exception as e:
            print(f"[DIARIZATION] Error loading pipeline: {e}")
    yield


app = FastAPI(title="Diarization Service", lifespan=lifespan)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "device": DEVICE,
        "model_loaded": pipeline is not None,
    }


@app.post("/diarize")
async def diarize(file: UploadFile = File(...)):
    if not pipeline:
        raise HTTPException(status_code=503, detail="Diarization model not loaded")

    suffix = ".wav"
    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in [".webm", ".mp4", ".m4a"]:
            suffix = ext

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        print(f"[DIARIZATION] Processing: {file.filename}, size: {len(contents)} bytes")
        result = pipeline(tmp_path)
        annotation = getattr(result, "speaker_diarization", result)
        speakers = [
            {"speaker": speaker, "start": round(turn.start, 3), "end": round(turn.end, 3)}
            for turn, _, speaker in annotation.itertracks(yield_label=True)
        ]
        unique_speakers = len(set(s["speaker"] for s in speakers))
        print(f"[DIARIZATION] Done: {unique_speakers} speakers, {len(speakers)} turns")
        return {"speakers": speakers}
    except Exception as e:
        print(f"[DIARIZATION] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Diarization failed: {str(e)}")
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
