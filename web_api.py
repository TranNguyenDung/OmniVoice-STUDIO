import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from routers.tts import router as tts_router
from routers.audio_library import router as audio_router
from routers.video import router as video_router
from routers.ffmpeg import router as ffmpeg_router

BASE_DIR = Path(__file__).resolve().parent
LIBRARY_AUDIO_DIR = BASE_DIR / "library_audio"
MEDIA_DIR = BASE_DIR / "media_uploads"
VIDEO_OUT_DIR = BASE_DIR / "output_videos"

app = FastAPI(title="OmniVoice Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/audio/library_audio", StaticFiles(directory=str(LIBRARY_AUDIO_DIR)), name="library_audio")
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
app.mount("/video/output", StaticFiles(directory=str(VIDEO_OUT_DIR)), name="video_output")

# Include routers
app.include_router(tts_router)
app.include_router(audio_router)
app.include_router(video_router)
app.include_router(ffmpeg_router)

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Use 1 worker to ensure shared in-memory state (like srt_progress) works correctly
    # Multiple workers have separate memory spaces
    print(f"Starting server with 1 worker...")
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)
