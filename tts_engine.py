"""
OmniVoice TTS Engine
====================
- Load model về local (cache) để không cần load lại mỗi lần
- Tự động kiểm tra update từ HuggingFace Hub
- Backup model cũ khi có version mới
"""

import torch
import torchaudio
from pathlib import Path
from typing import Union, Optional
import os
import shutil
import json
import requests
import time
import numpy

# =============================================================================
# CONFIGURATION
# =============================================================================

MODEL_REPO = "k2-fsa/OmniVoice"           # HuggingFace repo ID
MODEL_CACHE_DIR = Path(__file__).parent / "model"  # Thư mục lưu model
MODEL_VERSION_FILE = MODEL_CACHE_DIR / "version.json"  # File lưu version hiện tại

# =============================================================================
# GLOBAL STATE
# =============================================================================

_model = None                              # Model đã load
_model_version = None                       # Version đang dùng

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def is_valid_audio_file(file_path: Union[str, Path]) -> bool:
    """
    Kiểm tra file audio có hợp lệ không.
    Returns True nếu file có thể đọc được, False nếu lỗi.
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return False
        if file_path.stat().st_size == 0:
            return False
        # Thử đọc file audio
        waveform, sample_rate = torchaudio.load(str(file_path))
        if waveform.numel() == 0:
            return False
        return True
    except Exception as e:
        print(f"Invalid audio file {file_path}: {e}")
        return False


# =============================================================================
# MODEL MANAGEMENT
# =============================================================================

def get_latest_model_version() -> Optional[str]:
    """Kiểm tra version mới nhất của model trên HuggingFace Hub"""
    try:
        # Gọi API để lấy thông tin repo
        url = f"https://huggingface.co/api/models/{MODEL_REPO}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Lấy sha của commit mới nhất (dùng làm version ID)
            return data.get('sha') or data.get('lastModified', '').split('T')[0]
        return None
    except Exception as e:
        print(f"Warning: Cannot check model version: {e}")
        return None


def get_local_model_version() -> Optional[str]:
    """Lấy version model đã lưu locally"""
    if MODEL_VERSION_FILE.exists():
        try:
            with open(MODEL_VERSION_FILE, 'r') as f:
                data = json.load(f)
                return data.get('version')
        except:
            pass
    return None


def save_model_version(version: str):
    """Lưu version hiện tại"""
    MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODEL_VERSION_FILE, 'w') as f:
        json.dump({
            'version': version,
            'updated_at': time.strftime("%Y-%m-%d %H:%M:%S")
        }, f, indent=2)


def backup_model():
    """Backup model cũ trước khi update"""
    backup_dir = MODEL_CACHE_DIR / "backup"
    model_dir = MODEL_CACHE_DIR / "snapshots"  # Thư mục mặc định của HuggingFace
    
    if not model_dir.exists():
        return
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    try:
        # Backup thư mục snapshots
        backup_path = backup_dir / f"model_{timestamp}"
        shutil.copytree(model_dir, backup_path, dirs_exist_ok=True)
        print(f"Backed up old model to: {backup_path}")
        
        # Dọn dẹp các backup cũ (giữ lại 3 bản gần nhất)
        backups = sorted(backup_dir.glob("model_*"), key=lambda x: x.stat().st_mtime, reverse=True)
        for old_backup in backups[3:]:
            shutil.rmtree(old_backup)
            print(f"Removed old backup: {old_backup}")
    except Exception as e:
        print(f"Warning: Cannot backup model: {e}")


def load_model(force_reload: bool = False):
    """
    Load model từ local cache.
    Nếu có version mới trên HuggingFace thì backup model cũ và tải version mới.
    
    Args:
        force_reload: True nếu muốn load lại model (bỏ qua cache)
    """
    global _model, _model_version
    
    # Nếu model đã load và không cần reload thì return
    if _model is not None and not force_reload:
        print(f"Using cached OmniVoice model (version: {_model_version})")
        return _model
    
    print("Loading OmniVoice model...")
    
    # Kiểm tra version mới nhất
    latest_version = get_latest_model_version()
    local_version = get_local_model_version()
    
    print(f"Local version: {local_version}")
    print(f"Latest version: {latest_version}")
    
    # Nếu có version mới thì backup và reload
    if latest_version and latest_version != local_version:
        print(f"⚠️ New model version available! Downloading...")
        backup_model()
    else:
        print(f"✓ Using local model (version: {local_version})")
    
    # Thiết lập device
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    print(f"Device: {device}, dtype: {dtype}")
    
    try:
        # Import và load model
        from omnivoice import OmniVoice
        
        # Load từ cache (sẽ tự động tải về nếu chưa có)
        _model = OmniVoice.from_pretrained(
            MODEL_REPO,
            device_map=device,
            dtype=dtype,
            cache_dir=str(MODEL_CACHE_DIR)  # Cache vào thư mục local
        )
        
        # Lưu version sau khi load thành công
        if latest_version:
            save_model_version(latest_version)
            _model_version = latest_version
        
        print(f"✓ Model loaded successfully!")
        return _model
        
    except Exception as e:
        print(f"Error loading model: {e}")
        # Thử load model cũ từ backup nếu load version mới thất bại
        backup_dir = MODEL_CACHE_DIR / "backup"
        backups = sorted(backup_dir.glob("model_*"), reverse=True)
        if backups:
            print("Trying to load from backup...")
            try:
                from omnivoice import OmniVoice
                backup_path = str(backups[0])
                _model = OmniVoice.from_pretrained(
                    backup_path,
                    device_map=device,
                    dtype=dtype,
                )
                print("✓ Model loaded from backup!")
                return _model
            except Exception as e2:
                print(f"Cannot load from backup: {e2}")
        raise


def get_model(force_reload: bool = False):
    """
    Get model instance (wrapper cho compatibility)
    
    Args:
        force_reload: True để reload model mới
    """
    return load_model(force_reload=force_reload)


# =============================================================================
# TTS GENERATION
# =============================================================================

def generate_tts(
    text: str,
    output_path: Union[str, Path],
    ref_audio: str = None,
    ref_text: str = None,
    instruct: str = None,
    speed: float = 1.0,
    duration: float = None,
    force_reload_model: bool = False
):
    """
    Generates TTS using OmniVoice model.
    Supports:
    - Voice Clone (ref_audio + ref_text)
    - Auto Voice (text only)
    - Voice Design (instruct)
    
    Args:
        text: Text cần chuyển thành audio
        output_path: Đường dẫn lưu file audio output
        ref_audio: Đường dẫn audio mẫu để clone
        ref_text: Text của audio mẫu
        instruct: Hướng dẫn giọng đọc (vd: "giọng nam trẻ")
        speed: Tốc độ đọc (1.0 = bình thường)
        duration: Duration cụ thể (optional)
        force_reload_model: True nếu muốn reload model trước khi generate
    """
    # Load model (re-use cached model)
    model = get_model(force_reload=force_reload_model)
    
    print(f"Generating TTS: {text[:50] if text else 'N/A'}...")
    
    # Tạo thư mục output nếu chưa có
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Chuẩn bị arguments cho generation
    gen_args = {"text": text}
    
    # Xử lý ref_audio (chuyển đường dẫn web thành đường dẫn file local)
    if ref_audio:
        ref_audio = str(ref_audio)
        if ref_audio.startswith("/audio/library_audio/"):
            ref_audio = ref_audio.replace("/audio/library_audio/", "library_audio/")
        elif ref_audio.startswith("audio/library_audio/"):
            ref_audio = ref_audio.replace("audio/library_audio/", "library_audio/")
        elif ref_audio.startswith("/audio/"):
            # Legacy support
            ref_audio = ref_audio.replace("/audio/input/", "library_audio/").replace("/audio/output/", "output/")
        elif ref_audio.startswith("audio/"):
            ref_audio = ref_audio.replace("audio/input/", "library_audio/").replace("audio/output/", "output/")
        
        # Kiểm tra file audio hợp lệ trước khi sử dụng
        if not is_valid_audio_file(ref_audio):
            print(f"Warning: ref_audio file is invalid or empty: {ref_audio}")
            ref_audio = None  # Bỏ qua nếu file không hợp lệ
        else:
            gen_args["ref_audio"] = ref_audio
    
    if ref_text:
        gen_args["ref_text"] = ref_text
    if instruct:
        gen_args["instruct"] = instruct
    if speed != 1.0:
        gen_args["speed"] = speed
    if duration:
        gen_args["duration"] = duration
    
    # Generate audio
    audio = model.generate(**gen_args)
    
    # Xử lý audio output
    audio_data = audio[0] if isinstance(audio, (list, tuple)) else audio
    
    if isinstance(audio_data, torch.Tensor):
        audio_tensor = audio_data.detach().cpu()
    elif hasattr(audio_data, 'numpy'):
        audio_tensor = audio_data.numpy()
        if isinstance(audio_tensor, numpy.ndarray):
            audio_tensor = torch.from_numpy(audio_tensor)
    else:
        audio_tensor = torch.from_numpy(audio_data)
    
    # Save audio (24kHz sample rate)
    print(f"Saving audio to: {output_path}")
    print(f"Audio tensor shape: {audio_tensor.shape if hasattr(audio_tensor, 'shape') else 'N/A'}")
    try:
        import soundfile as sf
        temp_path = str(output_path) + '.tmp'
        sf.write(temp_path, audio_tensor.numpy(), 24000)
        os.replace(temp_path, str(output_path))
    except ImportError:
        print("soundfile not available, using torchaudio")
        torchaudio.save(str(output_path), audio_tensor, 24000)
    except Exception as e:
        print(f"Error saving with soundfile: {e}")
        try:
            torchaudio.save(str(output_path), audio_tensor, 24000)
        except Exception as e2:
            print(f"Error saving with torchaudio: {e2}")
            raise
    
    print(f"Saved audio to: {output_path}")
    return str(output_path)


# =============================================================================
# MAIN (TEST)
# =============================================================================

if __name__ == "__main__":
    # Test call
    generate_tts(
        text="Đây là bài kiểm tra.",
        ref_audio="test_omni.wav",
        ref_text="alo 1, 2, 3, 4, 5, 6, 7, 8, 9, 10",
        output_path="output/test_direct.wav"
    )