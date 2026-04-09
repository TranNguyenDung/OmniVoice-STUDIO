# OmniVoice STUDIO

Công cụ chuyển văn bản thành giọng nói (TTS) với khả năng clone giọng nói.

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

### 3. Cài đặt Frontend Dependencies
```bash
cd frontend
npm install
```

## Cách sử dụng

### Chế độ Batch (Xử lý nhiều file)

1. Tạo file `input/content.json` với cấu trúc:
```json
[
  {
    "text": "Nội dung cần chuyển thành giọng nói",
    "ref_audio": "input/ten_file_mau.wav",
    "ref_text": "Văn bản của file mẫu",
    "instruct": "Hướng dẫn giọng nói",
    "output_path": "output/ten_file_output.wav"
  }
]
```

2. Chạy chương trình:
```bash
python main.py
```

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