import os
import time
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from tts_engine import generate_tts

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="OmniVoice Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/audio/input", StaticFiles(directory=str(INPUT_DIR)), name="input_audio")

class GenerateRequest(BaseModel):
    text: str
    instruct: Optional[str] = None
    ref_audio: Optional[str] = None
    ref_text: Optional[str] = None
    speed: Optional[float] = 1.0
    duration: Optional[float] = None

@app.post("/generate")
async def generate(req: GenerateRequest):
    if not req.text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    ts = time.strftime("%Y%m%d_%H%M%S")
    filename_base = f"web_{ts}"
    audio_filename = f"{filename_base}.wav"
    json_filename = f"{filename_base}.json"
    
    output_path = INPUT_DIR / audio_filename
    meta_path = INPUT_DIR / json_filename
    
    try:
        # 1. Tạo audio
        generate_tts(
            text=req.text,
            output_path=output_path,
            ref_audio=req.ref_audio,
            ref_text=req.ref_text,
            instruct=req.instruct,
            speed=req.speed,
            duration=req.duration
        )
        
        # 2. Lưu Metadata vào file JSON
        metadata = {
            "text": req.text,
            "instruct": req.instruct,
            "ref_text": req.text, # Lưu nội dung vừa tạo vào ref_text để dùng làm transcript mẫu sau này
            "created_at": ts
        }
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "success",
            "filename": audio_filename,
            "url": f"/audio/input/{audio_filename}",
            "metadata": metadata
        }
    except Exception as e:
        print(f"Error generating TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/list_audios")
async def list_audios():
    try:
        files = []
        for f in INPUT_DIR.glob("*.wav"):
            # Kiểm tra xem có file metadata JSON đi kèm không
            meta_file = f.with_suffix(".json")
            metadata = {}
            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as mf:
                        metadata = json.load(mf)
                except:
                    pass
            
            files.append({
                "name": f.name,
                "url": f"/audio/input/{f.name}",
                "type": "input",
                "mtime": f.stat().st_mtime,
                "metadata": metadata
            })
        
        files.sort(key=lambda x: x["mtime"], reverse=True)
        return files[:100] # Tăng giới hạn lên 100 file
    except Exception as e:
        print(f"Error listing audios: {e}")
        return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
