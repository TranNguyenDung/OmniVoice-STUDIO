# OmniVoice STUDIO

Công cụ tạo video tin tức AI với giọng nói tự nhiên sử dụng OmniVoice TTS và MoviePy.

## Yêu cầu

- **Python** 3.10+
- **Node.js** 18+
- **Git** (để pip install omnivoice)
- **RAM** tối thiểu 8GB

## Cài đặt

### 1. Clone repo

```bash
git clone https://github.com/TranNguyenDung/OmniVoice-STUDIO.git
cd OmniVoice-STUDIO
```

### 2. Tạo môi trường ảo (khuyến nghị)

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Cài Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Cài Frontend

```bash
cd frontend
npm install
cd ..
```

## Chạy

**Click đúp** vào `run.bat` — tự động tạo thư mục cần thiết, khởi động Backend (port 8000) và Frontend (port 5173), mở trình duyệt tại `http://localhost:5173`.

## Cấu trúc thư mục

```
OmniVoice-STUDIO/
├── run.bat              # Chạy nhanh (click đúp)
├── run.py               # Cài đặt + chạy backend
├── web_api.py           # API server (FastAPI)
├── tts_engine.py        # Engine TTS (OmniVoice)
├── speech_to_text.py    # STT
├── ai_news_video.py     # Tạo video tin tức
├── requirements.txt     # Python dependencies
├── routers/             # API routers
├── frontend/            # Giao diện Web (React + Vite)
├── input/
├── output/
├── media_uploads/
├── output_videos/
└── library_audio/
```

## Xử lý sự cố

- **Thiếu module**: `pip install -r requirements.txt`
- **GPU**: `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121`
- **ffmpeg**: `pip install imageio-ffmpeg`

## Giấy phép

MIT
