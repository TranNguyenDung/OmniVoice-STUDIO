# OmniVoice STUDIO

Công cụ tạo video tin tức AI với giọng nói tự nhiên sử dụng OmniVoice TTS và MoviePy.

## Tính năng

- Tạo video tin tức tự động từ văn bản
- Hỗ trợ đa ngôn ngữ với OmniVoice
- Tùy chỉnh giọng nói (voice design)
- Overlay từ khóa với hiệu ứng fade
- Xuất video chất lượng cao (1080p, 24fps)

## Cài đặt

### 1. Cài đặt Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Cài đặt GPU (Tùy chọn)
Nếu có GPU NVIDIA, chạy:
```bash
python install_gpu.py
```

## Cách sử dụng

### Tạo Video Tin Tức

1. Chỉnh sửa `news_config.json` với danh sách tin tức:
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

2. Chạy chương trình:
```bash
python ai_news_video.py
```

Video sẽ được tạo trong thư mục `output/`.

### Chế độ API Server
```bash
python web_api.py
```
Server sẽ chạy tại `http://localhost:8000`

### Chạy Frontend
```bash
cd frontend
npm run dev
```

## Cấu trúc thư mục

```
OmniVoice STUDIO/
├── main.py           # Chương trình chính (batch)
├── web_api.py        # API server
├── tts_engine.py     # Engine TTS
├── requirements.txt  # Python dependencies
├── install_gpu.py    # Cài đặt GPU
├── input/            # File input và audio mẫu
├── output/           # File audio đầu ra
└── frontend/         # Giao diện web (React + Vite)
```

## Yêu cầu

- Python 3.10+
- GPU NVIDIA (khuyến nghị để tăng tốc độ)
- Node.js 18+ (cho frontend)