import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import { 
  Play, Music, Image as ImageIcon, Video as VideoIcon, 
  Trash2, Plus, ArrowLeft, Loader2, CheckCircle, 
  Download, Film, Sparkles, Volume2, Pause, X,
  ZoomIn, Move, Sparkle, Settings
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

interface AudioItem {
  name: string;
  url: string;
  metadata?: any;
}

const ASPECT_RATIOS = [
  { label: '16:9 Landscape', value: '16:9', icon: '📺' },
  { label: '9:16 Vertical', value: '9:16', icon: '📱' },
  { label: '1:1 Square', value: '1:1', icon: '🟦' },
];

interface MediaItem {
  id: string;
  file: File;
  preview: string;
  type: 'image' | 'video';
  status: 'uploading' | 'ready' | 'error';
  remoteFilename?: string;
  duration?: number;      // Thời gian hiển thị (giây) - chỉ áp dụng cho ảnh
  motion?: 'auto' | 'none' | 'zoom' | 'pan' | 'kenburns';  // Loại chuyển động - chỉ áp dụng cho ảnh
  motionParams?: {
    zoom_start?: number;
    zoom_end?: number;
    pan_x_start?: number;
    pan_x_end?: number;
    pan_y_start?: number;
    pan_y_end?: number;
  };
}

export default function VideoStudio() {
  const navigate = useNavigate();
  const [audios, setAudios] = useState<AudioItem[]>([]);
  const [selectedAudio, setSelectedAudio] = useState<AudioItem | null>(null);
  const [mediaItems, setMediaItems] = useState<MediaItem[]>([]);
  const [selectedRatio, setSelectedRatio] = useState(ASPECT_RATIOS[0]);
  const [blurRadius, setBlurRadius] = useState(20);
  const [bgOpacity, setBgOpacity] = useState(0.7);
  const [isProcessing, setIsProcessing] = useState(false);
  const [resultVideoUrl, setResultVideoUrl] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  
  // Audio Preview Ref
  const [playingUrl, setPlayingUrl] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    // Khởi tạo audio object một lần duy nhất
    audioRef.current = new Audio();
    fetchAudios();
    
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = '';
      }
    };
  }, []);

  const fetchAudios = async () => {
    try {
      const response = await axios.get('/list_audios');
      setAudios(response.data);
    } catch (err) {
      console.error('Failed to fetch audios', err);
    }
  };

  const handleAudioSelect = (audio: AudioItem) => {
    // Luôn chọn audio này làm nhạc nền
    setSelectedAudio(audio);
    
    if (!audioRef.current) return;

    if (playingUrl === audio.url) {
      // Nếu đang phát chính audio này, thì dừng lại
      audioRef.current.pause();
      setPlayingUrl(null);
    } else {
      // Phát audio mới
      audioRef.current.pause();
      audioRef.current.src = audio.url;
      audioRef.current.load(); // Đảm bảo tệp tin được tải lại
      
      const playPromise = audioRef.current.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            setPlayingUrl(audio.url);
          })
          .catch(error => {
            console.error("Playback failed:", error);
            // Một số trình duyệt chặn autoplay, có thể thông báo cho người dùng
          });
      }
      
      audioRef.current.onended = () => setPlayingUrl(null);
    }
  };

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const newItems = acceptedFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      preview: URL.createObjectURL(file),
      type: (file.type.startsWith('video/') ? 'video' : 'image') as 'image' | 'video',
      status: 'uploading' as const,
      motion: 'auto' as const,
      duration: 5
    }));

    setMediaItems(prev => [...prev, ...newItems]);

    // Upload từng file lên backend
    for (const item of newItems) {
      const formData = new FormData();
      formData.append('file', item.file);
      try {
        const response = await axios.post('/upload_media', formData);
        setMediaItems(prev => prev.map(m => 
          m.id === item.id ? { ...m, status: 'ready', remoteFilename: response.data.filename } : m
        ));
      } catch (err) {
        setMediaItems(prev => prev.map(m => 
          m.id === item.id ? { ...m, status: 'error' } : m
        ));
      }
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png'],
      'video/*': ['.mp4', '.mov', '.avi']
    }
  });

  const removeMedia = (id: string) => {
    setMediaItems(prev => prev.filter(item => item.id !== id));
  };

  const handleGenerateVideo = async () => {
    const readyMedia = mediaItems.filter(m => m.status === 'ready');
    if (!selectedAudio || readyMedia.length === 0) return;
    
    setIsProcessing(true);
    setResultVideoUrl(null);
    setProgress(10);

    try {
      const response = await axios.post('/generate_video', {
        audio_url: selectedAudio.url,
        media_files: readyMedia.map(m => ({
          filename: m.remoteFilename,
          type: m.type,
          duration: m.duration || 5,
          motion: m.motion || 'none',
          motion_params: m.motionParams || {}
        })),
        aspect_ratio: selectedRatio.value,
        blur_radius: blurRadius,
        bg_opacity: bgOpacity
      });
      
      setProgress(100);
      setResultVideoUrl(response.data.url);
    } catch (err) {
      console.error('Video generation failed', err);
      alert('Lỗi khi tạo video. Vui lòng kiểm tra lại media và audio.');
    } finally {
      setIsProcessing(false);
    }
  };

  const isReadyToGenerate = selectedAudio && mediaItems.some(m => m.status === 'ready') && !isProcessing;

  return (
    <div className="min-h-screen bg-orange-50 font-sans text-orange-950 p-6">
      <div className="max-w-7xl mx-auto flex flex-col gap-8">
        {/* Header */}
        <header className="flex items-center justify-between bg-white p-6 rounded-[32px] shadow-sm border border-orange-100">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/')} className="p-3 hover:bg-orange-50 rounded-2xl text-orange-600 transition-colors">
              <ArrowLeft size={24} />
            </button>
            <div>
              <h1 className="text-2xl font-black italic">Video <span className="text-orange-500">CREATOR</span></h1>
              <p className="text-[10px] font-bold text-orange-400 uppercase tracking-widest">AI Video Production Suite</p>
            </div>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-600 rounded-full border border-emerald-100">
            <Sparkles size={16} />
            <span className="text-xs font-black uppercase tracking-tighter">Pro Studio Enabled</span>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Section 1: Audio Selection (4 cols) */}
          <section className="lg:col-span-4 bg-white rounded-[40px] border border-orange-100 shadow-xl overflow-hidden flex flex-col h-[700px]">
            <div className="p-8 border-b border-orange-50 bg-orange-50/30">
              <div className="flex items-center gap-3 mb-2">
                <Music className="text-orange-500" size={20} />
                <h2 className="font-black uppercase tracking-widest text-sm">Audio Library</h2>
              </div>
              <p className="text-xs text-orange-400 font-medium">Chọn một bản thu để làm nhạc nền cho video</p>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 space-y-3 scrollbar-hide">
              {audios.map((audio, idx) => (
                <div 
                  key={idx}
                  onClick={() => handleAudioSelect(audio)}
                  className={`p-4 rounded-2xl border-2 transition-all cursor-pointer flex items-center justify-between group ${selectedAudio?.url === audio.url ? 'bg-orange-500 border-orange-600 text-white shadow-lg shadow-orange-200' : 'bg-white border-orange-50 hover:border-orange-200'}`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`p-2.5 rounded-xl transition-all ${playingUrl === audio.url ? 'bg-white text-orange-500 animate-pulse' : (selectedAudio?.url === audio.url ? 'bg-white/20 text-white' : 'bg-orange-50 text-orange-500')}`}>
                      {playingUrl === audio.url ? (
                        <div className="flex items-center gap-0.5 h-4">
                           <motion.div animate={{ height: [4, 12, 4] }} transition={{ repeat: Infinity, duration: 0.5 }} className="w-1 bg-current rounded-full" />
                           <motion.div animate={{ height: [8, 4, 12] }} transition={{ repeat: Infinity, duration: 0.6 }} className="w-1 bg-current rounded-full" />
                           <motion.div animate={{ height: [12, 8, 4] }} transition={{ repeat: Infinity, duration: 0.4 }} className="w-1 bg-current rounded-full" />
                        </div>
                      ) : (
                        <Volume2 size={16} />
                      )}
                    </div>
                    <div className="truncate">
                      <p className={`text-xs font-black truncate ${selectedAudio?.url === audio.url ? 'text-white' : 'text-orange-900'}`}>{audio.name}</p>
                      <p className={`text-[9px] font-bold ${selectedAudio?.url === audio.url ? 'text-orange-100' : 'text-orange-300'}`}>
                        {playingUrl === audio.url ? 'Đang phát thử...' : 'Nhấn để chọn & nghe thử'}
                      </p>
                    </div>
                  </div>
                  <div className={`p-2 rounded-full ${selectedAudio?.url === audio.url ? 'bg-white/20' : 'bg-orange-50 text-orange-300 group-hover:text-orange-500'}`}>
                    {playingUrl === audio.url ? (
                      <Pause size={12} fill="currentColor" />
                    ) : (
                      <Play size={12} fill="currentColor" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Section 2: Media Upload (8 cols) */}
          <section className="lg:col-span-8 flex flex-col gap-6 h-[700px]">
            {/* Dropzone */}
            <div 
              {...getRootProps()} 
              className={`relative flex-1 bg-white rounded-[40px] border-4 border-dashed transition-all flex flex-col items-center justify-center p-12 text-center group cursor-pointer ${isDragActive ? 'border-orange-500 bg-orange-50' : 'border-orange-100 hover:border-orange-300'}`}
            >
              <input {...getInputProps()} />
              <div className="bg-orange-100 p-6 rounded-full mb-6 group-hover:scale-110 transition-transform shadow-lg shadow-orange-100">
                <Plus className="text-orange-500" size={48} />
              </div>
              <h3 className="text-2xl font-black text-orange-900 mb-2">Tải lên Hình ảnh & Video</h3>
              <p className="text-orange-400 font-bold max-w-sm leading-relaxed">
                Kéo thả file vào đây hoặc click để chọn tệp tin từ máy tính của bạn.
              </p>
              <div className="absolute bottom-8 flex gap-6 text-[10px] font-black text-orange-300 uppercase tracking-widest">
                <span className="flex items-center gap-1"><ImageIcon size={14}/> Support PNG/JPG</span>
                <span className="flex items-center gap-1"><VideoIcon size={14}/> Support MP4/AVI</span>
              </div>
            </div>

            {/* Media List */}
            {mediaItems.length > 0 && (
              <div className="bg-white p-6 rounded-[40px] border border-orange-100 shadow-lg overflow-hidden flex flex-col">
                <div className="flex items-center justify-between mb-4 px-2">
                  <h3 className="text-xs font-black uppercase tracking-widest text-orange-600">Media Timeline</h3>
                  <span className="text-[10px] font-bold text-orange-300 uppercase">{mediaItems.length} items added</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 max-h-96 overflow-y-auto pr-2 scrollbar-hide">
                  <AnimatePresence>
                    {mediaItems.map((item) => (
                      <motion.div 
                        key={item.id}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.8 }}
                        className="relative group"
                      >
                        <div className="bg-orange-50/50 p-4 rounded-3xl border-2 border-orange-100 hover:border-orange-200 transition-colors">
                          {/* Preview */}
                          <div className="w-full h-32 rounded-2xl overflow-hidden relative bg-orange-100 mb-3">
                            {item.type === 'video' ? (
                              <video src={item.preview} className="w-full h-full object-cover" muted />
                            ) : (
                              <img src={item.preview} className="w-full h-full object-cover" />
                            )}
                            
                            {/* Overlay status */}
                            {item.status === 'uploading' && (
                              <div className="absolute inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center rounded-2xl">
                                <Loader2 className="animate-spin text-white" size={24} />
                              </div>
                            )}
                            
                            {item.status === 'error' && (
                              <div className="absolute inset-0 bg-red-500/40 backdrop-blur-sm flex items-center justify-center rounded-2xl">
                                <X className="text-white" size={24} />
                              </div>
                            )}
                            
                            <button 
                              onClick={() => removeMedia(item.id)}
                              className="absolute top-2 right-2 p-1.5 bg-red-500 text-white rounded-xl opacity-0 group-hover:opacity-100 transition-opacity shadow-lg"
                            >
                              <Trash2 size={14} />
                            </button>
                            
                            <div className="absolute bottom-2 left-2 px-2 py-1 bg-black/50 backdrop-blur-md rounded-lg flex items-center gap-1">
                              {item.type === 'video' ? <VideoIcon className="text-white" size={10} /> : <ImageIcon className="text-white" size={10} />}
                              <span className="text-[8px] font-bold text-white uppercase tracking-tighter">
                                {item.type === 'video' ? 'Video' : 'Image'}
                              </span>
                            </div>
                          </div>
                          
                          {/* Settings for images */}
                          {item.type === 'image' && item.status === 'ready' && (
                            <div className="space-y-3">
                              {/* Duration */}
                              <div className="flex items-center gap-2">
                                <Settings size={12} className="text-orange-400" />
                                <label className="text-[10px] font-bold text-orange-500 uppercase tracking-wider flex-1">Duration</label>
                                <input
                                  type="number"
                                  min="1"
                                  max="60"
                                  value={item.duration || 5}
                                  onChange={(e) => {
                                    setMediaItems(prev => prev.map(m => 
                                      m.id === item.id ? { ...m, duration: parseFloat(e.target.value) || 5 } : m
                                    ));
                                  }}
                                  className="w-14 px-2 py-1 text-xs font-bold text-orange-700 bg-white border border-orange-200 rounded-lg text-center"
                                />
                                <span className="text-[10px] text-orange-400">sec</span>
                              </div>
                              
                              {/* Motion Type */}
                              <div className="flex items-center gap-2">
                                <Sparkle size={12} className="text-orange-400" />
                                <label className="text-[10px] font-bold text-orange-500 uppercase tracking-wider flex-1">Motion</label>
                                <select
                                  value={item.motion || 'auto'}
                                  onChange={(e) => {
                                    setMediaItems(prev => prev.map(m => 
                                      m.id === item.id ? { ...m, motion: e.target.value as any } : m
                                    ));
                                  }}
                                  className="w-24 px-2 py-1 text-xs font-bold text-orange-700 bg-white border border-orange-200 rounded-lg"
                                >
                                  <option value="auto">Auto</option>
                                  <option value="none">None</option>
                                  <option value="zoom">Zoom</option>
                                  <option value="pan">Pan</option>
                                  <option value="kenburns">Ken Burns</option>
                                </select>
                              </div>
                              
                              {/* Motion Preview Badge */}
                              {item.motion && item.motion !== 'none' && (
                                <div className="flex items-center justify-center gap-1 py-1 bg-orange-100 rounded-lg">
                                  {item.motion === 'auto' && <Sparkle size={10} className="text-orange-500" />}
                                  {item.motion === 'zoom' && <ZoomIn size={10} className="text-orange-500" />}
                                  {item.motion === 'pan' && <Move size={10} className="text-orange-500" />}
                                  {item.motion === 'kenburns' && <Sparkle size={10} className="text-orange-500" />}
                                  <span className="text-[9px] font-bold text-orange-500 uppercase tracking-tighter">
                                    {item.motion === 'auto' ? 'Auto Effect' : item.motion === 'zoom' ? 'Zoom In Effect' : item.motion === 'pan' ? 'Pan Effect' : 'Ken Burns Effect'}
                                  </span>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              </div>
            )}
          </section>
        </div>

        {/* Generate Section */}
        <section className="bg-white p-8 rounded-[48px] border border-orange-100 shadow-2xl flex flex-col gap-8 mb-20">
          <div className="flex flex-col md:flex-row items-center justify-between gap-8">
            <div className="flex-1 w-full">
              <h2 className="text-2xl font-black italic mb-2">Cấu hình & Xuất <span className="text-orange-500">VIDEO</span></h2>
              <p className="text-orange-400 font-bold text-sm">Chọn kích thước video phù hợp với nền tảng bạn muốn đăng tải.</p>
              
              {/* Background Settings Sliders */}
              <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-6 p-6 bg-orange-50/50 rounded-[32px] border border-orange-100">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <label className="text-[10px] font-black uppercase tracking-widest text-orange-600">Độ mờ nền (Blur)</label>
                    <span className="text-xs font-black text-orange-500">{blurRadius}px</span>
                  </div>
                  <input 
                    type="range" min="0" max="100" step="5" 
                    value={blurRadius} onChange={(e) => setBlurRadius(parseInt(e.target.value))}
                    className="w-full h-2 bg-orange-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
                  />
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <label className="text-[10px] font-black uppercase tracking-widest text-orange-600">Độ sáng nền (Opacity)</label>
                    <span className="text-xs font-black text-orange-500">{Math.round(bgOpacity * 100)}%</span>
                  </div>
                  <input 
                    type="range" min="0" max="1" step="0.1" 
                    value={bgOpacity} onChange={(e) => setBgOpacity(parseFloat(e.target.value))}
                    className="w-full h-2 bg-orange-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
                  />
                </div>
              </div>
            </div>

            {/* Aspect Ratio Selector */}
            <div className="flex bg-orange-50 p-2 rounded-3xl border border-orange-100 gap-2">
              {ASPECT_RATIOS.map((ratio) => (
                <button
                  key={ratio.value}
                  onClick={() => setSelectedRatio(ratio)}
                  className={`flex items-center gap-2 px-6 py-3 rounded-2xl font-black text-sm transition-all ${selectedRatio.value === ratio.value ? 'bg-white text-orange-600 shadow-md' : 'text-orange-300 hover:text-orange-500'}`}
                >
                  <span>{ratio.icon}</span>
                  {ratio.label.split(' ')[0]}
                </button>
              ))}
            </div>
          </div>
          
          <div className="h-px bg-orange-50 w-full" />

          <div className="flex flex-col md:flex-row items-center justify-between gap-8">
            <div className="flex items-center gap-4 text-orange-400">
               <div className="p-3 bg-orange-50 rounded-2xl"><Sparkles size={20}/></div>
               <p className="text-xs font-bold leading-relaxed max-w-md">
                 Hệ thống sẽ tự động tạo <span className="text-orange-600">lớp nền mờ (Blurred Background)</span> nếu hình ảnh hoặc video của bạn không khớp với kích thước đã chọn.
               </p>
            </div>

            <div className="w-full md:w-auto flex flex-col items-end gap-4">
              {!resultVideoUrl ? (
                <button
                  onClick={handleGenerateVideo}
                  disabled={!isReadyToGenerate}
                  className={`w-full md:w-80 py-5 rounded-3xl text-xl font-black flex items-center justify-center gap-4 transition-all shadow-xl ${!isReadyToGenerate ? 'bg-orange-100 text-orange-300 cursor-not-allowed' : 'bg-gradient-to-r from-orange-500 to-yellow-400 hover:from-orange-600 hover:to-yellow-500 text-white hover:-translate-y-1 shadow-orange-100'}`}
                >
                  {isProcessing ? (
                    <><Loader2 className="animate-spin" size={24} /> Đang xử lý...</>
                  ) : (
                    <><Film size={24} /> TẠO VIDEO NGAY</>
                  )}
                </button>
              ) : (
                <div className="flex flex-col items-end gap-4 w-full">
                  <div className="flex items-center gap-3 text-emerald-600 font-black uppercase text-sm mb-2">
                     <CheckCircle size={20} /> Video Đã Sẵn Sàng
                  </div>
                  <div className="flex gap-4 w-full">
                    <a 
                      href={resultVideoUrl} 
                      download 
                      className="flex-1 md:w-48 bg-emerald-500 hover:bg-emerald-600 text-white p-5 rounded-3xl font-black flex items-center justify-center gap-3 transition-all shadow-xl shadow-emerald-100"
                    >
                      <Download size={20} /> TẢI XUỐNG
                    </a>
                    <button 
                      onClick={() => setResultVideoUrl(null)}
                      className="bg-orange-50 text-orange-500 p-5 rounded-3xl font-black hover:bg-orange-100 transition-colors"
                    >
                      TẠO MỚI
                    </button>
                  </div>
                </div>
              )}
              
              {isProcessing && (
                <div className="w-full bg-orange-50 h-3 rounded-full overflow-hidden mt-2">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    className="h-full bg-gradient-to-r from-orange-500 to-yellow-400"
                  />
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Video Preview Modal (If result ready) */}
        <AnimatePresence>
          {resultVideoUrl && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 backdrop-blur-xl z-50 flex items-center justify-center p-6"
            >
              <div className="bg-white rounded-[48px] overflow-hidden max-w-4xl w-full shadow-2xl relative">
                <button 
                  onClick={() => setResultVideoUrl(null)}
                  className="absolute top-6 right-6 p-4 bg-black/10 hover:bg-black/20 rounded-full transition-colors z-10"
                >
                  <Plus className="rotate-45" size={24} />
                </button>
                <div className="aspect-video bg-black">
                  <video src={resultVideoUrl} controls autoPlay className="w-full h-full" />
                </div>
                <div className="p-10 flex items-center justify-between">
                  <div>
                    <h3 className="text-2xl font-black mb-1">Preview Video</h3>
                    <p className="text-orange-400 font-bold uppercase text-[10px] tracking-widest">High Definition Export • libx264</p>
                  </div>
                  <a 
                    href={resultVideoUrl} 
                    download 
                    className="bg-orange-500 hover:bg-orange-600 text-white px-10 py-5 rounded-3xl font-black flex items-center gap-3 transition-all"
                  >
                    <Download size={20} /> TẢI VỀ MÁY
                  </a>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
