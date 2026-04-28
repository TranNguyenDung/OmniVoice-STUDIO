/**
 * CloneVoice.tsx - Trang ghi âm và quản lý thư viện âm thanh
 * ============================================================
 * Chức năng:
 * - Ghi âm trực tiếp từ microphone (record -> convert to WAV)
 * - Kéo thả audio file vào
 * - Chọn text mẫu để đọc
 * - Lưu audio vào thư viện (folder library_audio/ trên server)
 * - Hiển thị danh sách audio từ API /list_audios
 * 
 * API sử dụng:
 * - GET  /list_audios  : Lấy danh sách audio trong thư viện
 * - POST /upload_audio : Upload audio ghi âm lên server
 */

import React, { useState, useRef, useEffect } from 'react';
import { 
  ArrowLeft, 
  Mic, 
  Upload, 
  FileAudio, 
  X, 
  Play, 
  Pause, 
  Save, 
  FolderOpen,
  Trash2
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

// =============================================================================
// TYPES & INTERFACES
// =============================================================================

/** Interface cho audio item từ API */
interface AudioItem {
  name: string;
  url: string;
  type: string;
  mtime: number;
  metadata?: {
    text?: string;
    instruct?: string;
    ref_text?: string;
    created_at?: string;
    source?: string;
  };
}

/** Danh sách text mẫu để người dùng chọn */
const SAMPLE_TEXTS = [
  "Xin chào, tôi là OmniVoice. Rất vui được gặp bạn.",
  "Hôm nay trời đẹp quá! Bạn có muốn đi dạo không?",
  "Hãy cùng nhau khám phá thế giới âm thanh tuyệt vời.",
  "Con người ta có thể làm được mọi thứ nếu có niềm tin.",
  "Âm nhạc là ngôn ngữ của tâm hồn.",
];

// =============================================================================
// HELPER FUNCTIONS (OUTSIDE COMPONENT)
// =============================================================================

/** Convert WebM blob to WAV blob */
const convertWebmToWav = async (webmBlob: Blob): Promise<Blob> => {
  const arrayBuffer = await webmBlob.arrayBuffer();
  const audioContext = new AudioContext();
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
  
  const wavBuffer = audioBufferToWav(audioBuffer);
  return new Blob([wavBuffer], { type: 'audio/wav' });
};

/** Helper: Convert AudioBuffer to WAV format */
const audioBufferToWav = (buffer: AudioBuffer): ArrayBuffer => {
  const numChannels = buffer.numberOfChannels;
  const sampleRate = buffer.sampleRate;
  const format = 1;
  const bitDepth = 16;
  
  const bytesPerSample = bitDepth / 8;
  const blockAlign = numChannels * bytesPerSample;
  const dataLength = buffer.length * blockAlign;
  const headerLength = 44;
  const totalLength = headerLength + dataLength;
  
  const arrayBuffer = new ArrayBuffer(totalLength);
  const view = new DataView(arrayBuffer);
  
  const writeString = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };
  
  writeString(0, 'RIFF');
  view.setUint32(4, totalLength - 8, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, format, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitDepth, true);
  writeString(36, 'data');
  view.setUint32(40, dataLength, true);
  
  const channelData: Float32Array[] = [];
  for (let i = 0; i < numChannels; i++) {
    channelData.push(buffer.getChannelData(i));
  }
  
  let offset = 44;
  for (let i = 0; i < buffer.length; i++) {
    for (let ch = 0; ch < numChannels; ch++) {
      const sample = Math.max(-1, Math.min(1, channelData[ch][i]));
      const intSample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
      view.setInt16(offset, intSample, true);
      offset += 2;
    }
  }
  
  return arrayBuffer;
};

// =============================================================================
// COMPONENT
// =============================================================================

export default function RecordAudio() {
  const navigate = useNavigate();
  
  // ---------- State: Recording ----------
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');
  
  // ---------- State: Current Audio ----------
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioName, setAudioName] = useState('');
  const [textContent, setTextContent] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  
  // ---------- State: Library ----------
  const [audioLibrary, setAudioLibrary] = useState<AudioItem[]>([]);
  const [currentPlayingId, setCurrentPlayingId] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  
  // ---------- Refs ----------
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // =============================================================================
  // EFFECTS
  // =============================================================================

  useEffect(() => {
    fetchAudioLibrary();
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
      stream.getTracks().forEach(track => track.stop());
      return navigator.mediaDevices.enumerateDevices();
    }).then(devices => {
      const audioInputs = devices.filter(d => d.kind === 'audioinput');
      setAudioDevices(audioInputs);
      if (audioInputs.length > 0) {
        setSelectedDeviceId(audioInputs[0].deviceId);
      }
    }).catch(err => {
      console.error('Error getting audio devices:', err);
    });
  }, []);

  // =============================================================================
  // API FUNCTIONS
  // =============================================================================

  const fetchAudioLibrary = async () => {
    try {
      const response = await fetch('/list_audios');
      const data = await response.json();
      setAudioLibrary(data);
    } catch (err) {
      console.error('Error fetching audio library:', err);
    }
  };

  // =============================================================================
  // AUDIO HANDLING - DRAG & DROP
  // =============================================================================

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type.startsWith('audio/')) {
      const file = files[0];
      const url = URL.createObjectURL(file);
      setAudioUrl(url);
      setAudioName(file.name.replace(/\.[^/.]+$/, ''));
      getAudioDuration(url);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      const url = URL.createObjectURL(file);
      setAudioUrl(url);
      setAudioName(file.name.replace(/\.[^/.]+$/, ''));
      getAudioDuration(url);
    }
  };

  const getAudioDuration = (url: string) => {
    const audio = new Audio(url);
    audio.onloadedmetadata = () => {
      setRecordingTime(Math.floor(audio.duration));
    };
  };

  // =============================================================================
  // AUDIO HANDLING - RECORD
  // =============================================================================

  const startRecording = async () => {
    try {
      const constraints: MediaStreamConstraints = {
        audio: selectedDeviceId 
          ? { deviceId: { exact: selectedDeviceId } }
          : true
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const wavBlob = await convertWebmToWav(blob);
        const url = URL.createObjectURL(wavBlob);
        setAudioUrl(url);
        setAudioName(`Recording ${audioLibrary.length + 1}`);
        getAudioDuration(url);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    } catch (err) {
      console.error('Error accessing microphone:', err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
  };

  // =============================================================================
  // AUDIO HANDLING - SAVE
  // =============================================================================

  const saveAudio = async () => {
    if (!audioUrl || isSaving) return;
    
    const fileName = audioName?.trim() || `Recording ${audioLibrary.length + 1}`;
    const fileNameWithExt = fileName.endsWith('.wav') ? fileName : `${fileName}.wav`;
    
    const isDuplicate = audioLibrary.some(item => item.name === fileNameWithExt);
    if (isDuplicate) {
      setErrorMessage(`Tên file "${fileNameWithExt}" đã tồn tại. Vui lòng đặt tên khác.`);
      return;
    }
    
    setIsSaving(true);
    setErrorMessage('');
    try {
      const response = await fetch(audioUrl);
      const blob = await response.blob();
      
      const formData = new FormData();
      formData.append('file', blob, fileNameWithExt);
      formData.append('text', textContent);
      formData.append('instruct', 'record');
      
      const res = await fetch('/upload_audio', {
        method: 'POST',
        body: formData,
      });
      
      if (res.ok) {
        await fetchAudioLibrary();
      } else {
        console.error('Upload failed:', await res.text());
      }
    } catch (err) {
      console.error('Error saving audio:', err);
    } finally {
      setIsSaving(false);
      setAudioUrl(null);
      setAudioName('');
      setRecordingTime(0);
      setTextContent('');
    }
  };

  const clearAudio = () => {
    setAudioUrl(null);
    setAudioName('');
    setRecordingTime(0);
    setTextContent('');
  };

  // =============================================================================
  // AUDIO HANDLING - LIBRARY
  // =============================================================================

  const selectFromLibrary = (item: AudioItem) => {
    setAudioUrl(item.url);
    setAudioName(item.name.replace('.wav', ''));
    if (item.metadata?.text) {
      setTextContent(item.metadata.text);
    }
  };

  const deleteAudio = async (item: AudioItem, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Xóa "${item.name}"?`)) return;
    
    try {
      const res = await fetch(`/audio/${item.name}`, { method: 'DELETE' });
      if (res.ok) {
        await fetchAudioLibrary();
        if (audioUrl === item.url) {
          clearAudio();
        }
      }
    } catch (err) {
      console.error('Error deleting audio:', err);
    }
  };

  const playAudio = (item?: AudioItem) => {
    if (audioRef.current) {
      if (item) {
        if (currentPlayingId === item.name && isPlaying) {
          audioRef.current.pause();
          setIsPlaying(false);
        } else {
          audioRef.current.src = item.url;
          audioRef.current.play();
          setCurrentPlayingId(item.name);
          setIsPlaying(true);
        }
      } else if (audioUrl) {
        if (isPlaying && currentPlayingId === 'current') {
          audioRef.current.pause();
          setIsPlaying(false);
        } else {
          audioRef.current.src = audioUrl;
          audioRef.current.play();
          setCurrentPlayingId('current');
          setIsPlaying(true);
        }
      }
    }
  };

  // =============================================================================
  // UTILITIES
  // =============================================================================

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (mtime: number): string => {
    return new Date(mtime * 1000).toLocaleDateString('vi-VN');
  };

  // =============================================================================
  // RENDER
  // =============================================================================

  return (
    <div className="min-h-screen bg-orange-50 font-sans text-orange-950 p-6">
      <div className="max-w-7xl mx-auto">
        
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-orange-600 hover:text-orange-800 font-bold mb-8 transition-colors"
        >
          <ArrowLeft size={20} />
          <span>Quay lại</span>
        </button>

        <h1 className="text-4xl font-black text-orange-900 mb-2">Record Audio</h1>
        <p className="text-orange-600/70 font-medium mb-8">
          Ghi âm, kéo thả audio hoặc chọn từ thư viện để lưu lại
        </p>

        <div className="grid lg:grid-cols-3 gap-8">
          
          <div className="lg:col-span-2 space-y-6">
            
            {/* Text Content Input */}
            <div className="bg-white p-6 rounded-3xl border border-orange-100 shadow-xl">
              <h2 className="text-xl font-black text-orange-900 mb-4">Nội dung text</h2>
              <textarea
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                placeholder="Nhập nội dung bạn muốn đọc..."
                className="w-full p-4 bg-orange-50 rounded-2xl border-2 border-orange-100 focus:border-orange-300 focus:outline-none font-medium resize-y min-h-[300px]"
              />
              
              <div className="mt-4">
                <p className="text-sm text-orange-400 mb-2">Text mẫu để đọc:</p>
                <div className="flex flex-wrap gap-2">
                  {SAMPLE_TEXTS.map((text, index) => (
                    <button
                      key={index}
                      onClick={() => setTextContent(text)}
                      className={`text-xs px-3 py-2 rounded-lg transition-all ${
                        textContent === text 
                          ? 'bg-orange-500 text-white' 
                          : 'bg-orange-50 text-orange-600 hover:bg-orange-100'
                      }`}
                    >
                      {text.length > 30 ? text.substring(0, 30) + '...' : text}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Audio Input Section */}
            <div className="bg-white p-6 rounded-3xl border border-orange-100 shadow-xl">
              <h2 className="text-xl font-black text-orange-900 mb-4">Nguồn âm thanh</h2>
              
              {audioUrl ? (
                <div className="space-y-4 mb-4">
                  <div className="flex items-center gap-3 bg-orange-50 p-4 rounded-2xl">
                    <div className="bg-orange-100 p-3 rounded-xl">
                      <FileAudio className="text-orange-500" size={24} />
                    </div>
                    <div className="flex-1">
                      <input
                        type="text"
                        value={audioName}
                        onChange={(e) => { setAudioName(e.target.value); setErrorMessage(''); }}
                        placeholder="Nhập tên audio..."
                        className="w-full bg-transparent font-bold text-orange-900 placeholder-orange-400 focus:outline-none"
                      />
                      <p className="text-xs text-orange-400">Thời lượng: {formatTime(recordingTime)}</p>
                    </div>
                    <button
                      onClick={clearAudio}
                      className="p-2 hover:bg-red-100 rounded-xl transition-colors"
                    >
                      <X className="text-red-400" size={18} />
                    </button>
                  </div>
                  
                  {errorMessage && (
                    <p className="text-sm text-red-500 font-medium">{errorMessage}</p>
                  )}
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => playAudio()}
                      className="flex-1 bg-orange-500 hover:bg-orange-600 text-white py-3 rounded-xl font-bold flex items-center justify-center gap-2 transition-colors"
                    >
                      {isPlaying ? <Pause size={20} /> : <Play size={20} />}
                      Phát thử
                    </button>
                    <button
                      onClick={saveAudio}
                      disabled={!audioUrl || isSaving}
                      className="flex-1 bg-green-500 hover:bg-green-600 disabled:bg-green-300 disabled:cursor-not-allowed text-white py-3 rounded-xl font-bold flex items-center justify-center gap-2 transition-colors"
                    >
                      <Save size={20} />
                      {isSaving ? 'Đang lưu...' : 'Lưu'}
                    </button>
                  </div>
                </div>
              ) : (
                <div
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onClick={() => document.getElementById('fileInput')?.click()}
                  className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer ${
                    isDragging 
                      ? 'border-orange-500 bg-orange-50' 
                      : 'border-orange-200 hover:border-orange-400 hover:bg-orange-50/50'
                  }`}
                >
                  <input
                    id="fileInput"
                    type="file"
                    accept="audio/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <Upload className="mx-auto text-orange-300 mb-3" size={40} />
                  <p className="font-bold text-orange-600">Kéo audio vào đây</p>
                  <p className="text-sm text-orange-400">hoặc nhấn để chọn file</p>
                </div>
              )}

              {audioDevices.length > 0 && (
                <select
                  value={selectedDeviceId}
                  onChange={(e) => setSelectedDeviceId(e.target.value)}
                  className="w-full mt-4 mb-2 p-2 bg-orange-50 rounded-xl border border-orange-200 text-orange-900 font-medium focus:outline-none"
                >
                  {audioDevices.map((device, index) => (
                    <option key={device.deviceId} value={device.deviceId}>
                      {device.label || `Microphone ${index + 1}`}
                    </option>
                  ))}
                </select>
              )}

              <button
                onClick={isRecording ? stopRecording : startRecording}
                className={`w-full py-4 rounded-2xl font-bold flex items-center justify-center gap-3 transition-all ${
                  isRecording 
                    ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse' 
                    : 'bg-orange-100 hover:bg-orange-200 text-orange-600'
                }`}
              >
                <Mic size={24} className={isRecording ? 'text-white' : 'text-orange-500'} />
                {isRecording ? (
                  <>Đang ghi âm... {formatTime(recordingTime)}</>
                ) : (
                  'Ghi âm mới'
                )}
              </button>
            </div>
          </div>

          {/* Right Column - Audio Library */}
          <div className="bg-white p-6 rounded-3xl border border-orange-100 shadow-xl">
            <h2 className="text-xl font-black text-orange-900 mb-4">
              <FolderOpen className="inline mr-2" size={24} />
              Thư viện âm thanh ({audioLibrary.length})
            </h2>
            
            {audioLibrary.length === 0 ? (
              <div className="text-center py-8">
                <FileAudio className="mx-auto text-orange-200 mb-3" size={48} />
                <p className="text-orange-400 font-medium">Chưa có audio nào</p>
                <p className="text-sm text-orange-300">Hãy ghi âm hoặc kéo file vào để lưu</p>
              </div>
            ) : (
              <div className="space-y-3 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 280px)' }}>
                {audioLibrary.map((item) => (
                  <div
                    key={item.name}
                    className={`flex items-center gap-3 p-3 rounded-xl transition-all cursor-pointer ${
                      audioUrl === item.url ? 'bg-orange-200 ring-2 ring-orange-400' : 'bg-orange-50 hover:bg-orange-100'
                    }`}
                    onClick={() => selectFromLibrary(item)}
                  >
                    <button
                      onClick={(e) => { e.stopPropagation(); playAudio(item); }}
                      className="bg-orange-500 hover:bg-orange-600 text-white p-2 rounded-lg transition-colors"
                    >
                      {currentPlayingId === item.name && isPlaying ? <Pause size={16} /> : <Play size={16} />}
                    </button>
                    
                    <div className="flex-1">
                      <p className="font-bold text-orange-900 text-sm truncate">{item.name}</p>
                      <p className="text-xs text-orange-400">
                        {formatDate(item.mtime)}
                      </p>
                    </div>
                    
                    <button
                      onClick={(e) => deleteAudio(item, e)}
                      className="p-2 hover:bg-red-100 rounded-lg transition-colors"
                    >
                      <Trash2 className="text-red-400" size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <audio 
          ref={audioRef} 
          onEnded={() => setIsPlaying(false)}
          className="hidden"
        />
      </div>
    </div>
  );
}