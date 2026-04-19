import os
import time
import json
import uuid
import asyncio
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
from tts_engine import generate_tts
from moviepy import (
    VideoFileClip,
    ImageClip,
    AudioFileClip,
    concatenate_videoclips,
    CompositeVideoClip,
)
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image

from moviepy.Effect import Effect

import subprocess

def check_nvidia_gpu():
    try:
        result = subprocess.run(
            ["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=5
        )
        return "h264_nvenc" in result.stdout
    except:
        return False

HAS_NVIDIA_GPU = check_nvidia_gpu()

import os
NUM_THREADS = os.cpu_count() or 4
FFMPEG_THREADS = max(4, NUM_THREADS // 2)


# Custom Blur effect for MoviePy 2.x
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


# Ken Burns / Zoom / Pan Effect for MoviePy 2.x
class KenBurnsEffect(Effect):
    def __init__(self, zoom_start=1.0, zoom_end=1.2, pan_start=(0, 0), pan_end=(0, 0)):
        self.zoom_start = zoom_start
        self.zoom_end = zoom_end
        self.pan_start = pan_start  # (x, y) as fractions of frame size
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

            # Convert RGBA to RGB if needed (PIL requires RGB for LANCZOS)
            if frame.shape[2] == 4:
                pil_frame = Image.fromarray(frame).convert("RGB")
            else:
                pil_frame = Image.fromarray(frame)

            scaled = pil_frame.resize((scaled_w, scaled_h), Image.LANCZOS)

            # Calculate offset to keep center aligned
            # Center offset: (scaled_w - w) / 2
            # Pan adjusts from center: -pan_x * extra_space (negative pan_x = move right, positive = move left)
            extra_w = scaled_w - w
            extra_h = scaled_h - h

            offset_x = (extra_w / 2) - (pan_x * extra_w)
            offset_y = (extra_h / 2) - (pan_y * extra_h)

            offset_x = max(0, min(offset_x, max(0, extra_w)))
            offset_y = max(0, min(offset_y, max(0, extra_h)))

            cropped = scaled.crop(
                (int(offset_x), int(offset_y), int(offset_x + w), int(offset_y + h))
            )
            return np.array(cropped)

        return clip.transform(filter_frame)


HAS_BLUR = True

from moviepy.video.fx import MultiplyColor

BASE_DIR = Path(__file__).resolve().parent
LIBRARY_AUDIO_DIR = BASE_DIR / "library_audio"
OUTPUT_DIR = BASE_DIR / "output"
MEDIA_DIR = BASE_DIR / "media_uploads"
VIDEO_OUT_DIR = BASE_DIR / "output_videos"
TEMP_DEBUG_DIR = BASE_DIR / "temp_debug"

for d in [LIBRARY_AUDIO_DIR, OUTPUT_DIR, MEDIA_DIR, VIDEO_OUT_DIR, TEMP_DEBUG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="OmniVoice Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/audio/library_audio", StaticFiles(directory=str(LIBRARY_AUDIO_DIR)), name="library_audio")
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
app.mount(
    "/video/output", StaticFiles(directory=str(VIDEO_OUT_DIR)), name="video_output"
)


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


@app.get("/list_audios")
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

            files.append(
                {
                    "name": f.name,
                    "url": f"/audio/library_audio/{f.name}",
                    "type": "input",
                    "mtime": f.stat().st_mtime,
                    "metadata": metadata,
                }
            )

        files.sort(key=lambda x: x["mtime"], reverse=True)
        return files[:100]
    except Exception as e:
        print(f"Error listing audios: {e}")
        return []


@app.post("/upload_media")
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


@app.post("/upload_audio")
async def upload_audio(
    file: UploadFile = File(...),
    text: Optional[str] = Form(None),
    instruct: Optional[str] = Form(None),
):
    """Upload audio ghi âm vào thư viện (library_audio/)"""
    ts = time.strftime("%Y%m%d_%H%M%S")
    ext = Path(file.filename).suffix if file.filename else ".wav"
    
    # Sử dụng tên file từ frontend nếu có, không thì tạo tên mặc định
    if file.filename and Path(file.filename).stem:
        filename_base = Path(file.filename).stem
    else:
        filename_base = f"rec_{ts}_{uuid.uuid4().hex[:6]}"
    audio_filename = f"{filename_base}{ext}"
    json_filename = f"{filename_base}.json"
    
    audio_path = LIBRARY_AUDIO_DIR / audio_filename
    meta_path = LIBRARY_AUDIO_DIR / json_filename

    # Lưu file audio
    with open(audio_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Lưu metadata
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


@app.delete("/audio/{filename:path}")
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


class VideoRequest(BaseModel):
    audio_url: str
    media_files: List[
        dict
    ]  # [{"filename": "...", "type": "image|video", "duration": 5.0, "motion": "none|zoom|pan|kenburns", "motion_params": {...}}]
    aspect_ratio: Optional[str] = "16:9"
    blur_radius: Optional[int] = 20
    bg_opacity: Optional[float] = 0.7
    image_duration: Optional[float] = 5.0  # Default thời gian hiển thị cho ảnh (giây)


def assemble_clip_layers(
    clip,
    target_w,
    target_h,
    blur_radius=20,
    bg_opacity=0.7,
    motion=None,
    motion_params=None,
):
    """
    Nguyên lý lắp ghép (Assembly Principle):
    1. Lớp nền (Background Layer):
       - Lấy từ ảnh tĩnh (không áp dụng motion của fg).
       - Scale clip để phủ kín (cover) toàn bộ khung hình.
       - Áp dụng Blur và làm tối.
    2. Lớp trên (Foreground Layer):
       - Áp dụng motion effect (zoom, pan, kenburns).
       - Đảm bảo 'pan' luôn có zoom > 1.0 để có không gian trượt.
       - Scale clip để vừa khít (contain) trong khung hình.
    3. Kết hợp (Composition):
       - Chồng lớp trên lên lớp nền.
    """
    # Tạo bản sao tĩnh cho nền
    static_clip = clip

    # --- XỬ LÝ MOTION CHO LỚP TRÊN (FG) ---
    fg_clip = clip
    if motion and motion != "none":
        import random
        print(f"    [motion] Applying {motion} effect")

        if motion == "auto":
            motion_type = random.choice(["zoom", "pan", "kenburns"])
            if motion_type == "zoom":
                z_start, z_end = 1.0, random.uniform(1.2, 1.4)
                fg_clip = fg_clip.with_effects([KenBurnsEffect(zoom_start=z_start, zoom_end=z_end)])
            elif motion_type == "pan":
                # Pan BUỘC phải có zoom để có chỗ trượt
                z = random.uniform(1.25, 1.4)
                direction = random.choice(["left", "right", "up", "down"])
                amt = 0.15
                p_start, p_end = (amt, 0), (-amt, 0)
                if direction == "right": p_start, p_end = (-amt, 0), (amt, 0)
                elif direction == "up": p_start, p_end = (0, amt), (0, -amt)
                elif direction == "down": p_start, p_end = (0, -amt), (0, amt)
                fg_clip = fg_clip.with_effects([KenBurnsEffect(zoom_start=z, zoom_end=z, pan_start=p_start, pan_end=p_end)])
            else: # kenburns
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
            z = motion_params.get("zoom", 1.3) # Ép zoom tối thiểu 1.3 nếu là pan
            px_s, px_e = motion_params.get("pan_x_start", 0.1), motion_params.get("pan_x_end", -0.1)
            py_s, py_e = motion_params.get("pan_y_start", 0), motion_params.get("pan_y_end", 0)
            fg_clip = fg_clip.with_effects([KenBurnsEffect(zoom_start=z, zoom_end=z, pan_start=(px_s, py_s), pan_end=(px_e, py_e))])

        elif motion == "kenburns":
            z_s, z_e = motion_params.get("zoom_start", 1.0), motion_params.get("zoom_end", 1.5)
            px_s, px_e = motion_params.get("pan_x_start", -0.1), motion_params.get("pan_x_end", 0.1)
            py_s, py_e = motion_params.get("pan_y_start", -0.05), motion_params.get("pan_y_end", 0.05)
            fg_clip = fg_clip.with_effects([KenBurnsEffect(zoom_start=z_s, zoom_end=z_e, pan_start=(px_s, py_s), pan_end=(px_e, py_e))])

    # 1. Tạo lớp nền (Background Layer) - Dùng static_clip
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

    # 2. Tạo lớp trên (Foreground Layer) - Dùng fg_clip (đã có motion)
    scale_w_fg = target_w / fg_clip.w
    scale_h_fg = target_h / fg_clip.h
    contain_scale = min(scale_w_fg, scale_h_fg)
    
    # resized() trên một clip đã có effect sẽ áp dụng lên từng frame của effect đó
    fg_clip = fg_clip.resized(contain_scale).with_position("center")

    # 3. Kết hợp
    combined = CompositeVideoClip([bg_clip, fg_clip], size=(target_w, target_h))
    return combined.with_duration(clip.duration)



@app.post("/generate_video")
async def generate_video(req: VideoRequest):
    temp_clips = []
    final_video = None
    try:
        print(f"=== BLOCK 0: KHỞI TẠO ===")
        print(f"--- Starting Video Generation ({req.aspect_ratio}) ---")
        print(f"--- Settings: Blur={req.blur_radius}, Opacity={req.bg_opacity} ---")

        # ============================================================
        # BLOCK 1: XÁC ĐỊNH THÔNG SỐ MỤC TIÊU
        # Mục tiêu: Setup kích thước video output theo aspect ratio
        # ============================================================
        print(f"\n=== BLOCK 1: THÔNG SỐ MỤC TIÊU ===")
        target_w, target_h = 1920, 1080
        if req.aspect_ratio == "9:16":
            target_w, target_h = 1080, 1920
        elif req.aspect_ratio == "1:1":
            target_w, target_h = 1080, 1080
        print(f"[OK] Target size: {target_w}x{target_h}")

        # ============================================================
        # BLOCK 2: LOAD AUDIO
        # Mục tiêu: Lấy duration tổng của video từ audio
        # ============================================================
        print(f"\n=== BLOCK 2: LOAD AUDIO ===")
        audio_filename = Path(req.audio_url).name
        audio_path = LIBRARY_AUDIO_DIR / audio_filename

        if not audio_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Audio file not found: {audio_filename}"
            )

        audio = AudioFileClip(str(audio_path))
        target_duration = audio.duration
        print(f"[OK] Audio loaded: {audio_filename}, duration: {target_duration:.2f}s")

        # ============================================================
        # BLOCK 3: FILTER MEDIA HỢP LỆ
        # Mục tiêu: Lọc ra các media file tồn tại trong thư mục
        # ============================================================
        print(f"\n=== BLOCK 3: FILTER MEDIA HỢP LỆ ===")
        print(f"Input: {len(req.media_files)} media files")

        valid_media = [
            m for m in req.media_files if (MEDIA_DIR / m["filename"]).exists()
        ]
        print(f"Valid media found: {len(valid_media)}")

        for idx, m in enumerate(valid_media):
            print(f"  - [{idx + 1}] {m['filename']} (type: {m['type']})")

        if not valid_media:
            raise HTTPException(status_code=400, detail="No valid media files found")

        # ============================================================
        # BLOCK 4: KHỞI TẠO MẢNG CLIPS
        # Mục tiêu: Chuẩn bị danh sách clips rỗng
        # ============================================================
        print(f"\n=== BLOCK 4: KHỞI TẠO CLIPS ARRAY ===")
        clips = []
        img_duration = req.image_duration if hasattr(req, "image_duration") else 5.0
        print(f"[OK] Image duration: {img_duration}s")
        print(f"[OK] Target audio duration: {target_duration:.2f}s")
        print(f"[OK] Total media files: {len(valid_media)}")

        # ============================================================
        # BLOCK 5: XỬ LÝ TỪNG MEDIA FILE -> CLIP (PARALLEL)
        # Mục tiêu: Load từng media, áp dụng assembly layers (blur + opacity + scale)
        # Output: Mảng clips đã được assemble
        # ============================================================
        print(f"\n=== BLOCK 5: XỬ LÝ TỪNG MEDIA -> CLIP (PARALLEL) ===")
        from concurrent.futures import ThreadPoolExecutor, as_completed

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
                clip,
                tw,
                th,
                blur_radius=blur_r,
                bg_opacity=bg_op,
                motion=m_motion if m["type"] == "image" else None,
                motion_params=m_motion_params if m["type"] == "image" else None,
            )
            return i, assembled_clip

        tasks = [
            (i, m, target_w, target_h, req.blur_radius, req.bg_opacity, img_duration)
            for i, m in enumerate(valid_media)
        ]

        max_workers = min(len(valid_media), NUM_THREADS)
        print(f"[5a] Processing {len(valid_media)} media with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_single_media, task): task[0] for task in tasks}
            for future in as_completed(futures):
                idx, result_clip = future.result()
                clips.append(result_clip)
                temp_clips.append(result_clip)
                print(f"[5b] Media {idx + 1}/{len(valid_media)} done")

        print(f"[5c] All media processed. Total clips: {len(clips)}")

        # ============================================================
        # BLOCK 6: KIỂM TRA TRƯỚC KHI GHÉP
        # Mục tiêu: Xác nhận số lượng clips trước khi concatenate
        # ============================================================
        print(f"\n=== BLOCK 6: KIỂM TRA TRƯỚC KHI GHÉP ===")
        print(f"Total clips ready for concatenation: {len(clips)}")

        if not clips:
            raise HTTPException(status_code=400, detail="No clips generated")

        # ============================================================
        # BLOCK 7: GHÉP CLIPS VÀ LOOP NẾU CẦN
        # Mục tiêu: Nối tất cả clips, loop nếu audio dài hơn tổng duration
        # ============================================================
        print(f"\n=== BLOCK 7: CONCATENATE CLIPS ===")
        print(f"Concatenating {len(clips)} clips into single video...")

        one_cycle_video = concatenate_videoclips(clips, method="compose")
        one_cycle_duration = one_cycle_video.duration
        print(f"[OK] One cycle duration: {one_cycle_duration:.2f}s")

        temp_debug_id = f"debug_{int(time.time())}"
        temp_debug_path = TEMP_DEBUG_DIR / temp_debug_id
        temp_debug_path.mkdir(exist_ok=True)

        one_cycle_path = temp_debug_path / "01_one_cycle.mp4"
        print(f"[7a] Saving one cycle to: {one_cycle_path}")
        
        if HAS_NVIDIA_GPU:
            print(f"[GPU] Using NVIDIA encoder h264_nvenc, threads={FFMPEG_THREADS}")
            one_cycle_video.write_videofile(
                str(one_cycle_path),
                fps=24,
                codec="h264_nvenc",
                audio=False,
                remove_temp=True,
                preset="p4",
                bitrate="4000k",
                ffmpeg_params=["-threads", str(FFMPEG_THREADS)],
                logger="bar",
            )
        else:
            print(f"[CPU] Using libx264 with ultrafast, threads={FFMPEG_THREADS}")
            one_cycle_video.write_videofile(
                str(one_cycle_path),
                fps=24,
                codec="libx264",
                audio=False,
                remove_temp=True,
                preset="ultrafast",
                threads=FFMPEG_THREADS,
                bitrate="3000k",
                logger="bar",
            )

        if target_duration > one_cycle_duration:
            print(
                f"[7b] Audio ({target_duration:.2f}s) > Media ({one_cycle_duration:.2f}s), looping..."
            )
            num_loops = int(target_duration / one_cycle_duration) + 1
            print(f"[7b] Number of loops needed: {num_loops}")

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

        final_video = final_video.subclipped(
            0, min(target_duration, final_video.duration)
        )
        print(
            f"[OK] Final video: {final_video.w}x{final_video.h}, duration={final_video.duration:.2f}s"
        )

        # ============================================================
        # BLOCK 8: ĐẢM BẢO KÍCH THƯỚC CHUẨN
        # Mục tiêu: Resize nếu kích thước không đúng target
        # ============================================================
        print(f"\n=== BLOCK 8: ĐẢM BẢO KÍCH THƯỚC CHUẨN ===")
        if final_video.w != target_w or final_video.h != target_h:
            print(
                f"[WARN] Size mismatch! Expected {target_w}x{target_h}, got {final_video.w}x{final_video.h}"
            )
            print(f"[FIX] Resizing to target size...")
            final_video = CompositeVideoClip(
                [final_video.with_position("center")], size=(target_w, target_h)
            )
            print(f"[OK] Resized: {final_video.w}x{final_video.h}")
        else:
            print(f"[OK] Size matches target: {target_w}x{target_h}")

        # ============================================================
        # BLOCK 9: GẮN AUDIO
        # Mục tiêu: Thêm audio vào video output
        # ============================================================
        print(f"\n=== BLOCK 9: GẮN AUDIO ===")
        final_video = final_video.with_duration(target_duration)
        final_video = final_video.with_audio(audio)
        print(f"[OK] Audio attached. Final duration: {final_video.duration:.2f}s")

        final_debug_path = temp_debug_path / "02_final_with_audio.mp4"
        print(f"[9a] Saving final video to debug: {final_debug_path}")
        if HAS_NVIDIA_GPU:
            final_video.write_videofile(
                str(final_debug_path),
                fps=24,
                codec="h264_nvenc",
                audio_codec="aac",
                remove_temp=True,
                preset="p4",
                bitrate="4000k",
                logger="bar",
            )
        else:
            final_video.write_videofile(
                str(final_debug_path),
                fps=24,
                codec="libx264",
                audio_codec="aac",
                remove_temp=True,
                preset="ultrafast",
                threads=FFMPEG_THREADS,
                bitrate="3000k",
                logger="bar",
            )

        # ============================================================
        # BLOCK 10: EXPORT VIDEO
        # Mục tiêu: Render và lưu file video ra output folder
        # ============================================================
        print(f"\n=== BLOCK 10: EXPORT VIDEO ===")
        output_filename = f"video_{int(time.time())}.mp4"
        output_path = VIDEO_OUT_DIR / output_filename
        print(f"Writing to: {output_path}")
        print(f"[DEBUG] Check temp files at: {temp_debug_path}")

        loop = asyncio.get_event_loop()
        
        if HAS_NVIDIA_GPU:
            await loop.run_in_executor(
                None,
                lambda: final_video.write_videofile(
                    str(output_path),
                    fps=24,
                    codec="h264_nvenc",
                    audio_codec="aac",
                    temp_audiofile=f"temp-audio-{uuid.uuid4()}.m4a",
                    remove_temp=True,
                    preset="p4",
                    bitrate="4000k",
                    logger="bar",
                ),
            )
        else:
            await loop.run_in_executor(
                None,
                lambda: final_video.write_videofile(
                    str(output_path),
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile=f"temp-audio-{uuid.uuid4()}.m4a",
                    remove_temp=True,
                    preset="ultrafast",
                    threads=FFMPEG_THREADS,
                    bitrate="3000k",
                    logger="bar",
                ),
            )

        print(f"\n=== BLOCK 11: HOÀN TẤT ===")
        print(f"[SUCCESS] Video generated: {output_filename}")

        return {"status": "success", "url": f"/video/output/{output_filename}"}

    except Exception as e:
        print(f"\n=== ERROR TRAP ===")
        print(f"CRITICAL ERROR in generate_video: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # ============================================================
        # BLOCK 12: DỌN DẸP TÀI NGUYÊN
        # Mục tiêu: Giải phóng bộ nhớ sau khi xử lý xong
        # ============================================================
        print(f"\n=== BLOCK 12: CLEANUP ===")
        print("Cleaning up resources...")
        print(f"[DEBUG] Temp files saved at: {temp_debug_path}")
        try:
            if final_video:
                final_video.close()
            if one_cycle_video:
                one_cycle_video.close()
            for c in temp_clips:
                try:
                    c.close()
                except:
                    pass
            if "audio" in dir() and audio:
                audio.close()
            print("[OK] Cleanup completed")
        except Exception as e:
            print(f"[WARN] Cleanup error: {e}")


if __name__ == "__main__":
    import uvicorn
    import os

    workers = os.cpu_count() or 4
    print(f"Starting server with {workers} workers...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
