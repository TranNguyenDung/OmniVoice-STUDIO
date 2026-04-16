import torch
import torchaudio
from pathlib import Path
from typing import Union
import os
import numpy

# To avoid reloading the model every time the function is called
_model = None

def get_model():
    global _model
    if _model is None:
        print("Loading OmniVoice model...")
        from omnivoice import OmniVoice
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        _model = OmniVoice.from_pretrained(
            "k2-fsa/OmniVoice", device_map=device, dtype=dtype
        )
    return _model

def generate_tts(text: str, output_path: Union[str, Path], ref_audio: str = None, ref_text: str = None, instruct: str = None, speed: float = 1.0, duration: float = None):
    """
    Generates TTS using OmniVoice model.
    Supports Voice Clone (with ref_audio), Auto Voice (no ref), or Voice Design (with instruct).
    """
    model = get_model()
    
    print(f"Generating TTS for: {text[:50]}...")
    
    # Create directory if it doesn't exist
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Prepare generation arguments
    gen_args = {"text": text}
    if ref_audio:
        # Nếu ref_audio là đường dẫn từ web (/audio/input/...), cần chuyển thành đường dẫn file hệ thống
        if ref_audio.startswith("/audio/"):
            # Thay /audio/input/ -> input/ và /audio/output/ -> output/
            ref_audio = ref_audio.replace("/audio/input/", "input/").replace("/audio/output/", "output/")
        elif ref_audio.startswith("audio/"):
            ref_audio = ref_audio.replace("audio/input/", "input/").replace("audio/output/", "output/")
        
        gen_args["ref_audio"] = str(ref_audio)
    if ref_text:
        gen_args["ref_text"] = ref_text
    if instruct:
        gen_args["instruct"] = instruct
    
    # Thêm speed và duration nếu mô hình hỗ trợ (OmniVoice thường xử lý qua gen_args)
    # Lưu ý: Một số phiên bản OmniVoice có thể yêu cầu xử lý speed thủ công sau khi gen
    # nhưng chúng ta cứ truyền vào gen_args theo chuẩn mẫu của bạn.
    if speed != 1.0:
        gen_args["speed"] = speed
    if duration:
        gen_args["duration"] = duration
    
    audio = model.generate(**gen_args)
    
    # Handle different audio types
    audio_data = audio[0] if isinstance(audio, (list, tuple)) else audio
    
    if isinstance(audio_data, torch.Tensor):
        audio_tensor = audio_data.detach().cpu()
    elif hasattr(audio_data, 'numpy'):
        audio_tensor = audio_data.numpy()
        if isinstance(audio_tensor, numpy.ndarray):
            audio_tensor = torch.from_numpy(audio_tensor)
    else:
        audio_tensor = torch.from_numpy(audio_data)
    
    # Save with 24000 sample rate - use soundfile as fallback
    try:
        import soundfile as sf
        sf.write(str(output_path), audio_tensor.numpy(), 24000)
    except ImportError:
        torchaudio.save(str(output_path), audio_tensor, 24000)
    print(f"Saved audio to: {output_path}")
    return str(output_path)

if __name__ == "__main__":
    # Test call
    generate_tts(
        text="Đây là bài kiểm tra.",
        ref_audio="test_omni.wav",
        ref_text="alo 1, 2, 3, 4, 5, 6, 7, 8, 9, 10",
        output_path="output/test_direct.wav"
    )
