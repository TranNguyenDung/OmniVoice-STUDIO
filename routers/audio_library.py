import time
import json
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
LIBRARY_AUDIO_DIR = BASE_DIR / "library_audio"

router = APIRouter(prefix="/api/audio", tags=["Audio Library"])

@router.get("/list")
async def list_audios():
    try:
        files = []
        for f in LIBRARY_AUDIO_DIR.glob("*.wav"):
            meta_file = f.with_suffix(".json")
            metadata = {}
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as mf:
                        metadata = json.load(mf)
                except:
                    pass

            files.append({
                "name": f.name,
                "url": f"/audio/library_audio/{f.name}",
                "type": "input",
                "mtime": f.stat().st_mtime,
                "metadata": metadata,
            })

        files.sort(key=lambda x: x["mtime"], reverse=True)
        return files[:100]
    except Exception as e:
        print(f"Error listing audios: {e}")
        return []

@router.delete("/delete")
async def delete_audio_item(filename: str):
    try:
        file_path = LIBRARY_AUDIO_DIR / filename
        meta_file = LIBRARY_AUDIO_DIR / (Path(filename).stem + ".json")
        
        if file_path.exists():
            file_path.unlink()
        if meta_file.exists():
            meta_file.unlink()
            
        return {"success": True, "message": f"Deleted {filename}"}
    except Exception as e:
        print(f"Error deleting audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{filename:path}")
async def delete_audio(filename: str):
    """Xóa audio khỏi thư viện"""
    audio_path = Path(filename)
    if audio_path.is_absolute():
        audio_file = LIBRARY_AUDIO_DIR / audio_path.name
    else:
        audio_file = LIBRARY_AUDIO_DIR / audio_path.name
    
    json_file = audio_file.with_suffix('.json')
    
    if audio_file.exists():
        audio_file.unlink()
    if json_file.exists():
        json_file.unlink()
    
    return {"status": "success", "filename": audio_file.name}

@router.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    text: Optional[str] = Form(None),
    instruct: Optional[str] = Form(None),
):
    """Upload audio ghi âm vào thư viện (library_audio/)"""
    ts = time.strftime("%Y%m%d_%H%M%S")
    ext = Path(file.filename).suffix if file.filename else ".wav"
    
    if file.filename and Path(file.filename).stem:
        filename_base = Path(file.filename).stem
    else:
        filename_base = f"rec_{ts}_{os.urandom(3).hex}"
    audio_filename = f"{filename_base}{ext}"
    json_filename = f"{filename_base}.json"
    
    audio_path = LIBRARY_AUDIO_DIR / audio_filename
    meta_path = LIBRARY_AUDIO_DIR / json_filename

    with open(audio_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    metadata = {
        "text": text or "",
        "instruct": instruct or "",
        "ref_text": text or "",
        "created_at": ts,
        "source": "record",
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return {
        "status": "success",
        "filename": audio_filename,
        "url": f"/audio/library_audio/{audio_filename}",
        "metadata": metadata,
    }
