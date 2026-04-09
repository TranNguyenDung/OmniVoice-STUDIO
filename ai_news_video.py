import os
import sys
import json
from pathlib import Path
from datetime import datetime
from moviepy import ColorClip, AudioFileClip, TextClip, CompositeVideoClip
import moviepy.video.fx as vfx
from tts_engine import generate_tts

# Cấu hình UTF-8 cho Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def save_voice_metadata(audio_path, instruct, ref_text):
    """
    Lưu file JSON metadata đi kèm với file audio để làm voice mẫu sau này.
    """
    meta_path = Path(audio_path).with_suffix(".json")
    metadata = {
        "instruct": instruct,
        "ref_text": ref_text,
        "created_at": datetime.now().strftime("%Y%m%d_%H%M%S")
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"Đã lưu metadata giọng nói: {meta_path.name}")

def create_ai_news_video(text, keywords, output_video, background_color=(30, 30, 30), instruct=None):
    """
    Tạo video tin tức AI với nền một màu, font chữ đẹp và hiệu ứng chuyển cảnh mượt mà.
    """
    # 1. Tạo Audio từ TTS
    audio_path = f"output/temp_{Path(output_video).stem}.wav"
    print(f"--- Đang tạo audio cho: {output_video} ---")
    
    # Mặc định giọng nữ trẻ, trầm nếu không chỉ định
    if not instruct:
        instruct = "female, young adult, low pitch"
        
    generate_tts(text, audio_path, instruct=instruct)
    
    # Tạo metadata cho giọng nói mới
    save_voice_metadata(audio_path, instruct, text[:100])
    
    # 2. Tải audio và kiểm tra
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
        print(f"Lỗi: File audio không được tạo hoặc quá nhỏ!")
        return

    audio_clip = AudioFileClip(audio_path)
    try:
        audio_clip = audio_clip.with_volume_scaled(2.0)
    except:
        pass
            
    duration = audio_clip.duration
    
    # 3. Tạo nền (Background)
    bg_clip = ColorClip(size=(1280, 720), color=background_color, duration=duration)
    
    # 4. Tạo các TextClip cho Keywords
    text_clips = []
    font_path = "C:/Windows/Fonts/segoeuib.ttf"
    if not os.path.exists(font_path):
        font_path = "Arial"
        
    for kw, start, end in keywords:
        end = min(end, duration)
        if start >= duration: continue
        
        fade_duration = 0.5 
        txt = TextClip(
            text=kw,
            font_size=100, 
            color='white',
            font=font_path,
            duration=end-start,
            stroke_color='black',
            stroke_width=2
        ).with_start(start).with_position('center')
        
        try:
            txt = txt.with_effects([vfx.FadeIn(fade_duration), vfx.FadeOut(fade_duration)])
        except:
            try:
                txt = txt.fadein(fade_duration).fadeout(fade_duration)
            except:
                pass
        
        text_clips.append(txt)
        
    # 5. Ghép nối Video
    video = CompositeVideoClip([bg_clip] + text_clips)
    video = video.with_audio(audio_clip)
    
    # 6. Xuất video
    os.makedirs(os.path.dirname(output_video), exist_ok=True)
    print(f"--- Đang xuất video: {output_video} ---")
    
    video.write_videofile(
        output_video, 
        fps=24, 
        codec="libx264", 
        audio_codec="libmp3lame",
        temp_audiofile=f"output/temp_{Path(output_video).stem}_audio.mp3",
        remove_temp=True
    )
    
    # Dọn dẹp
    audio_clip.close()
    video.close()
    # Để lại file audio và json theo yêu cầu để làm mẫu
    print(f"Hoàn thành: {output_video}\n")

def process_batch(config_file):
    if not os.path.exists(config_file):
        print(f"Không tìm thấy file cấu hình: {config_file}")
        return

    with open(config_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    news_list = data.get("news_list", [])
    print(f"Tìm thấy {len(news_list)} tin tức cần xử lý.")
    
    for news in news_list:
        text = news.get("text")
        keywords = news.get("keywords")
        output_name = news.get("output_name", "output.mp4")
        bg_color = tuple(news.get("background_color", [30, 30, 30]))
        instruct = news.get("instruct")
        
        output_path = f"output/{output_name}"
        create_ai_news_video(text, keywords, output_path, bg_color, instruct=instruct)

if __name__ == "__main__":
    config_path = "news_config.json"
    process_batch(config_path)
