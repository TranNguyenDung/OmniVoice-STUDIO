import json
import sys
import os
from pathlib import Path
from tts_engine import generate_tts

# Fix UTF-8 for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def main():
    print("=== OMNIVOICE TTS BATCH PROCESSOR ===")

    content_file = Path("input/content.json")
    if not content_file.exists():
        return
    try:
        with open(content_file, "r", encoding="utf-8") as f:
            tasks = json.load(f)
    except Exception as e:
        print(f"Lỗi đọc file cấu hình: {e}")
        input("Nhấn Enter để thoát...")
        return

    print(f"Tìm thấy {len(tasks)} tác vụ cần xử lý.")

    for i, task in enumerate(tasks):
        text = task.get("text")
        ref_audio = task.get("ref_audio")
        ref_text = task.get("ref_text")
        instruct = task.get("instruct")
        output_path = task.get("output_path")

        if not text or not output_path:
            print(f"Bỏ qua tác vụ {i+1}: Thiếu text hoặc output_path.")
            continue

        # Tự động nạp Metadata từ file JSON nếu có ref_audio
        if ref_audio:
            ref_path = Path(ref_audio)
            if ref_path.exists():
                meta_path = ref_path.with_suffix(".json")
                if meta_path.exists():
                    try:
                        with open(meta_path, "r", encoding="utf-8") as mf:
                            metadata = json.load(mf)
                            # Ưu tiên lấy từ file JSON nếu task không ghi rõ
                            if not ref_text:
                                ref_text = metadata.get("ref_text")
                            if not instruct:
                                instruct = metadata.get("instruct")
                            print(f"  -> Đã nạp metadata từ: {meta_path.name}")
                    except:
                        pass
            else:
                print(f"Bỏ qua tác vụ {i+1}: Không tìm thấy file mẫu {ref_audio}")
                continue
        print(f"\nref_text: {ref_text}:")
        try:
            print(f"\nĐang xử lý ({i+1}/{len(tasks)}): {text[:50]}...")
            generate_tts(text, output_path, ref_audio=ref_audio, ref_text=ref_text, instruct=instruct)
        except Exception as e:
            print(f"Lỗi tại tác vụ {i+1}: {e}")

    print("\n=== HOÀN THÀNH ===")
    input("Nhấn Enter để kết thúc...")

if __name__ == "__main__":
    main()
