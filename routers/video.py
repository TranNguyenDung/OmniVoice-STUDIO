import os
import time
import json
import uuid
import asyncio
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
from moviepy import (
    VideoFileClip,
    ImageClip,
    AudioFileClip,
    concatenate_videoclips,
    CompositeVideoClip,
    Effect,
)
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
import moviepy.video.fx as vfx
import subprocess

BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_DIR = BASE_DIR / "media_uploads"
VIDEO_OUT_DIR = BASE_DIR / "output_videos"
TEMP_DEBUG_DIR = BASE_DIR / "temp_debug"

for d in [MEDIA_DIR, VIDEO_OUT_DIR, TEMP_DEBUG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/video", tags=["Video Generation"])

# Check NVIDIA GPU
def check_nvidia_gpu():
    try:
        result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=5)
        return "h264_nvenc" in result.stdout
    except:
        return False

HAS_NVIDIA_GPU = check_nvidia_gpu()
NUM_THREADS = os.cpu_count() or 4
FFMPEG_THREADS = max(4, NUM_THREADS // 2)

# Custom Effects for MoviePy 2.x
class Blur(Effect):
    def __init__(self, radius=20):
        self.radius = radius

    def copy(self):
        return Blur(radius=self.radius)

    def apply(self, clip):
        def filter_frame(get_frame, t):
            frame = get_frame(t)
            sigma = [self.radius / 2, self.radius / 2, 0]
            return gaussian_filter(frame, sigma=sigma)
        return clip.transform(filter_frame)

class KenBurnsEffect(Effect):
    def __init__(self, zoom_start=1.0, zoom_end=1.2, pan_start=(0, 0), pan_end=(0, 0)):
        self.zoom_start = zoom_start
        self.zoom_end = zoom_end
        self.pan_start = pan_start
        self.pan_end = pan_end

    def copy(self):
        return KenBurnsEffect(
            zoom_start=self.zoom_start,
            zoom_end=self.zoom_end,
            pan_start=self.pan_start,
            pan_end=self.pan_end,
        )

    def apply(self, clip):
        def filter_frame(get_frame, t):
            progress = t / clip.duration
            zoom = self.zoom_start + (self.zoom_end - self.zoom_start) * progress
            pan_x = self.pan_start[0] + (self.pan_end[0] - self.pan_start[0]) * progress
            pan_y = self.pan_start[1] + (self.pan_end[1] - self.pan_start[1]) * progress

            frame = get_frame(t)
            h, w = frame.shape[:2]

            scaled_w = int(w * zoom)
            scaled_h = int(h * zoom)

            if frame.shape[2] == 4:
                pil_frame = Image.fromarray(frame).convert("RGB")
            else:
                pil_frame = Image.fromarray(frame)

            scaled = pil_frame.resize((scaled_w, scaled_h), Image.LANCZOS)

            extra_w = scaled_w - w
            extra_h = scaled_h - h

            offset_x = (extra_w / 2) - (pan_x * extra_w)
            offset_y = (extra_h / 2) - (pan_y * extra_h)

            offset_x = max(0, min(offset_x, max(0, extra_w)))
            offset_y = max(0, min(offset_y, max(0, extra_h)))

            cropped = scaled.crop((int(offset_x), int(offset_y), int(offset_x + w), int(offset_y + h)))
            return np.array(cropped)

        return clip.transform(filter_frame)

class MultiplyColor(Effect):
    def __init__(self, opacity=0.7):
        self.opacity = opacity

    def copy(self):
        return MultiplyColor(opacity=self.opacity)

    def apply(self, clip):
        def filter_frame(get_frame, t):
            frame = get_frame(t)
            return (frame * self.opacity).astype(frame.dtype)
        return clip.transform(filter_frame)

def assemble_clip_layers(clip, target_w, target_h, blur_radius=20, bg_opacity=0.7, motion=None, motion_params=None):
    static_clip = clip
    fg_clip = clip
    
    if motion and motion != "none":
        import random
        if motion == "auto":
            motion_type = random.choice(["zoom", "pan", "kenburns"])
            if motion_type == "zoom":
                z_start, z_end = 1.0, random.uniform(1.2, 1.4)
                fg_clip = fg_clip.with_effects([KenBurnsEffect(zoom_start=z_start, zoom_end=z_end)])
            elif motion_type == "pan":
                z = random.uniform(1.25, 1.4)
                direction = random.choice(["left", "right", "up", "down"])
                amt = 0.15
                p_start, p_end = (amt, 0), (-amt, 0)
                if direction == "right": p_start, p_end = (-amt, 0), (amt, 0)
                elif direction == "up": p_start, p_end = (0, amt), (0, -amt)
                elif direction == "down": p_start, p_end = (0, -amt), (0, amt)
                fg_clip = fg_clip.with_effects([KenBurnsEffect(zoom_start=z, zoom_end=z, pan_start=p_start, pan_end=p_end)])
            else:
                z_start, z_end = 1.0, random.uniform(1.3, 1.5)
                amt = 0.1
                p_start = (random.uniform(-amt, amt), random.uniform(-amt, amt))
                p_end = (random.uniform(-amt, amt), random.uniform(-amt, amt))
                fg_clip = fg_clip.with_effects([KenBurnsEffect(zoom_start=z_start, zoom_end=z_end, pan_start=p_start, pan_end=p_end)])
        elif motion == "zoom":
            z_start = motion_params.get("zoom_start", 1.0)
            z_end = motion_params.get("zoom_end", 1.4)
            fg_clip = fg_clip.with_effects([KenBurnsEffect(zoom_start=z_start, zoom_end=z_end)])
        elif motion == "pan":
            z = motion_params.get("zoom", 1.3)
            px_s, px_e = motion_params.get("pan_x_start", 0.1), motion_params.get("pan_x_end", -0.1)
            py_s, py_e = motion_params.get("pan_y_start", 0), motion_params.get("pan_y_end", 0)
            fg_clip = fg_clip.with_effects([KenBurnsEffect(zoom_start=z, zoom_end=z, pan_start=(px_s, py_s), pan_end=(px_e, py_e))])
        elif motion == "kenburns":
            z_s, z_e = motion_params.get("zoom_start", 1.0), motion_params.get("zoom_end", 1.5)
            px_s, px_e = motion_params.get("pan_x_start", -0.1), motion_params.get("pan_x_end", 0.1)
            py_s, py_e = motion_params.get("pan_y_start", -0.05), motion_params.get("pan_y_end", 0.05)
            fg_clip = fg_clip.with_effects([KenBurnsEffect(zoom_start=z_s, zoom_end=z_e, pan_start=(px_s, py_s), pan_end=(px_e, py_e))])

    scale_w_bg = target_w / static_clip.w
    scale_h_bg = target_h / static_clip.h
    cover_scale = max(scale_w_bg, scale_h_bg)

    bg_clip = static_clip.resized(cover_scale).cropped(
        x_center=static_clip.w * cover_scale / 2,
        y_center=static_clip.h * cover_scale / 2,
        width=target_w,
        height=target_h,
    )

    bg_effects = [MultiplyColor(bg_opacity)]
    if blur_radius > 0:
        bg_effects.insert(0, Blur(radius=blur_radius))
    bg_clip = bg_clip.with_effects(bg_effects)

    scale_w_fg = target_w / fg_clip.w
    scale_h_fg = target_h / fg_clip.h
    contain_scale = min(scale_w_fg, scale_h_fg)
    
    fg_clip = fg_clip.resized(contain_scale).with_position("center")

    combined = CompositeVideoClip([bg_clip, fg_clip], size=(target_w, target_h))
    return combined.with_duration(clip.duration)

class VideoRequest(BaseModel):
    audio_url: str
    media_files: List[dict]
    aspect_ratio: Optional[str] = "16:9"
    blur_radius: Optional[int] = 20
    bg_opacity: Optional[float] = 0.7
    image_duration: Optional[float] = 5.0

@router.post("/upload_media")
async def upload_media(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = MEDIA_DIR / unique_filename

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    return {
        "filename": unique_filename,
        "url": f"/media/{unique_filename}",
        "type": "video" if ext.lower() in [".mp4", ".mov", ".avi"] else "image",
    }

@router.post("/generate")
async def generate_video(req: VideoRequest):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    temp_clips = []
    final_video = None
    one_cycle_video = None
    
    try:
        print(f"=== Starting Video Generation ({req.aspect_ratio}) ===")
        
        target_w, target_h = 1920, 1080
        if req.aspect_ratio == "9:16":
            target_w, target_h = 1080, 1920
        elif req.aspect_ratio == "1:1":
            target_w, target_h = 1080, 1080

        audio_filename = Path(req.audio_url).name
        audio_path = BASE_DIR / "library_audio" / audio_filename

        if not audio_path.exists():
            raise HTTPException(status_code=404, detail=f"Audio file not found: {audio_filename}")

        audio = AudioFileClip(str(audio_path))
        target_duration = audio.duration

        valid_media = [m for m in req.media_files if (MEDIA_DIR / m["filename"]).exists()]
        
        if not valid_media:
            raise HTTPException(status_code=400, detail="No valid media files found")

        clips = []
        img_duration = req.image_duration or 5.0

        def process_single_media(args):
            i, m, tw, th, blur_r, bg_op, img_dur = args
            m_path = MEDIA_DIR / m["filename"]
            m_duration = m.get("duration", img_dur)
            m_motion = m.get("motion", "none")
            m_motion_params = m.get("motion_params", {})

            if m["type"] == "image":
                clip = ImageClip(str(m_path)).with_duration(m_duration).with_fps(24)
            else:
                clip = VideoFileClip(str(m_path))

            assembled_clip = assemble_clip_layers(
                clip, tw, th, blur_radius=blur_r, bg_opacity=bg_op,
                motion=m_motion if m["type"] == "image" else None,
                motion_params=m_motion_params if m["type"] == "image" else None,
            )
            return i, assembled_clip

        tasks = [(i, m, target_w, target_h, req.blur_radius, req.bg_opacity, img_duration) 
                 for i, m in enumerate(valid_media)]

        max_workers = min(len(valid_media), NUM_THREADS)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_single_media, task): task[0] for task in tasks}
            for future in as_completed(futures):
                idx, result_clip = future.result()
                clips.append(result_clip)
                temp_clips.append(result_clip)

        one_cycle_video = concatenate_videoclips(clips, method="compose")
        one_cycle_duration = one_cycle_video.duration

        temp_debug_id = f"debug_{int(time.time())}"
        temp_debug_path = TEMP_DEBUG_DIR / temp_debug_id
        temp_debug_path.mkdir(exist_ok=True)
        one_cycle_path = temp_debug_path / "01_one_cycle.mp4"

        if HAS_NVIDIA_GPU:
            one_cycle_video.write_videofile(str(one_cycle_path), fps=24, codec="h264_nvenc", 
                audio=False, remove_temp=True, preset="p4", bitrate="4000k",
                ffmpeg_params=["-threads", str(FFMPEG_THREADS)], logger="bar")
        else:
            one_cycle_video.write_videofile(str(one_cycle_path), fps=24, codec="libx264",
                audio=False, remove_temp=True, preset="ultrafast", threads=FFMPEG_THREADS, 
                bitrate="3000k", logger="bar")

        if target_duration > one_cycle_duration:
            num_loops = int(target_duration / one_cycle_duration) + 1
            looped_clips = []
            for loop_idx in range(num_loops):
                looped_clip = VideoFileClip(str(one_cycle_path))
                actual_clip_duration = min(one_cycle_duration, looped_clip.duration)
                looped_clips.append(looped_clip.subclipped(0, actual_clip_duration))
            final_video = concatenate_videoclips(looped_clips, method="compose")
            for c in looped_clips:
                c.close()
        else:
            final_video = one_cycle_video

        final_video = final_video.subclipped(0, min(target_duration, final_video.duration))

        if final_video.w != target_w or final_video.h != target_h:
            final_video = CompositeVideoClip([final_video.with_position("center")], size=(target_w, target_h))

        final_video = final_video.with_duration(target_duration)
        final_video = final_video.with_audio(audio)

        output_filename = f"video_{int(time.time())}.mp4"
        output_path = VIDEO_OUT_DIR / output_filename

        loop = asyncio.get_event_loop()
        
        if HAS_NVIDIA_GPU:
            await loop.run_in_executor(None, lambda: final_video.write_videofile(
                str(output_path), fps=24, codec="h264_nvenc", audio_codec="aac",
                temp_audiofile=f"temp-audio-{uuid.uuid4()}.m4a", remove_temp=True,
                preset="p4", bitrate="4000k", logger="bar"))
        else:
            await loop.run_in_executor(None, lambda: final_video.write_videofile(
                str(output_path), fps=24, codec="libx264", audio_codec="aac",
                temp_audiofile=f"temp-audio-{uuid.uuid4()}.m4a", remove_temp=True,
                preset="ultrafast", threads=FFMPEG_THREADS, bitrate="3000k", logger="bar"))

        return {"status": "success", "url": f"/video/output/{output_filename}"}

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if final_video:
            final_video.close()
        if one_cycle_video:
            one_cycle_video.close()
        for c in temp_clips:
            try:
                c.close()
            except:
                pass
        if 'audio' in dir() and audio:
            audio.close()
