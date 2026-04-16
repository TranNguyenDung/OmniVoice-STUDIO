import os
import sys
import json
from pathlib import Path
from datetime import datetime
import argparse
import wave
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

try:
    from moviepy import TextClip, CompositeVideoClip, ColorClip, AudioFileClip
    import moviepy.video.fx as vfx
except Exception:
    from moviepy.editor import TextClip, CompositeVideoClip, ColorClip, AudioFileClip
    import moviepy.video.fx as vfx

from tts_engine import generate_tts

# Cấu hình UTF-8 cho Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def save_voice_metadata(audio_path, instruct, ref_text):
    meta_path = Path(audio_path).with_suffix(".json")
    metadata = {
        "instruct": instruct,
        "ref_text": ref_text,  # FULL TEXT
        "created_at": datetime.now().strftime("%Y%m%d_%H%M%S"),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"Đã lưu metadata giọng nói: {meta_path.name}")


def _clip_set_start(clip, start: float):
    try:
        return clip.with_start(start)
    except Exception:
        return clip.set_start(start)


def _clip_set_duration(clip, duration: float):
    try:
        return clip.with_duration(duration)
    except Exception:
        return clip.set_duration(duration)


def _clip_set_position(clip, position):
    try:
        return clip.with_position(position)
    except Exception:
        return clip.set_position(position)


def _video_set_audio(video, audio_clip):
    try:
        return video.with_audio(audio_clip)
    except Exception:
        return video.set_audio(audio_clip)


def _clip_fadein(clip, duration: float):
    try:
        return clip.fadein(duration)
    except Exception:
        try:
            return clip.fx(vfx.fadein, duration)
        except Exception:
            return clip


def _clip_fadeout(clip, duration: float):
    try:
        return clip.fadeout(duration)
    except Exception:
        try:
            return clip.fx(vfx.fadeout, duration)
        except Exception:
            return clip


def _make_text_clip(
    *,
    text: str,
    font: str,
    font_size: int,
    color: str,
    stroke_color: str,
    stroke_width: int,
    size: Optional[Tuple[int, Optional[int]]] = None,
    method: Optional[str] = None,
):
    kwargs_v2: Dict[str, Any] = {
        "text": text,
        "font": font,
        "font_size": font_size,
        "color": color,
        "stroke_color": stroke_color,
        "stroke_width": stroke_width,
    }
    if size is not None:
        kwargs_v2["size"] = size
    if method is not None:
        kwargs_v2["method"] = method
    try:
        return TextClip(**kwargs_v2)
    except Exception:
        try:
            kwargs_v2_fallback = dict(kwargs_v2)
            kwargs_v2_fallback.pop("size", None)
            kwargs_v2_fallback.pop("method", None)
            return TextClip(**kwargs_v2_fallback)
        except Exception:
            pass
        kwargs_v1: Dict[str, Any] = {
            "txt": text,
            "font": font,
            "fontsize": font_size,
            "color": color,
            "stroke_color": stroke_color,
            "stroke_width": stroke_width,
        }
        if size is not None:
            kwargs_v1["size"] = size
        if method is not None:
            kwargs_v1["method"] = method
        try:
            return TextClip(**kwargs_v1)
        except Exception:
            kwargs_v1_fallback = dict(kwargs_v1)
            kwargs_v1_fallback.pop("size", None)
            kwargs_v1_fallback.pop("method", None)
            try:
                return TextClip(**kwargs_v1_fallback)
            except Exception:
                return TextClip(text)


def _normalize_color(color_value: Any, default: Tuple[int, int, int]) -> Tuple[int, int, int]:
    if isinstance(color_value, (list, tuple)) and len(color_value) == 3:
        try:
            r, g, b = int(color_value[0]), int(color_value[1]), int(color_value[2])
            return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
        except Exception:
            return default
    return default


def _normalize_keywords(keywords: Any, duration: float) -> List[Tuple[str, float, float]]:
    if not isinstance(keywords, list):
        return []
    out: List[Tuple[str, float, float]] = []
    for item in keywords:
        if not isinstance(item, (list, tuple)) or len(item) < 1:
            continue
        kw = str(item[0]).strip()
        if not kw:
            continue
        start = 0.0
        end = 0.0
        if len(item) >= 2:
            try:
                start = float(item[1])
            except Exception:
                start = 0.0
        if len(item) >= 3:
            try:
                end = float(item[2])
            except Exception:
                end = start + 3.0
        else:
            end = start + 3.0
        if end <= start:
            end = start + 3.0
        start = max(0.0, min(duration, start))
        end = max(0.0, min(duration, end))
        if end <= 0.0 or start >= duration:
            continue
        if end - start < 0.15:
            end = min(duration, start + 0.15)
        out.append((kw, start, end))
    return out


def _write_silence_wav(output_path: Union[str, Path], seconds: float, sample_rate: int = 24000):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    seconds = max(0.1, float(seconds))
    n_frames = int(seconds * sample_rate)
    silence = b"\x00\x00" * n_frames
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(silence)


def _generate_audio(
    *,
    text: str,
    audio_path: Union[str, Path],
    instruct: Optional[str],
    ref_audio: Optional[str] = None,
    ref_text: Optional[str] = None,
    speed: float = 1.0,
    duration: Optional[float] = None,
    mock_tts: bool = False,
):
    if mock_tts:
        approx_seconds = max(4.0, min(90.0, len(text) / 12.0))
        _write_silence_wav(audio_path, approx_seconds)
        return str(audio_path)
    return generate_tts(
        text=text,
        output_path=audio_path,
        ref_audio=ref_audio,
        ref_text=ref_text,
        instruct=instruct,
        speed=speed,
        duration=duration,
    )


def create_ai_news_video(
    text: str,
    keywords: Sequence[Sequence[Any]],
    output_video: Union[str, Path],
    background_color: Tuple[int, int, int] = (30, 30, 30),
    instruct: Optional[str] = None,
    *,
    video_resolution: Tuple[int, int] = (1280, 720),
    video_fps: int = 24,
    audio_volume: float = 2.0,
    subtitle_font_size: int = 52,
    keyword_stroke_width: int = 3,
    mock_tts: bool = False,
    ref_audio: Optional[str] = None,
    ref_text: Optional[str] = None,
    speed: float = 1.0,
    duration: Optional[float] = None,
):
    if not text:
        print("Bỏ qua: text rỗng.")
        return

    output_video = str(output_video)
    audio_path = f"output/temp_{Path(output_video).stem}.wav"
    print(f"--- Đang tạo audio cho: {output_video} ---")

    if not instruct:
        instruct = "female, young adult, low pitch"

    _generate_audio(
        text=text,
        audio_path=audio_path,
        instruct=instruct,
        ref_audio=ref_audio,
        ref_text=ref_text,
        speed=speed,
        duration=duration,
        mock_tts=mock_tts,
    )

    # FULL TEXT metadata
    save_voice_metadata(audio_path, instruct, text)

    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
        print(f"Lỗi: File audio không được tạo!")
        return

    audio_clip = AudioFileClip(audio_path)
    try:
        audio_clip = audio_clip.fx(vfx.volumex, audio_volume)
    except Exception:
        pass
    duration = audio_clip.duration

    # Background
    bg_clip = ColorClip(size=video_resolution, color=background_color, duration=duration)

    # Font
    font_path = "C:/Windows/Fonts/segoeuib.ttf"
    if not os.path.exists(font_path):
        font_path = "Arial"

    # Keywords clips NHIỀU HƠN - NO FONT CONFLICT
    text_clips = []
    for kw, start, end in _normalize_keywords(keywords, duration):

        # Adjust font size based on keyword length
        safe_len = max(1, len(kw))
        font_size = max(72, min(120, int(2000 / safe_len)))

        txt = _make_text_clip(
            text=kw,
            font=font_path,
            font_size=font_size,
            color="white",
            stroke_color="black",
            stroke_width=keyword_stroke_width,
        )
        txt = _clip_set_duration(txt, end - start)
        txt = _clip_set_start(txt, start)
        txt = _clip_set_position(txt, "center")
        txt = _clip_fadein(txt, 0.35)
        txt = _clip_fadeout(txt, 0.35)
        text_clips.append(txt)

    subtitle_text = text.replace(". ", ".\n").replace("! ", "!\n").replace("? ", "?\n")
    subtitle_clip = _make_text_clip(
        text=subtitle_text,
        font=font_path,
        font_size=subtitle_font_size,
        color="white",
        stroke_color="black",
        stroke_width=2,
        size=(max(1, video_resolution[0] - 160), max(1, int(video_resolution[1] * 0.35))),
        method="caption",
    )
    subtitle_clip = _clip_set_position(subtitle_clip, ("center", "bottom"))
    subtitle_clip = _clip_set_duration(subtitle_clip, duration)
    subtitle_clip = _clip_fadein(subtitle_clip, 0.8)
    subtitle_clip = _clip_fadeout(subtitle_clip, 0.8)
    text_clips.append(subtitle_clip)

    # Composite
    video = CompositeVideoClip([bg_clip] + text_clips)
    video = _video_set_audio(video, audio_clip)

    # Export
    os.makedirs(os.path.dirname(output_video), exist_ok=True)
    print(f"--- Xuất video: {output_video} ---")

    video.write_videofile(
        output_video,
        fps=video_fps,
        codec="libx264",
        audio_codec="aac",
    )

    video.close()
    audio_clip.close()
    print(f"✅ Hoàn thành: {output_video}")


def process_batch(config_file: Union[str, Path], *, mock_tts: bool = False):
    if not os.path.exists(config_file):
        print(f"Không tìm thấy {config_file}")
        return

    with open(config_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    global_settings = data.get("global_settings", {}) if isinstance(data, dict) else {}
    default_voice = global_settings.get("default_voice") or "female, young adult, low pitch"
    default_bg = _normalize_color(global_settings.get("default_background_color"), (30, 30, 30))
    video_fps = int(global_settings.get("video_fps") or 24)
    res = global_settings.get("video_resolution") or [1280, 720]
    try:
        video_resolution = (int(res[0]), int(res[1]))
    except Exception:
        video_resolution = (1280, 720)

    news_list = data.get("news_list", [])
    print(f"Tìm thấy {len(news_list)} tin tức.")

    for i, news in enumerate(news_list, 1):
        print(f"\n--- Xử lý tin tức {i}/{len(news_list)}: {news.get('id', 'unknown')} ---")
        try:
            text = news.get("text") if isinstance(news, dict) else None
            keywords = (news.get("keywords", []) if isinstance(news, dict) else []) or []
            output_name = (news.get("output_name") if isinstance(news, dict) else None) or "output.mp4"
            bg_color = _normalize_color((news.get("background_color") if isinstance(news, dict) else None), default_bg)
            instruct = (news.get("instruct") if isinstance(news, dict) else None) or default_voice
            ref_audio = (news.get("ref_audio") if isinstance(news, dict) else None) or None
            ref_text = (news.get("ref_text") if isinstance(news, dict) else None) or None
            speed = float((news.get("speed") if isinstance(news, dict) else None) or 1.0)
            clip_duration = news.get("duration") if isinstance(news, dict) else None
            if clip_duration is not None:
                try:
                    clip_duration = float(clip_duration)
                except Exception:
                    clip_duration = None

            output_path = f"output/{output_name}"
            create_ai_news_video(
                text=text,
                keywords=keywords,
                output_video=output_path,
                background_color=bg_color,
                instruct=instruct,
                video_resolution=video_resolution,
                video_fps=video_fps,
                mock_tts=mock_tts,
                ref_audio=ref_audio,
                ref_text=ref_text,
                speed=speed,
                duration=clip_duration,
            )
            print(f"✅ Đã hoàn thành tin tức {i}")
        except Exception as e:
            print(f"❌ Lỗi khi xử lý tin tức {i}: {e}")
            continue


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="news_config.json")
    parser.add_argument("--mock-tts", action="store_true")
    args = parser.parse_args()
    process_batch(args.config, mock_tts=args.mock_tts)
