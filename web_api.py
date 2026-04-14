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
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
MEDIA_DIR = BASE_DIR / "media_uploads"
VIDEO_OUT_DIR = BASE_DIR / "output_videos"
TEMP_DEBUG_DIR = BASE_DIR / "temp_debug"

for d in [INPUT_DIR, OUTPUT_DIR, MEDIA_DIR, VIDEO_OUT_DIR, TEMP_DEBUG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="OmniVoice Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/audio/input", StaticFiles(directory=str(INPUT_DIR)), name="input_audio")
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

    output_path = INPUT_DIR / audio_filename
    meta_path = INPUT_DIR / json_filename

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
            "url": f"/audio/input/{audio_filename}",
            "metadata": metadata,
        }
    except Exception as e:
        print(f"Error generating TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/list_audios")
async def list_audios():
    try:
        files = []
        for f in INPUT_DIR.glob("*.wav"):
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
                    "url": f"/audio/input/{f.name}",
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
       - Scale clip để phủ kín (cover) toàn bộ khung hình.
       - Crop phần trung tâm để khớp chính xác target_w x target_h.
       - Áp dụng Blur theo thông số blur_radius.
       - Áp dụng MultiplyColor theo bg_opacity để làm tối/sáng nền.
    2. Lớp trên (Foreground Layer):
       - Áp dụng motion effect (zoom, pan, kenburns) nếu có (TRƯỚC KHI resize).
       - Scale clip để vừa khít (contain) trong khung hình, giữ nguyên tỷ lệ.
       - Đặt ở giữa (center).
    3. Kết hợp (Composition):
       - Chồng lớp trên lên lớp nền bằng CompositeVideoClip.
    """
    # Áp dụng motion effect TRƯỚC KHI resize (trên ảnh gốc)
    if motion and motion != "none" and motion_params is not None:
        import random

        print(f"    [motion] Applying {motion} effect")

        if motion == "auto":
            # Auto: random chọn 1 trong 3 loại: zoom, pan, hoặc kenburns
            motion_type = random.choice(["zoom", "pan", "kenburns"])

            if motion_type == "zoom":
                # Pure zoom (center, no pan)
                zoom_start = 1.0
                zoom_end = random.uniform(1.2, 1.5)
                clip = clip.with_effects(
                    [
                        KenBurnsEffect(
                            zoom_start=zoom_start,
                            zoom_end=zoom_end,
                            pan_start=(0, 0),
                            pan_end=(0, 0),
                        )
                    ]
                )
                print(f"    [motion] Auto (zoom): {zoom_start:.2f} -> {zoom_end:.2f}")

            elif motion_type == "pan":
                # Pure pan (no zoom)
                direction = random.choice(["left", "right", "up", "down"])
                pan_amount = random.uniform(0.1, 0.2)

                if direction == "left":
                    pan_start = (pan_amount, 0)
                    pan_end = (-pan_amount, 0)
                elif direction == "right":
                    pan_start = (-pan_amount, 0)
                    pan_end = (pan_amount, 0)
                elif direction == "up":
                    pan_start = (0, pan_amount)
                    pan_end = (0, -pan_amount)
                else:  # down
                    pan_start = (0, -pan_amount)
                    pan_end = (0, pan_amount)

                clip = clip.with_effects(
                    [
                        KenBurnsEffect(
                            zoom_start=1.0,
                            zoom_end=1.0,
                            pan_start=pan_start,
                            pan_end=pan_end,
                        )
                    ]
                )
                print(f"    [motion] Auto (pan): {direction} {pan_amount:.2f}")

            else:  # kenburns
                # Ken Burns: zoom + pan
                zoom_start = 1.0
                zoom_end = random.uniform(1.2, 1.4)
                direction = random.choice(["left", "right", "up", "down", "center"])
                pan_amount = random.uniform(0.08, 0.15)

                if direction == "center":
                    pan_start = (0, 0)
                    pan_end = (0, 0)
                elif direction == "left":
                    pan_start = (pan_amount, pan_amount)
                    pan_end = (-pan_amount, -pan_amount)
                elif direction == "right":
                    pan_start = (-pan_amount, -pan_amount)
                    pan_end = (pan_amount, pan_amount)
                elif direction == "up":
                    pan_start = (pan_amount, pan_amount)
                    pan_end = (-pan_amount, -pan_amount)
                else:  # down
                    pan_start = (-pan_amount, -pan_amount)
                    pan_end = (pan_amount, pan_amount)

                clip = clip.with_effects(
                    [
                        KenBurnsEffect(
                            zoom_start=zoom_start,
                            zoom_end=zoom_end,
                            pan_start=pan_start,
                            pan_end=pan_end,
                        )
                    ]
                )
                print(
                    f"    [motion] Auto (kenburns): zoom {zoom_start:.2f}->{zoom_end:.2f}, {direction}"
                )

        elif motion == "zoom":
            zoom_start = motion_params.get("zoom_start", 1.0)
            zoom_end = motion_params.get("zoom_end", 1.4)
            clip = clip.with_effects(
                [
                    KenBurnsEffect(
                        zoom_start=zoom_start,
                        zoom_end=zoom_end,
                        pan_start=(0, 0),
                        pan_end=(0, 0),
                    )
                ]
            )
            print(f"    [motion] Zoom: {zoom_start} -> {zoom_end}")

        elif motion == "pan":
            pan_x_start = motion_params.get("pan_x_start", -0.15)
            pan_x_end = motion_params.get("pan_x_end", 0.15)
            pan_y_start = motion_params.get("pan_y_start", -0.1)
            pan_y_end = motion_params.get("pan_y_end", 0.1)
            clip = clip.with_effects(
                [
                    KenBurnsEffect(
                        zoom_start=1.0,
                        zoom_end=1.0,
                        pan_start=(pan_x_start, pan_y_start),
                        pan_end=(pan_x_end, pan_y_end),
                    )
                ]
            )
            print(
                f"    [motion] Pan: ({pan_x_start},{pan_y_start}) -> ({pan_x_end},{pan_y_end})"
            )

        elif motion == "kenburns":
            zoom_start = motion_params.get("zoom_start", 1.0)
            zoom_end = motion_params.get("zoom_end", 1.5)
            pan_x_start = motion_params.get("pan_x_start", -0.15)
            pan_x_end = motion_params.get("pan_x_end", 0.15)
            pan_y_start = motion_params.get("pan_y_start", -0.1)
            pan_y_end = motion_params.get("pan_y_end", 0.1)
            clip = clip.with_effects(
                [
                    KenBurnsEffect(
                        zoom_start=zoom_start,
                        zoom_end=zoom_end,
                        pan_start=(pan_x_start, pan_y_start),
                        pan_end=(pan_x_end, pan_y_end),
                    )
                ]
            )
            print(f"    [motion] KenBurns: zoom {zoom_start}->{zoom_end}")

    # 1. Tạo lớp nền
    scale_w = target_w / clip.w
    scale_h = target_h / clip.h
    cover_scale = max(scale_w, scale_h)

    bg_clip = clip.resized(cover_scale).cropped(
        x_center=clip.w * cover_scale / 2,
        y_center=clip.h * cover_scale / 2,
        width=target_w,
        height=target_h,
    )

    # Áp dụng Blur và Opacity (Brightness)
    effects = [MultiplyColor(bg_opacity)]
    if blur_radius > 0:
        effects.insert(0, Blur(radius=blur_radius))

    bg_clip = bg_clip.with_effects(effects)

    # 2. Tạo lớp trên (sau khi motion đã được áp dụng)
    contain_scale = min(scale_w, scale_h)
    fg_clip = clip.resized(contain_scale).with_position("center")

    # 3. Chồng lớp
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
        audio_path = INPUT_DIR / audio_filename

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
        # BLOCK 5: XỬ LÝ TỪNG MEDIA FILE -> CLIP
        # Mục tiêu: Load từng media, áp dụng assembly layers (blur + opacity + scale)
        # Output: Mảng clips đã được assemble
        # ============================================================
        print(f"\n=== BLOCK 5: XỬ LÝ TỪNG MEDIA -> CLIP ===")

        for i, m in enumerate(valid_media):
            m_path = MEDIA_DIR / m["filename"]
            print(
                f"\n--- Processing clip {i + 1}/{len(valid_media)}: {m['filename']} ---"
            )

            # Lấy settings cho từng media
            m_duration = m.get("duration", img_duration)
            m_motion = m.get("motion", "none")
            m_motion_params = m.get("motion_params", {})

            print(f"[5a] Loading: {m['filename']}")
            print(f"[5a] Media settings: duration={m_duration}s, motion={m_motion}")

            # 5a. Load clip gốc từ file
            if m["type"] == "image":
                clip = ImageClip(str(m_path)).with_duration(m_duration).with_fps(24)
                print(
                    f"[5a] ImageClip created: {clip.w}x{clip.h}, fps={clip.fps}, duration={clip.duration}s"
                )
            else:
                video_clip = VideoFileClip(str(m_path))
                clip = video_clip
                temp_clips.append(video_clip)
                print(
                    f"[5a] VideoClip loaded (full): {video_clip.w}x{video_clip.h}, duration={video_clip.duration:.2f}s"
                )
            print(f"[5b] Final duration: {clip.duration:.2f}s")

            # 5c. Áp dụng Assembly Layers (Background blur + Foreground contain)
            print(
                f"[5c] Applying assemble_clip_layers (blur={req.blur_radius}, opacity={req.bg_opacity}, motion={m_motion})"
            )
            assembled_clip = assemble_clip_layers(
                clip,
                target_w,
                target_h,
                blur_radius=req.blur_radius,
                bg_opacity=req.bg_opacity,
                motion=m_motion if m["type"] == "image" else None,
                motion_params=m_motion_params if m["type"] == "image" else None,
            )
            print(
                f"[5c] Assembled: {assembled_clip.w}x{assembled_clip.h}, duration={assembled_clip.duration:.2f}s"
            )

            # 5d. Thêm vào mảng clips
            clips.append(assembled_clip)
            temp_clips.append(assembled_clip)
            print(f"[5d] Added to clips array. Total clips now: {len(clips)}")

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
        one_cycle_video.write_videofile(
            str(one_cycle_path), fps=24, codec="libx264", audio=False, remove_temp=True
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
        final_video.write_videofile(
            str(final_debug_path),
            fps=24,
            codec="libx264",
            audio_codec="aac",
            remove_temp=True,
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
        await loop.run_in_executor(
            None,
            lambda: final_video.write_videofile(
                str(output_path),
                fps=24,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=f"temp-audio-{uuid.uuid4()}.m4a",
                remove_temp=True,
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

    uvicorn.run(app, host="0.0.0.0", port=8000)
