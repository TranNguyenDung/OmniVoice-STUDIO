import React, { useState, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import {
  Play, Video as VideoIcon, Music,
  Trash2, ArrowLeft, Loader2, CheckCircle,
  Download, Film, Plus, X, Repeat, RefreshCw,
  Globe, Clock, Edit3, Type
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

interface MediaFile {
  id: string;
  file: File;
  preview: string;
  type: 'video' | 'audio';
}

interface AudioItem {
  name: string;
  url: string;
  type: 'input' | 'output';
  metadata?: {
    text?: string;
    created_at?: string;
  };
}

interface OutputVideo {
  name: string;
  url: string;
  size: number;
  mtime: number;
}

interface SRTSegment {
  id: number;
  startTime: string;
  endTime: string;
  startTimeSec: number;
  endTimeSec: number;
  text: string;
}

export default function FFmpegStudio() {
  const navigate = useNavigate();
  const [videoFiles, setVideoFiles] = useState<MediaFile[]>([]);
  const [audioFile, setAudioFile] = useState<MediaFile | null>(null);
  const [audioLibrary, setAudioLibrary] = useState<AudioItem[]>([]);
  const [selectedLibraryAudio, setSelectedLibraryAudio] = useState<AudioItem | null>(null);
  const [useSRT, setUseSRT] = useState<boolean>(false);
  const [isGeneratingSRT, setIsGeneratingSRT] = useState<boolean>(false);
  const [srtProgress, setSrtProgress] = useState<number>(0);
  const [srtUrl, setSrtUrl] = useState<string>('');
  const [srtFilename, setSrtFilename] = useState<string>('');
  const [srtContent, setSrtContent] = useState<string>('');
  const [srtSegments, setSrtSegments] = useState<SRTSegment[]>([]);
  const [srtLanguage, setSrtLanguage] = useState<string>('vi-VN');
  const [isEditingSRT, setIsEditingSRT] = useState<boolean>(false);
  const [isSavingSRT, setIsSavingSRT] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [activeSegmentId, setActiveSegmentId] = useState<number | null>(null);

  const audioRef = useRef<HTMLAudioElement>(null);
  const srtInputRef = useRef<HTMLInputElement>(null);
  const segmentRefs = useRef<{ [key: number]: HTMLDivElement | null }>({});

  const LANGUAGES = [
    { label: 'Tiếng Việt', value: 'vi-VN' },
    { label: 'English', value: 'en-US' },
    { label: '中文 (Chinese)', value: 'zh-CN' },
    { label: '日本語 (Japanese)', value: 'ja-JP' },
    { label: '한국어 (Korean)', value: 'ko-KR' },
    { label: 'Français', value: 'fr-FR' },
  ];

  const [loopCount, setLoopCount] = useState(1);
  const [aspectRatio, setAspectRatio] = useState<'16:9' | '9:16'>('16:9');
  const [fontSize, setFontSize] = useState<number>(24);
  const [subtitleMargin, setSubtitleMargin] = useState<number>(20);
  const [isProcessing, setIsProcessing] = useState(false);
  const [resultVideoUrl, setResultVideoUrl] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [outputVideos, setOutputVideos] = useState<OutputVideo[]>([]);
  const [playingVideo, setPlayingVideo] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const ASPECT_RATIOS = [
    { label: '16:9 Landscape', value: '16:9' as const, icon: '📺' },
    { label: '9:16 Vertical', value: '9:16' as const, icon: '📱' },
  ];

  useEffect(() => {
    fetchOutputVideos();
    fetchAudioLibrary();
    
    return () => {
      videoFiles.forEach(v => URL.revokeObjectURL(v.preview));
      if (audioFile) URL.revokeObjectURL(audioFile.preview);
    };
  }, []);

  // Sync active segment with audio time
  useEffect(() => {
    const active = srtSegments.find(seg => 
      currentTime >= seg.startTimeSec && currentTime <= seg.endTimeSec
    );
    if (active) {
      setActiveSegmentId(active.id);
      // Auto-scroll to active segment
      if (segmentRefs.current[active.id]) {
        segmentRefs.current[active.id]?.scrollIntoView({
          behavior: 'smooth',
          block: 'center'
        });
      }
    } else {
      setActiveSegmentId(null);
    }
  }, [currentTime, srtSegments]);

  const timeToSeconds = (timeStr: string): number => {
    const parts = timeStr.split(':');
    if (parts.length < 3) return 0;
    const h = parseFloat(parts[0]);
    const m = parseFloat(parts[1]);
    const sAndMs = parts[2].split(',');
    const s = parseFloat(sAndMs[0]);
    const ms = sAndMs.length > 1 ? parseFloat(sAndMs[1]) : 0;
    return h * 3600 + m * 60 + s + ms / 1000;
  };

  const parseSRT = (content: string): SRTSegment[] => {
    const segments: SRTSegment[] = [];
    const blocks = content.trim().split(/\n\s*\n/);
    
    blocks.forEach(block => {
      const lines = block.split('\n');
      if (lines.length >= 3) {
        const id = parseInt(lines[0]);
        const timeMatch = lines[1].match(/(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})/);
        if (timeMatch) {
          segments.push({
            id,
            startTime: timeMatch[1],
            endTime: timeMatch[2],
            startTimeSec: timeToSeconds(timeMatch[1]),
            endTimeSec: timeToSeconds(timeMatch[2]),
            text: lines.slice(2).join('\n')
          });
        }
      }
    });
    return segments;
  };

  const stringifySRT = (segments: SRTSegment[]): string => {
    return segments.map(seg => 
      `${seg.id}\n${seg.startTime} --> ${seg.endTime}\n${seg.text}`
    ).join('\n\n');
  };

  const handleImportSRT = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.srt')) {
      alert('Vui lòng chọn file định dạng .srt');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      if (content) {
        setSrtContent(content);
        setSrtSegments(parseSRT(content));
        // Use a safe filename for the server
        const safeName = file.name.replace(/[^a-zA-Z0-9.]/g, '_');
        setSrtFilename(`imported_${Date.now()}_${safeName}`);
        setIsEditingSRT(true);
        setUseSRT(true);
      }
    };
    reader.readAsText(file);
    // Reset input
    e.target.value = '';
  };

  const fetchOutputVideos = async () => {
    try {
      const response = await axios.get('/api/ffmpeg/list_videos');
      setOutputVideos(response.data);
    } catch (err) {
      console.error('Failed to fetch output videos', err);
    }
  };

  const fetchAudioLibrary = async () => {
    try {
      const response = await axios.get('/api/audio/list');
      setAudioLibrary(response.data);
    } catch (err) {
      console.error('Failed to fetch audio library', err);
    }
  };

  const handleGenerateSRT = async () => {
    const taskId = `srt_${Date.now()}`;
    setIsGeneratingSRT(true);
    setSrtProgress(0);
    setSrtUrl('');
    setSrtFilename('');
    setSrtContent('');
    setSrtSegments([]);

    const progressInterval = setInterval(async () => {
      try {
        const res = await axios.get(`/api/ffmpeg/srt_progress/${taskId}`);
        setSrtProgress(res.data.progress);
        if (res.data.progress >= 100) clearInterval(progressInterval);
      } catch (e) {
        console.error("Progress error", e);
      }
    }, 1000);

    try {
      let url = `/api/ffmpeg/generate_srt?language=${srtLanguage}&task_id=${taskId}&`;

      if (selectedLibraryAudio) {
        url += `audio_url=${encodeURIComponent(selectedLibraryAudio.url)}`;
      } else if (audioFile) {
        const formData = new FormData();
        formData.append('audio', audioFile.file);
        const tempResponse = await axios.post('/api/ffmpeg/upload_temp_audio', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        url += `audio_filename=${encodeURIComponent(tempResponse.data.filename)}`;
      } else {
        clearInterval(progressInterval);
        setIsGeneratingSRT(false);
        return;
      }

      const response = await axios.get(url);
      clearInterval(progressInterval);
      setSrtProgress(100);

      if (response.data.srt_url) {
        setSrtUrl(response.data.srt_url);
        setSrtFilename(response.data.filename);
        const content = response.data.srt_content || '';
        setSrtContent(content);
        setSrtSegments(parseSRT(content));
        setIsEditingSRT(true);
        setUseSRT(true);
      }
    } catch (err) {
      clearInterval(progressInterval);
      console.error('Failed to generate SRT', err);
      alert('Lỗi khi tạo file SRT. Vui lòng thử lại.');
    } finally {
      setIsGeneratingSRT(false);
    }
  };

  const handleUpdateSRT = async () => {
    setIsSavingSRT(true);
    try {
      const finalContent = stringifySRT(srtSegments);
      const formData = new FormData();
      formData.append('filename', srtFilename);
      formData.append('content', finalContent);

      await axios.post('/api/ffmpeg/update_srt', formData);
      setSrtContent(finalContent);
      alert('Đã cập nhật file SRT thành công!');
    } catch (err) {
      console.error('Failed to update SRT', err);
      alert('Lỗi khi lưu file SRT.');
    } finally {
      setIsSavingSRT(false);
    }
  };

  const onVideoDrop = (acceptedFiles: File[]) => {
    const newFiles = acceptedFiles
      .filter(file => file.type.startsWith('video/'))
      .map(file => ({
        id: Math.random().toString(36).substr(2, 9),
        file,
        preview: URL.createObjectURL(file),
        type: 'video' as const
      }));
    setVideoFiles(prev => [...prev, ...newFiles]);
  };

  const onAudioDrop = (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file && file.type.startsWith('audio/')) {
      const preview = URL.createObjectURL(file);
      setAudioFile({
        id: Math.random().toString(36).substr(2, 9),
        file,
        preview,
        type: 'audio'
      });
      setSelectedLibraryAudio(null);
    }
  };

  const removeVideo = (id: string) => {
    setVideoFiles(prev => prev.filter(v => v.id !== id));
  };

  const { getRootProps: getVideoProps, getInputProps: getVideoInput } = useDropzone({
    onDrop: onVideoDrop,
    accept: { 'video/*': ['.mp4', '.mov', '.avi'] },
    multiple: true
  });

  const { getRootProps: getAudioProps, getInputProps: getAudioInput } = useDropzone({
    onDrop: onAudioDrop,
    accept: { 'audio/*': ['.mp3', '.wav', '.m4a', '.aac'] },
    maxFiles: 1
  });

  const handleGenerate = async () => {
    if (videoFiles.length === 0 || (!audioFile && !selectedLibraryAudio)) return;

    setIsProcessing(true);
    setResultVideoUrl(null);
    setProgress(10);

    const formData = new FormData();
    videoFiles.forEach(v => formData.append('videos', v.file));

    if (audioFile) {
      formData.append('audio', audioFile.file);
    } else if (selectedLibraryAudio) {
      formData.append('audio_url', selectedLibraryAudio.url);
    }

    if (useSRT) {
      formData.append('include_srt', 'true');
      formData.append('language', srtLanguage);
      if (srtFilename) {
        formData.append('srt_filename', srtFilename);
      }
    }

    formData.append('loop_count', loopCount.toString());
    formData.append('aspect_ratio', aspectRatio);
    formData.append('font_size', fontSize.toString());
    formData.append('subtitle_margin', subtitleMargin.toString());

    try {
      const response = await axios.post('/api/ffmpeg/generate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setProgress(100);
      setResultVideoUrl(response.data.url);
      fetchOutputVideos();
    } catch (err) {
      console.error('FFmpeg generation failed', err);
      alert('Lỗi khi xử lý video bằng FFmpeg. Vui lòng thử lại.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDeleteVideo = async (filename: string) => {
    if (!confirm(`Xóa video "${filename}"?`)) return;
    try {
      await axios.delete(`/api/ffmpeg/delete_video?filename=${encodeURIComponent(filename)}`);
      fetchOutputVideos();
      if (playingVideo?.includes(filename)) {
        setPlayingVideo(null);
      }
    } catch (err) {
      console.error('Failed to delete video', err);
    }
  };

  const handlePlayVideo = (url: string) => {
    setPlayingVideo(url);
    setTimeout(() => {
      if (videoRef.current) {
        videoRef.current.load();
        videoRef.current.play();
      }
    }, 100);
  };

  const seekAudio = (seconds: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = seconds;
      audioRef.current.play();
    }
  };

  const updateSegmentText = (id: number, newText: string) => {
    setSrtSegments(prev => prev.map(seg => 
      seg.id === id ? { ...seg, text: newText } : seg
    ));
  };

  const isReady = videoFiles.length > 0 && (audioFile || selectedLibraryAudio) && !isProcessing;

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="min-h-screen bg-[#fffbeb] text-gray-900 p-6 font-sans">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors font-medium"
          >
            <ArrowLeft size={20} />
            <span>Back</span>
          </button>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-amber-600 to-orange-600 bg-clip-text text-transparent">
            FFmpeg Studio
          </h1>
          <div className="w-20" />
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column - Input */}
          <div className="space-y-6">
            {/* Video Input */}
            <div className="bg-white/70 backdrop-blur rounded-xl p-6 border border-amber-200 shadow-sm">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-amber-900">
                <VideoIcon size={20} />
                Video Input
              </h3>
              <div
                {...getVideoProps()}
                className="border-2 border-dashed border-amber-300 rounded-lg p-8 text-center hover:border-amber-500 hover:bg-amber-50/50 transition-all cursor-pointer"
              >
                <input {...getVideoInput()} />
                <Plus size={40} className="mx-auto mb-2 text-amber-400" />
                <p className="text-amber-700 font-medium">Drop videos here or click to select</p>
              </div>
              {videoFiles.length > 0 && (
                <div className="mt-4 space-y-2">
                  {videoFiles.map(video => (
                    <div key={video.id} className="flex items-center gap-3 bg-amber-50/80 rounded-lg p-2 pr-3 border border-amber-100">
                      <div className="w-16 h-10 bg-black rounded overflow-hidden flex-shrink-0 border border-amber-200">
                        <video 
                          src={video.preview} 
                          className="w-full h-full object-cover"
                          onMouseOver={e => (e.target as HTMLVideoElement).play()}
                          onMouseOut={e => {
                            const v = e.target as HTMLVideoElement;
                            v.pause();
                            v.currentTime = 0;
                          }}
                          muted
                        />
                      </div>
                      <span className="text-xs truncate flex-1 text-gray-700 font-bold">{video.file.name}</span>
                      <button
                        onClick={() => removeVideo(video.id)}
                        className="text-red-500 hover:text-red-700 p-1 flex-shrink-0"
                      >
                        <X size={16} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Audio Input */}
            <div className="bg-white/70 backdrop-blur rounded-xl p-6 border border-amber-200 shadow-sm">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-amber-900">
                <Music size={20} />
                Audio Input
              </h3>

              {/* Dropzone for audio file */}
              <div
                {...getAudioProps()}
                className="border-2 border-dashed border-amber-300 rounded-lg p-6 text-center hover:border-amber-500 hover:bg-amber-50/50 transition-all cursor-pointer mb-4"
              >
                <input {...getAudioInput()} />
                <Plus size={30} className="mx-auto mb-2 text-amber-400" />
                <p className="text-amber-700 font-medium">Drop audio file here or click to select</p>
              </div>

              {audioFile && (
                <div className="flex items-center justify-between bg-amber-50/80 rounded-lg p-3 mb-4 border border-amber-100">
                  <span className="text-sm truncate text-gray-800 font-bold">{audioFile.file.name}</span>
                  <button
                    onClick={() => setAudioFile(null)}
                    className="text-red-500 hover:text-red-700"
                  >
                    <X size={16} />
                  </button>
                </div>
              )}

              {/* Library Audio Selection */}
              <div className="mt-4">
                <h4 className="text-sm font-bold mb-2 text-amber-800">Or select from Library:</h4>
                <div className="max-h-48 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                  {audioLibrary.filter(a => a.type === 'output').map(audio => (
                    <div
                      key={audio.name}
                      onClick={() => {
                        setSelectedLibraryAudio(audio);
                        setAudioFile(null);
                      }}
                      className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-all ${
                        selectedLibraryAudio?.name === audio.name
                          ? 'bg-amber-200 border-amber-400 shadow-sm'
                          : 'bg-white hover:bg-amber-50 border-amber-100'
                      } border`}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm truncate font-bold text-gray-800">{audio.name}</p>
                        {audio.metadata?.text && (
                          <p className="text-xs text-amber-700 truncate">{audio.metadata.text}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* SRT Management Section */}
              <div className="mt-6 p-5 bg-amber-100/40 rounded-xl border border-amber-200">
                <h4 className="text-sm font-bold mb-4 text-amber-900 flex items-center gap-2">
                  <Film size={18} className="text-amber-600" />
                  Subtitle Management (SRT)
                </h4>

                {/* Language Selection */}
                <div className="mb-4">
                  <label className="text-[10px] text-amber-700 mb-1 uppercase font-black px-1 flex items-center gap-1">
                    <Globe size={10} />
                    Audio Language
                  </label>
                  <select
                    value={srtLanguage}
                    onChange={(e) => setSrtLanguage(e.target.value)}
                    className="w-full bg-white text-sm p-2.5 rounded-lg border border-amber-200 focus:border-amber-500 outline-none text-gray-800 shadow-sm font-medium"
                  >
                    {LANGUAGES.map(lang => (
                      <option key={lang.value} value={lang.value}>{lang.label}</option>
                    ))}
                  </select>
                </div>

                {/* Audio Player for verification */}
                {(audioFile || selectedLibraryAudio) && (
                  <div className="mb-4 p-3 bg-white/90 rounded-xl border border-amber-200 shadow-sm">
                    <p className="text-[10px] text-amber-600 mb-1.5 uppercase font-black px-1 flex items-center justify-between">
                      <span>Audio Preview & Verification</span>
                      <span className="font-mono text-amber-500">{currentTime.toFixed(2)}s</span>
                    </p>
                    <audio 
                      ref={audioRef}
                      controls 
                      className="w-full h-10" 
                      src={selectedLibraryAudio ? selectedLibraryAudio.url : audioFile?.preview}
                      onTimeUpdate={(e) => setCurrentTime((e.target as HTMLAudioElement).currentTime)}
                    />
                  </div>
                )}
                
                <div className="grid grid-cols-2 gap-2 mb-2">
                  <button
                    onClick={handleGenerateSRT}
                    disabled={isGeneratingSRT || (!audioFile && !selectedLibraryAudio)}
                    className="flex items-center justify-center gap-2 px-4 py-3.5 bg-amber-600 hover:bg-amber-700 disabled:bg-gray-300 disabled:text-gray-500 rounded-xl transition-all text-xs font-bold shadow-lg shadow-amber-200/50 text-white"
                  >
                    {isGeneratingSRT ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <RefreshCw size={18} />
                    )}
                    Generate SRT
                  </button>

                  <button
                    onClick={() => srtInputRef.current?.click()}
                    disabled={isGeneratingSRT}
                    className="flex items-center justify-center gap-2 px-4 py-3.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 rounded-xl transition-all text-xs font-bold shadow-lg shadow-blue-200/50 text-white"
                  >
                    <Plus size={18} />
                    Import SRT
                  </button>
                  <input
                    type="file"
                    ref={srtInputRef}
                    onChange={handleImportSRT}
                    accept=".srt"
                    className="hidden"
                  />
                </div>

                {/* SRT Progress Bar */}
                {isGeneratingSRT && (
                  <div className="mb-6 mt-2 px-1">
                    <div className="flex justify-between items-center mb-1.5">
                      <span className="text-[10px] font-black text-amber-700 uppercase">Transcription Progress</span>
                      <span className="text-[10px] font-black text-amber-700">{srtProgress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden border border-amber-200 shadow-inner">
                      <motion.div 
                        className="bg-amber-500 h-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${srtProgress}%` }}
                        transition={{ duration: 0.5 }}
                      />
                    </div>
                  </div>
                )}

                <AnimatePresence>
                  {isEditingSRT && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="space-y-4"
                    >
                      <div className="flex items-center justify-between border-t border-amber-200 pt-4">
                        <label className="text-xs font-black text-amber-900 uppercase">Step 2: Review & Edit</label>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] bg-amber-200 text-amber-900 px-2 py-1 rounded-md font-mono border border-amber-300">
                            {srtSegments.length} Segments
                          </span>
                        </div>
                      </div>
                      
                      {/* Structured List Editor */}
                      <div className="h-[400px] overflow-y-auto pr-2 space-y-3 custom-scrollbar">
                        {srtSegments.map((seg) => (
                          <div 
                            key={seg.id}
                            ref={el => segmentRefs.current[seg.id] = el}
                            onClick={() => seekAudio(seg.startTimeSec)}
                            className={`p-3 rounded-xl border transition-all cursor-pointer ${
                              activeSegmentId === seg.id 
                                ? 'bg-amber-500 border-amber-600 shadow-md transform scale-[1.02]' 
                                : 'bg-white border-amber-200 hover:border-amber-400'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                                  activeSegmentId === seg.id ? 'bg-white/20 text-white' : 'bg-amber-100 text-amber-700'
                                }`}>#{seg.id}</span>
                                <div className={`flex items-center gap-1 text-[10px] font-mono ${
                                  activeSegmentId === seg.id ? 'text-white/80' : 'text-gray-500'
                                }`}>
                                  <Clock size={10} />
                                  <span>{seg.startTime}</span>
                                  <span>→</span>
                                  <span>{seg.endTime}</span>
                                </div>
                              </div>
                              {activeSegmentId === seg.id && (
                                <Play size={12} className="text-white fill-white animate-pulse" />
                              )}
                            </div>
                            <div className="relative group" onClick={e => e.stopPropagation()}>
                              <textarea
                                value={seg.text}
                                onChange={(e) => updateSegmentText(seg.id, e.target.value)}
                                rows={2}
                                className={`w-full bg-transparent border-none focus:ring-0 text-sm font-medium resize-none p-0 ${
                                  activeSegmentId === seg.id ? 'text-white' : 'text-gray-800'
                                }`}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                      
                      <button
                        onClick={handleUpdateSRT}
                        disabled={isSavingSRT}
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white rounded-xl transition-all font-bold shadow-lg"
                      >
                        {isSavingSRT ? (
                          <Loader2 size={18} className="animate-spin" />
                        ) : (
                          <CheckCircle size={18} />
                        )}
                        Save & Apply Changes
                      </button>
                      
                      <p className="text-[10px] text-amber-700 text-center italic font-bold">
                        * Changes are saved directly to the server.
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>

                {srtUrl && !isEditingSRT && (
                  <div className="mt-4 flex items-center justify-between p-3 bg-green-50 rounded-xl border border-green-200 shadow-sm">
                    <span className="text-xs text-green-700 font-black flex items-center gap-1">
                      <CheckCircle size={14} /> SUBTITLES READY
                    </span>
                    <button 
                      onClick={() => setIsEditingSRT(true)}
                      className="px-3 py-1 bg-amber-200 text-amber-800 rounded-lg text-xs hover:bg-amber-300 font-black transition-colors"
                    >
                      EDIT NOW
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Column - Settings & Output */}
          <div className="space-y-6">
            {/* Settings */}
            <div className="bg-white/70 backdrop-blur rounded-xl p-6 border border-amber-200 shadow-sm">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-amber-900">
                <Film size={20} />
                Video Settings
              </h3>

              {/* Aspect Ratio */}
              <div className="mb-6">
                <label className="block text-sm font-black mb-3 text-amber-800 uppercase">Aspect Ratio</label>
                <div className="grid grid-cols-2 gap-3">
                  {ASPECT_RATIOS.map(ratio => (
                    <button
                      key={ratio.value}
                      onClick={() => setAspectRatio(ratio.value)}
                      className={`p-4 rounded-xl border transition-all font-bold ${
                        aspectRatio === ratio.value
                          ? 'bg-amber-600 border-amber-700 text-white shadow-lg shadow-amber-200'
                          : 'bg-white border-amber-100 hover:border-amber-300 text-gray-600'
                      }`}
                    >
                      <div className="text-2xl mb-1">{ratio.icon}</div>
                      <div className="text-xs">{ratio.label}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Loop Count */}
              <div className="mb-6">
                <label className="block text-sm font-black mb-3 text-amber-800 uppercase">Video Looping</label>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setLoopCount(Math.max(1, loopCount - 1))}
                    className="w-12 h-12 bg-amber-100 rounded-xl hover:bg-amber-200 text-amber-900 font-black transition-colors flex items-center justify-center text-xl shadow-sm"
                  >
                    -
                  </button>
                  <div className="flex-1 h-12 flex items-center justify-center font-black text-xl text-amber-900 bg-white rounded-xl border border-amber-200 shadow-inner">
                    {loopCount} <span className="text-xs ml-1 text-amber-600 font-bold">times</span>
                  </div>
                  <button
                    onClick={() => setLoopCount(loopCount + 1)}
                    className="w-12 h-12 bg-amber-100 rounded-xl hover:bg-amber-200 text-amber-900 font-black transition-colors flex items-center justify-center text-xl shadow-sm"
                  >
                    +
                  </button>
                </div>
              </div>

              {/* Font Size Selection */}
              <div className="mb-6">
                <label className="block text-sm font-black mb-3 text-amber-800 uppercase flex items-center gap-2">
                  <Type size={16} />
                  Subtitle Font Size
                </label>
                <select
                  value={fontSize}
                  onChange={(e) => setFontSize(parseInt(e.target.value))}
                  className="w-full bg-white text-sm p-3 rounded-xl border border-amber-200 focus:border-amber-500 outline-none text-gray-800 shadow-sm font-bold"
                >
                  {[16, 18, 20, 22, 24, 26, 28, 30, 32, 36, 40, 44, 48, 54, 60].map(size => (
                    <option key={size} value={size}>{size}px {size === 18 ? '(Default)' : ''}</option>
                  ))}
                </select>
              </div>

              {/* Vertical Position Selection */}
              <div className="mb-6">
                <label className="block text-sm font-black mb-3 text-amber-800 uppercase flex items-center gap-2">
                  <Clock size={16} className="rotate-90" />
                  Vertical Position (Bottom Margin)
                </label>
                <select
                  value={subtitleMargin}
                  onChange={(e) => setSubtitleMargin(parseInt(e.target.value))}
                  className="w-full bg-white text-sm p-3 rounded-xl border border-amber-200 focus:border-amber-500 outline-none text-gray-800 shadow-sm font-bold"
                >
                  {[10, 20, 30, 40, 50, 60, 80, 100, 150, 200, 250, 300, 400, 500].map(margin => (
                    <option key={margin} value={margin}>{margin}px {margin === 20 ? '(Default)' : ''}</option>
                  ))}
                </select>
                <p className="text-[10px] text-amber-600 mt-2 italic">Higher value moves subtitles UP from the bottom.</p>
              </div>

              {/* SRT Checkbox */}
              <div className="mb-4">
                <label className="flex items-center gap-4 cursor-pointer p-4 rounded-xl hover:bg-amber-50 border border-transparent hover:border-amber-100 transition-all group">
                  <div className={`w-6 h-6 rounded-md border-2 flex items-center justify-center transition-all ${
                    useSRT ? 'bg-amber-600 border-amber-600' : 'bg-white border-amber-300 group-hover:border-amber-500'
                  }`}>
                    {useSRT && <CheckCircle size={16} className="text-white" />}
                  </div>
                  <input
                    type="checkbox"
                    checked={useSRT}
                    onChange={(e) => setUseSRT(e.target.checked)}
                    disabled={!audioFile && !selectedLibraryAudio}
                    className="hidden"
                  />
                  <div className="flex flex-col">
                    <span className={`text-sm font-black uppercase ${(!audioFile && !selectedLibraryAudio) ? 'text-gray-400' : 'text-amber-900'}`}>
                      Burn Subtitles (SRT)
                    </span>
                    <span className="text-[10px] text-amber-700 font-medium">Add hardcoded subtitles to the video</span>
                  </div>
                </label>
              </div>
            </div>

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={!isReady}
              className="w-full flex items-center justify-center gap-3 px-6 py-5 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700 disabled:from-gray-300 disabled:to-gray-300 rounded-2xl font-black text-xl text-white shadow-xl shadow-amber-200 transition-all transform hover:scale-[1.01] active:scale-95 disabled:scale-100 disabled:shadow-none"
            >
              {isProcessing ? (
                <>
                  <Loader2 size={28} className="animate-spin" />
                  Processing... {progress}%
                </>
              ) : (
                <>
                  <Film size={28} />
                  GENERATE FINAL VIDEO
                </>
              )}
            </button>

            {/* Result Video */}
            {resultVideoUrl && (
              <motion.div 
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-white/90 backdrop-blur rounded-2xl p-6 border-2 border-green-500 shadow-2xl"
              >
                <h3 className="text-lg font-black mb-4 flex items-center gap-2 text-green-700 uppercase italic">
                  <CheckCircle size={24} />
                  Your Video is Ready!
                </h3>
                <div className="relative rounded-xl overflow-hidden border-2 border-green-100 mb-6 bg-black shadow-inner">
                  <video
                    controls
                    src={resultVideoUrl}
                    className="w-full"
                  />
                </div>
                <a
                  href={resultVideoUrl}
                  download
                  className="flex items-center justify-center gap-2 w-full px-4 py-4 bg-green-600 hover:bg-green-700 text-white font-black rounded-xl transition-all shadow-lg active:scale-95"
                >
                  <Download size={24} />
                  DOWNLOAD VIDEO NOW
                </a>
              </motion.div>
            )}

            {/* Output Gallery */}
            <div className="bg-white/70 backdrop-blur rounded-2xl p-6 border border-amber-200 shadow-sm">
              <div className="flex items-center justify-between mb-5">
                <h3 className="text-lg font-black flex items-center gap-2 text-amber-900 uppercase">
                  <Film size={20} />
                  Output Gallery
                </h3>
                <button
                  onClick={fetchOutputVideos}
                  className="bg-amber-100 p-2 text-amber-600 hover:bg-amber-200 rounded-lg transition-colors"
                >
                  <RefreshCw size={20} />
                </button>
              </div>
              <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                {outputVideos.length === 0 ? (
                  <p className="text-amber-600/40 text-sm text-center py-12 italic font-black">No videos created yet</p>
                ) : (
                  outputVideos.map(video => (
                    <div key={video.name} className="flex items-center justify-between bg-white hover:bg-amber-50 rounded-xl p-4 border border-amber-100 shadow-sm transition-all group">
                      <div className="flex-1 min-w-0 mr-4">
                        <p className="text-sm font-black text-gray-800 truncate">{video.name}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-[10px] bg-amber-100 text-amber-700 px-2 py-0.5 rounded font-bold uppercase">{formatSize(video.size)}</span>
                          <span className="text-[10px] text-gray-400 font-medium">MP4 Video</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handlePlayVideo(video.url)}
                          className="p-2.5 text-amber-600 hover:bg-amber-100 rounded-full transition-colors"
                          title="Preview"
                        >
                          <Play size={20} fill="currentColor" />
                        </button>
                        <a
                          href={video.url}
                          download
                          className="p-2.5 text-green-600 hover:bg-green-100 rounded-full transition-colors"
                          title="Download"
                        >
                          <Download size={20} />
                        </a>
                        <button
                          onClick={() => handleDeleteVideo(video.name)}
                          className="p-2.5 text-red-400 hover:bg-red-50 rounded-full transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={20} />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Video Player Modal */}
        <AnimatePresence>
          {playingVideo && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/95 backdrop-blur-md flex items-center justify-center z-50 p-8"
              onClick={() => setPlayingVideo(null)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="relative max-w-5xl w-full flex flex-col items-center"
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  onClick={() => setPlayingVideo(null)}
                  className="absolute -top-14 right-0 text-white hover:text-amber-400 z-10 p-3 bg-white/10 rounded-full transition-all border border-white/20"
                >
                  <X size={28} />
                </button>
                <div className="flex items-center justify-center max-h-[85vh] w-full">
                  <video
                    ref={videoRef}
                    src={playingVideo}
                    controls
                    autoPlay
                    className="max-w-full max-h-[85vh] rounded-2xl shadow-[0_0_50px_rgba(251,191,36,0.3)] border-2 border-white/10"
                  />
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(0, 0, 0, 0.05);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #fbbf24;
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #d97706;
        }
      `}</style>
    </div>
  );
}
