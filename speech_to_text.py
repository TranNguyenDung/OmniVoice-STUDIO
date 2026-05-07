"""
Speech-to-Text module using speech_recognition library (free, uses Google Web Speech API)
Provides word-level timing for SRT subtitle generation
"""

import os
import tempfile
import subprocess
import json
import re
from pathlib import Path
from typing import List, Dict, Optional

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    print("[Speech] speech_recognition not installed. Install with: pip install SpeechRecognition")


def get_audio_duration(audio_path: Path) -> float:
    """Get audio duration using ffprobe"""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "json", str(audio_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except Exception:
        return 0.0


def audio_to_srt(audio_path: Path, language: str = "vi-VN", duration: Optional[float] = None, progress_callback=None) -> Optional[str]:
    """
    High-level function to convert audio to SRT content.
    Tries Vosk first (for timing), then Google Web Speech, then fallback to metadata.
    """
    if duration is None:
        duration = get_audio_duration(audio_path)
        
    print(f"[Speech] Generating SRT for {audio_path.name}...")
    
    # 1. Try with speech module (Vosk or Google)
    words = get_words_with_timing(audio_path, language, progress_callback=progress_callback)
    
    srt_content = None
    if words:
        # Check if we have timing info
        # We check if any segment has end > 0 or start > 0
        has_timing = any(w.get('end', 0) > 0 or w.get('start', 0) > 0 for w in words)
        
        if has_timing:
            # Has timing info (Vosk or chunked Google)
            srt_content = build_srt_from_words(words)
            print(f"[Speech] Generated SRT with timing: {len(words)} segments")
        else:
            # No timing info (Old Google or fallback)
            text = ""
            for w in words:
                text += (w.get('text') or w.get('word', '')) + " "
            
            if text.strip() and duration:
                srt_content = generate_srt_from_text(text, duration)
                print(f"[Speech] Generated SRT from speech recognition (duration-based)")

    # 2. Fallback to metadata if speech recognition failed
    if not srt_content:
        print("[Speech] Speech recognition failed or returned no results. Trying metadata...")
        meta_path = audio_path.with_suffix(".json")
        text = ""
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    text = metadata.get("text") or metadata.get("ref_text") or ""
            except Exception as e:
                print(f"[Speech] Error reading metadata: {e}")
        
        if text and duration:
            srt_content = generate_srt_from_text(text, duration)
            print(f"[Speech] Generated SRT from metadata text (duration-based)")

    return srt_content


def convert_audio_to_wav(audio_path: Path, output_dir: Optional[Path] = None) -> Path:
    """Convert audio to WAV format (LINEAR16, 16kHz, mono) for speech recognition"""
    if output_dir is None:
        output_dir = audio_path.parent
    
    wav_path = output_dir / f"{audio_path.stem}_converted.wav"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(audio_path),
        "-acodec", "pcm_s16le",  # LINEAR16
        "-ar", "16000",         # 16kHz
        "-ac", "1",             # mono
        str(wav_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"[Speech] FFmpeg conversion failed: {result.stderr}")
            return audio_path  # Return original if conversion fails
        print(f"[Speech] Converted audio to {wav_path}")
        return wav_path
    except Exception as e:
        print(f"[Speech] Error converting audio: {e}")
        return audio_path


try:
    from pydub import AudioSegment, silence
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("[Speech] pydub not installed. Install with: pip install pydub")


def transcribe_with_timing(audio_path: Path, language: str = "vi-VN", progress_callback=None) -> List[Dict]:
    """
    Transcribe audio and return words with timing information.
    Uses pydub for silence detection with refined parameters for better accuracy.
    """
    if not SPEECH_RECOGNITION_AVAILABLE:
        print("[Speech] speech_recognition library not available")
        return []
    
    if not PYDUB_AVAILABLE:
        print("[Speech] pydub not available, falling back to fixed chunking...")
        return transcribe_with_fixed_chunks(audio_path, language)

    try:
        # 1. Convert to a standard format first to avoid sample rate/drift issues
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            converted_wav = convert_audio_to_wav(audio_path, tmpdir_path)
            
            # 2. Load the standardized WAV
            audio = AudioSegment.from_wav(str(converted_wav))
            duration_s = len(audio) / 1000.0
            print(f"[Speech] Analyzing audio: {audio_path.name} ({duration_s:.2f}s)")
            
            # 3. Refined silence detection
            # Use a more generous threshold to avoid missing quiet words
            nonsilent_ranges = silence.detect_nonsilent(
                audio, 
                min_silence_len=300, 
                silence_thresh=audio.dBFS - 20 # More sensitive
            )
            
            # 4. Refine ranges and add padding
            max_seg_ms = 4000
            padding_ms = 500 # Add 0.5s padding to prevent clipping
            
            # Split long segments into smaller pieces to avoid timing drift
            refined_ranges = []
            for start, end in nonsilent_ranges:
                if (end - start) <= max_seg_ms:
                    refined_ranges.append((start, end))
                else:
                    curr = start
                    while curr < end:
                        next_end = min(curr + max_seg_ms, end)
                        refined_ranges.append((curr, next_end))
                        curr = next_end
            
            results = []
            r = sr.Recognizer()
            
            # 5. Transcribe each refined segment and treat as a SINGLE subtitle unit
            total_segments = len(refined_ranges)
            for i, (start_ms, end_ms) in enumerate(refined_ranges):
                # Update progress via callback
                if progress_callback:
                    progress_callback(int((i / total_segments) * 100))
                    
                chunk = audio[start_ms:end_ms]
                
                # Add padding for recognition but record original timing
                padded_start = max(0, start_ms - padding_ms)
                padded_end = min(len(audio), end_ms + padding_ms)
                padded_chunk = audio[padded_start:padded_end] + AudioSegment.silent(duration=200)
                
                chunk_path = tmpdir_path / f"chunk_{i}.wav"
                padded_chunk.export(str(chunk_path), format="wav")
                
                with sr.AudioFile(str(chunk_path)) as source:
                    audio_data = r.record(source)
                    try:
                        text = r.recognize_google(audio_data, language=language)
                        if text:
                            # CRITICAL: We treat this ENTIRE detected audio segment as one subtitle
                            # This ensures the timing of the text matches the timing of the sound
                            start_s = start_ms / 1000.0
                            end_s = end_ms / 1000.0
                            
                            results.append({
                                "text": text.strip(),
                                "start": float(start_s),
                                "end": float(end_s)
                            })
                            
                            if i % 5 == 0:
                                print(f"[Speech] Progress: {start_s:.1f}s / {duration_s:.1f}s")
                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError as e:
                        print(f"[Speech] Google request error: {e}")
                        break
            
            # Final progress
            if progress_callback:
                progress_callback(100)
                
            return results
            
    except Exception as e:
        print(f"[Speech] Error with refined transcription: {e}")
        import traceback
        traceback.print_exc()
        return []


def transcribe_with_fixed_chunks(audio_path: Path, language: str = "vi-VN") -> List[Dict]:
    """Fallback method using fixed duration chunks"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            converted_path = convert_audio_to_wav(audio_path, Path(tmpdir))
            r = sr.Recognizer()
            with sr.AudioFile(str(converted_path)) as source:
                duration = source.DURATION
                chunk_duration = 5.0
                results = []
                for start_time in range(0, int(duration), int(chunk_duration)):
                    audio_chunk = r.record(source, duration=chunk_duration)
                    try:
                        text = r.recognize_google(audio_chunk, language=language)
                        if text:
                            end_time = min(start_time + chunk_duration, duration)
                            actual_duration = end_time - start_time
                            words = text.split()
                            time_per_word = actual_duration / len(words)
                            for i, w in enumerate(words):
                                results.append({
                                    "word": w,
                                    "start": float(start_time + (i * time_per_word)),
                                    "end": float(start_time + ((i + 1) * time_per_word))
                                })
                    except: pass
                return results
    except: return []


def transcribe_with_vosk(audio_path: Path, language: str = "vi") -> List[Dict]:
    """
    Alternative: Use Vosk (free, offline) for word-level timing
    Install: pip install vosk
    Download model: https://alphacephei.com/vosk/models (choose vosk-model-small-vi-0.4)
    """
    try:
        from vosk import Model, KaldiRecognizer
        import wave
        
        # Check if model exists
        model_path = Path.home() / ".vosk" / f"vosk-model-{language}"
        if not model_path.exists():
            print(f"[Vosk] Model not found at {model_path}")
            print(f"[Vosk] Download from: https://alphacephei.com/vosk/models")
            return []
        
        # Convert audio to proper format
        with tempfile.TemporaryDirectory() as tmpdir:
            converted_path = convert_audio_to_wav(audio_path, Path(tmpdir))
            
            wf = wave.open(str(converted_path), "rb")
            rec = KaldiRecognizer(Model(str(model_path)), 16000)
            
            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    part_result = json.loads(rec.Result())
                    if 'result' in part_result:
                        for word_info in part_result['result']:
                            results.append({
                                "word": word_info.get('word', ''),
                                "start": word_info.get('start', 0),
                                "end": word_info.get('end', 0),
                            })
            
            part_result = json.loads(rec.FinalResult())
            if 'result' in part_result:
                for word_info in part_result['result']:
                    results.append({
                        "word": word_info.get('word', ''),
                        "start": word_info.get('start', 0),
                        "end": word_info.get('end', 0),
                    })
            
            wf.close()
            print(f"[Vosk] Got {len(results)} words with timing")
            return results
    
    except ImportError:
        print("[Vosk] vosk not installed. Install with: pip install vosk")
        return []
    except Exception as e:
        print(f"[Vosk] Error: {e}")
        import traceback
        traceback.print_exc()
        return []


def build_srt_from_words(segments: list) -> str:
    """
    Build SRT content from audio-aligned segments.
    Each segment is treated as a single atomic subtitle.
    """
    if not segments:
        return ""

    srt_lines = []
    for i, seg in enumerate(segments, 1):
        text = seg.get("text") or seg.get("word") or ""
        if not text:
            continue
            
        start_time = format_srt_time(seg["start"])
        end_time = format_srt_time(seg["end"])

        srt_lines.append(f"{i}")
        srt_lines.append(f"{start_time} --> {end_time}")
        srt_lines.append(text)
        srt_lines.append("")

    return "\n".join(srt_lines)


def generate_srt_from_text(text: str, duration: float, max_chars_per_line: int = 40) -> str:
    """Generate SRT from text using duration (no word-level timing available)"""
    if not text or not duration:
        return ""

    # Clean text
    text = re.sub(r'\s+', ' ', text.strip())

    # Split text into chunks that fit max_chars_per_line
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:
        if current_length + len(word) + 1 <= max_chars_per_line:
            current_chunk.append(word)
            current_length += len(word) + 1
        else:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = len(word)

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    if not chunks:
        return ""

    # Calculate time per chunk
    time_per_chunk = duration / len(chunks)

    # Generate SRT content
    srt_lines = []
    for i, chunk in enumerate(chunks, 1):
        start_time = time_per_chunk * (i - 1)
        end_time = time_per_chunk * i

        start_str = format_srt_time(start_time)
        end_str = format_srt_time(end_time)

        srt_lines.append(f"{i}")
        srt_lines.append(f"{start_str} --> {end_str}")
        srt_lines.append(chunk)
        srt_lines.append("")

    return "\n".join(srt_lines)


def format_srt_time(seconds: float) -> str:
    """Format time in SRT format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def get_words_with_timing(audio_path: Path, language: str = "vi-VN", progress_callback=None) -> List[Dict]:
    """
    Main function to get words with timing
    Tries Vosk first (offline, with timing), then falls back to Google Web Speech (no timing)
    """
    # Try Vosk first (has word-level timing)
    vosk_lang = language.split("-")[0] if "-" in language else language
    words = transcribe_with_vosk(audio_path, vosk_lang)

    if words:
        return words

    # Fall back to Google Web Speech (no timing, will use duration-based SRT)
    print("[Speech] Vosk not available, using Google Web Speech API...")
    words = transcribe_with_timing(audio_path, language, progress_callback=progress_callback)

    return words


def generate_srt_for_audio(audio_path: Path, duration: float, language: str = "vi-VN") -> str:
    """Wrapper for audio_to_srt to maintain backward compatibility"""
    return audio_to_srt(audio_path, language, duration) or ""


if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) > 1:
        audio_file = Path(sys.argv[1])
        if audio_file.exists():
            words = get_words_with_timing(audio_file)
            print(f"\nResult: {len(words)} words")
            for w in words[:10]:
                print(f"  {w}")
        else:
            print(f"File not found: {audio_file}")
    else:
        print("Usage: python speech_to_text.py <audio_file>")
