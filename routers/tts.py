import os
import time
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from tts_engine import generate_tts, list_local_snapshots, get_current_snapshot, set_current_snapshot

BASE_DIR = Path(__file__).resolve().parent.parent
LIBRARY_AUDIO_DIR = BASE_DIR / "library_audio"

router = APIRouter(prefix="/api/tts", tags=["TTS"])

class GenerateRequest(BaseModel):
    text: str
    instruct: Optional[str] = None
    ref_audio: Optional[str] = None
    ref_text: Optional[str] = None
    speed: Optional[float] = 1.0
    duration: Optional[float] = None
    snapshot_id: Optional[str] = None

@router.get("/list_snapshots")
async def list_snapshots():
    """API lấy danh sách các snapshot model có sẵn"""
    try:
        snapshots = list_local_snapshots()
        current = get_current_snapshot()
        return {
            "snapshots": snapshots,
            "current": current
        }
    except Exception as e:
        print(f"Error listing snapshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/set_snapshot")
async def set_snapshot(snapshot_id: str):
    """API chọn snapshot model để sử dụng"""
    try:
        set_current_snapshot(snapshot_id)
        return {
            "success": True,
            "snapshot_id": snapshot_id,
            "message": f"Switched to snapshot {snapshot_id[:8]}..."
        }
    except Exception as e:
        print(f"Error setting snapshot: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/generate")
async def generate(req: GenerateRequest):
    if not req.text:
        raise HTTPException(status_code=400, detail="Text is required")

    ts = time.strftime("%Y%m%d_%H%M%S")
    filename_base = f"web_{ts}"
    audio_filename = f"{filename_base}.wav"
    json_filename = f"{filename_base}.json"

    output_path = LIBRARY_AUDIO_DIR / audio_filename
    meta_path = LIBRARY_AUDIO_DIR / json_filename

    try:
        generate_tts(
            text=req.text,
            output_path=output_path,
            ref_audio=req.ref_audio,
            ref_text=req.ref_text,
            instruct=req.instruct,
            speed=req.speed,
            duration=req.duration,
            snapshot_id=req.snapshot_id,
        )

        metadata = {
            "text": req.text,
            "instruct": req.instruct,
            "ref_text": req.text,
            "created_at": ts,
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        return {
            "status": "success",
            "filename": audio_filename,
            "url": f"/audio/library_audio/{audio_filename}",
            "metadata": metadata,
        }
    except Exception as e:
        print(f"Error generating TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))
