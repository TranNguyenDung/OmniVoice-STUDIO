# OmniVoice STUDIO

Công cụ tạo video tin tức AI với giọng nói tự nhiên sử dụng OmniVoice TTS và MoviePy.

## Tính năng

- Tạo video tin tức tự động từ văn bản
- Hỗ trợ đa ngôn ngữ với OmniVoice
- Ghi âm và quản lý giọng nói (CloneVoice)
- Tùy chỉnh giọng nói (voice design)
- Overlay từ khóa với hiệu ứng fade
- Xuất video chất lượng cao (1080p, 24fps)

## Yêu cầu hệ thống

- **CPU**: Intel Core i5 hoặc tương đương
- **RAM**: Tối thiểu 8GB (khuyến nghị 16GB)
- **GPU**: NVIDIA RTX 20 series trở lên (khuyến nghị để tăng tốc độ)
- **Dung lượng đĩa**: 20GB trở lên
- **Python**: 3.10+
- **Node.js**: 18+ (cho frontend)

---

## Cài đặt chi tiết

### Bước 1: Cài đặt Python

Tải Python 3.10 hoặc cao hơn từ: https://www.python.org/downloads/

**Lưu ý khi cài đặt Python trên Windows:**
- ✓ Tick "Add Python to PATH"
- ✓ Tick "Install pip"

### Bước 2: Cài đặt Git (nếu chưa có)

**Windows:**
- Tải từ: https://git-scm.com/download/win
- Cài đặt với tùy chọn mặc định
- Chọn "Git Bash Here" và "Add to PATH"

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install git
```

**macOS:**
```bash
brew install git
```

### Bước 3: Clone repository

```bash
git clone https://github.com/TranNguyenDung/OmniVoice-STUDIO.git
cd OmniVoice-STUDIO
```

### Bước 4: Cài đặt GPU (NVIDIA CUDA)

#### 4.1. Kiểm tra GPU

Mở Command Prompt hoặc PowerShell, chạy:
```bash
nvidia-smi
```

Nếu hiển thị thông tin GPU => Đã có driver. Nếu không, sang Bước 4.2.

#### 4.2. Cài đặt NVIDIA Driver

**Windows:**
1. Tải driver từ: https://www.nvidia.com/download/index.aspx
2. Chọn GPU phù hợp và tải
3. Cài đặt (restart máy sau khi cài)

**Linux (Ubuntu):**
```bash
sudo apt install nvidia-driver-535
sudo reboot
```

#### 4.3. Cài đặt CUDA Toolkit 12.1

**Windows:**
1. Tải CUDA Toolkit 12.1 từ:
   https://developer.nvidia.com/cuda-12-1-0-download-archive?target_os=Windows&target_arch=x86_64
2. Chọn phiên bản phù hợp (Windows 10/11)
3. Cài đặt với tùy chọn mặc định
4. **QUAN TRỌNG**: Thêm CUDA vào PATH:
   - Mở System Properties → Environment Variables
   - Sửa biến Path, thêm 2 dòng:
     ```
     C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin
     C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\lib\x64
     ```

**Linux (Ubuntu):**
```bash
wget https://developer.download.nvidia.com/compute/cuda/12.1.0/local_installers/cuda_12.1.0_530.30.02_linux.run
sudo sh cuda_12.1.0_530.30.02_linux.run
```

Thêm vào ~/.bashrc:
```bash
export PATH=/usr/local/cuda-12.1/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.1/lib64:$LD_LIBRARY_PATH
```

#### 4.4. Cài đặt cuDNN

1. Tải cuDNN v8.9.7 từ:
   https://developer.nvidia.com/cudnn (cần đăng ký tài khoản NVIDIA)
2. Giải nén file
3. Copy các file vào thư mục CUDA:
   - `cudnn-12.1/bin/` → `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin\`
   - `cudnn-12.1/lib/` → `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\lib\x64\`
   - `cudnn-12.1/include/` → `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\include\`

#### 4.5. Cài đặt PyTorch với CUDA

```bash
pip uninstall torch -y
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**Kiểm tra GPU:**
```bash
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
```

### Bước 5: Cài đặt Python dependencies

```bash
pip install -r requirements.txt
```

**Nếu lỗi, cài từng gói:**
```bash
pip install fastapi uvicorn python-multipart moviepy edgedenoiser websockets huggingface_hub
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Bước 6: Cài đặt Node.js và Frontend

1. Tải Node.js 18+ từ: https://nodejs.org/
2. Cài đặt với tùy chọn mặc định

```bash
cd frontend
npm install
```

---

## Cách sử dụng

### Chế độ Web (khuyến nghị)

**1. Khởi động API Server:**
```bash
python web_api.py
```
Server chạy tại: http://localhost:8000

**2. Khởi động Frontend:**
```bash
cd frontend
npm run dev
```
Mở trình duyệt: http://localhost:5173

### Tạo Video Tin Tức

1. Chỉnh sửa `news_config.json`:
```json
{
  "news_list": [
    {
      "id": "news_001",
      "text": "Nội dung tin tức...",
      "keywords": [["TỪ KHÓA", 0, 5]],
      "output_name": "video.mp4",
      "background_color": [30, 30, 30],
      "instruct": "female, young adult, low pitch"
    }
  ]
}
```

2. Chạy:
```bash
python ai_news_video.py
```

Video tạo ra trong thư mục `output/`.

---

## Xử lý sự cố

### GPU không được nhận diện

```bash
# Kiểm tra CUDA
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

**Nếu False:**
1. Kiểm tra NVIDIA Driver đã cài chưa
2. Kiểm tra CUDA đã thêm vào PATH chưa
3. Thử cài lại PyTorch:
   ```bash
   pip uninstall torch -y
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

### Lỗi "No module named 'torch'"

```bash
pip install torch torchvision torchaudio
```

### Lỗi Out of Memory (OOM)

- Giảm batch_size trong code
- Đóng các ứng dụng khác
- Sử dụng GPU có VRAM cao hơn (ít nhất 8GB)

### Lỗi ffmpeg

```bash
# Windows
pip install imageio-ffmpeg

# Thêm vào PATH:
# C:\Users\YOUR_USER\AppData\Local\Programs\Python\PythonXXX\Lib\site-packages\imageio\modules\
```

---

## Cấu trúc thư mục

```
OmniVoice STUDIO/
├── web_api.py          # API server
├── tts_engine.py      # Engine TTS
├── requirements.txt   # Python dependencies
├── install_gpu.py    # Script cài đặt GPU tự động
├── input/             # File input và audio mẫu
├── output/            # File audio/video đầu ra
├── library_audio/    # Thư viện audio đã ghi âm
└── frontend/         # Giao diện web (React + Vite)
```

---

## Giấy phép

MIT License