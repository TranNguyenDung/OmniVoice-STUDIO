import React, { useState, useEffect } from 'react';
import { Play, Download, Mic, Settings, Music, RefreshCw, Volume2, Copy, X, Sparkles, FileJson, ArrowLeft, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface AudioItem {
  name: string;
  url: string;
  type: 'input' | 'output';
  metadata?: {
    text?: string;
    instruct?: string;
    ref_text?: string;
    speed?: number;
    duration?: number;
    created_at?: string;
  };
}

interface Snapshot {
  id: string;
  name: string;
  path: string;
  created_at?: string;
  llm_config?: {
    _name_or_path?: string;
  };
}

const GENDERS = [
  { label: 'Nam (Male)', value: 'male' },
  { label: 'Nữ (Female)', value: 'female' }
];

const AGES = [
  { label: 'Trẻ em (Child)', value: 'child' },
  { label: 'Thiếu niên (Teenager)', value: 'teenager' },
  { label: 'Thanh niên (Young Adult)', value: 'young adult' },
  { label: 'Trung niên (Middle-aged)', value: 'middle-aged' },
  { label: 'Người già (Elderly)', value: 'elderly' }
];

const PITCHES = [
  { label: 'Cực thấp', value: 'very low pitch' },
  { label: 'Thấp', value: 'low pitch' },
  { label: 'Vừa phải', value: 'moderate pitch' },
  { label: 'Cao', value: 'high pitch' },
  { label: 'Cực cao', value: 'very high pitch' }
];

const STYLES = [
  { label: 'Bình thường', value: 'neutral' },
  { label: 'Thì thầm (Whisper)', value: 'whisper' }
];

const ACCENTS = [
  { label: 'None (Auto)', value: '' },
  { label: 'American', value: 'american accent' },
  { label: 'British', value: 'british accent' },
  { label: 'Australian', value: 'australian accent' },
  { label: 'Canadian', value: 'canadian accent' },
  { label: 'Indian', value: 'indian accent' },
  { label: 'Chinese', value: 'chinese accent' },
  { label: 'Korean', value: 'korean accent' },
  { label: 'Japanese', value: 'japanese accent' },
  { label: 'Portuguese', value: 'portuguese accent' },
  { label: 'Russian', value: 'russian accent' }
];

export default function SoundStudio() {
  const navigate = useNavigate();
  const [text, setText] = useState('Chào bạn, đây là giọng nói được tạo mới hoàn toàn, mà không cần file mẫu!');
  const [gender, setGender] = useState(GENDERS[0].value);
  const [age, setAge] = useState(AGES[2].value);
  const [pitch, setPitch] = useState(PITCHES[2].value);
  const [style, setStyle] = useState(STYLES[0].value);
  const [accent, setAccent] = useState(ACCENTS[0].value);
  
  const [refAudio, setRefAudio] = useState<AudioItem | null>(null);
  const [refText, setRefText] = useState('');
  
  const [instruct, setInstruct] = useState('');
  const [recentAudios, setRecentAudios] = useState<AudioItem[]>([]);
  const [currentAudioUrl, setCurrentAudioUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [selectedSnapshot, setSelectedSnapshot] = useState<string | null>(null);

  useEffect(() => {
    const parts = [gender, age, pitch];
    if (style === 'whisper') parts.push('whisper');
    if (accent) parts.push(accent);
    setInstruct(parts.join(', '));
  }, [gender, age, pitch, style, accent]);

  useEffect(() => {
    fetchRecentAudios();
    fetchSnapshots();
  }, []);

  const fetchSnapshots = async () => {
    try {
      const response = await fetch('/list_snapshots');
      if (response.ok) {
        const data = await response.json();
        setSnapshots(data.snapshots || []);
        setSelectedSnapshot(data.current);
      }
    } catch (err) {
      console.error('Failed to fetch snapshots', err);
    }
  };

  const fetchRecentAudios = async () => {
    try {
      const response = await fetch('/list_audios');
      if (response.ok) {
        const data = await response.json();
        setRecentAudios(data);
      }
    } catch (err) {
      console.error('Failed to fetch recent audios', err);
    }
  };

  const handleSelectItem = (audio: AudioItem) => {
    setRefAudio(audio);
    setCurrentAudioUrl(audio.url);
    
    if (audio.metadata) {
      if (audio.metadata.text) setText(audio.metadata.text);
      if (audio.metadata.instruct) setInstruct(audio.metadata.instruct);
      if (audio.metadata.ref_text) setRefText(audio.metadata.ref_text);
    } else {
      setRefText('');
    }
  };

  const handleDeleteAudio = async (e: React.MouseEvent, audio: AudioItem) => {
    e.stopPropagation();
    if (!confirm(`Xoá "${audio.name}"?`)) return;
    
    try {
      const response = await fetch(`/delete_audio?filename=${encodeURIComponent(audio.name)}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        fetchRecentAudios();
      }
    } catch (err) {
      console.error('Failed to delete audio', err);
    }
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
const body = {
        text,
        instruct: refAudio ? '' : instruct,
        ref_audio: refAudio ? refAudio.url : null,
        ref_text: refAudio ? refText : null,
        speed: 1.0,
        snapshot_id: selectedSnapshot
      };

      const response = await fetch('/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Lỗi hệ thống khi tạo âm thanh');
      }
      
      const data = await response.json();
      setCurrentAudioUrl(data.url);
      fetchRecentAudios();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="max-w-screen-2xl mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-8 h-screen overflow-hidden bg-orange-50 text-orange-950 font-sans">
      <div className="lg:col-span-8 flex flex-col gap-6 overflow-y-auto pr-4 scrollbar-hide pb-20">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => navigate('/')}
              className="p-2 hover:bg-orange-200 rounded-full transition-colors text-orange-600 shadow-sm bg-white"
            >
              <ArrowLeft size={24} />
            </button>
            <div className="flex items-center gap-3">
              <div className="bg-orange-500 p-2.5 rounded-xl shadow-lg shadow-orange-200">
                <Mic className="text-white" size={28} />
              </div>
              <h1 className="text-3xl font-black tracking-tight bg-gradient-to-r from-orange-600 to-yellow-500 bg-clip-text text-transparent italic">OmniVoice <span className="text-orange-500 text-2xl font-bold not-italic">STUDIO</span></h1>
            </div>
          </div>
          <div className="px-4 py-1.5 bg-yellow-100 rounded-full border border-yellow-200 flex items-center gap-2">
             <Sparkles className="text-orange-500" size={14} />
             <span className="text-[10px] font-bold text-orange-600 uppercase tracking-widest">Smart Library Active</span>
          </div>
        </header>

        {snapshots.length > 0 && (
          <section className="bg-white p-4 rounded-2xl border-2 border-orange-100 shadow-lg">
            <div className="flex items-center gap-3">
              <label className="text-xs font-bold text-orange-500 uppercase tracking-wider">Model:</label>
              <select
                value={selectedSnapshot || ''}
                onChange={(e) => setSelectedSnapshot(e.target.value)}
                className="flex-1 bg-orange-50 border border-orange-200 rounded-lg px-3 py-2 text-sm text-orange-900 focus:ring-2 focus:ring-orange-300 outline-none"
              >
                {snapshots.map((snap) => (
                  <option key={snap.id} value={snap.id}>
                    {snap.id.slice(0, 8)} {snap.created_at ? `(${snap.created_at})` : ''} - {snap.llm_config?._name_or_path || 'OmniVoice'}
                  </option>
                ))}
              </select>
            </div>
          </section>
        )}

        <section className="bg-white p-6 rounded-[32px] border-2 border-orange-100 shadow-xl">
          <label className="block text-[10px] font-black text-orange-400 uppercase tracking-[0.2em] mb-4">Nội dung văn bản</label>
          <textarea
            className="w-full min-h-[200px] bg-orange-50/30 border border-orange-100 rounded-2xl p-5 text-xl text-orange-900 focus:ring-4 focus:ring-orange-100 focus:border-orange-300 outline-none resize-y transition-all placeholder:text-orange-200"
            placeholder="Nhập nội dung cần chuyển thành giọng nói..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </section>

        {refAudio && (
          <section className="bg-orange-100/50 border-2 border-orange-200 border-dashed p-6 rounded-[32px] animate-in slide-in-from-top-4 duration-300">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Copy className="text-orange-600" size={20} />
                <h2 className="text-sm font-black uppercase tracking-widest text-orange-700">Voice Cloning & Metadata Sync</h2>
              </div>
              <button onClick={() => setRefAudio(null)} className="p-1 hover:bg-orange-200 rounded-full text-orange-600 transition-colors">
                <X size={20} />
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white p-4 rounded-2xl border border-orange-100 relative">
                {refAudio.metadata?.text && <div className="absolute top-2 right-2"><FileJson size={14} className="text-emerald-500" /></div>}
                <p className="text-[10px] font-black text-orange-400 uppercase mb-2">Mẫu đang chọn</p>
                <p className="text-xs font-bold truncate text-orange-800 mb-2">{refAudio.name}</p>
                <audio src={refAudio.url} controls className="h-8 w-full" />
              </div>
              <div>
                <label className="block text-[10px] font-black text-orange-400 uppercase mb-2">Reference Transcript (Auto-loaded if available)</label>
                <textarea
                  className="w-full h-20 bg-white border border-orange-100 rounded-xl p-3 text-xs text-orange-900 outline-none focus:ring-4 focus:ring-orange-500/10 focus:border-orange-300"
                  placeholder="Nhập nội dung có trong file mẫu..."
                  value={refText}
                  onChange={(e) => setRefText(e.target.value)}
                />
              </div>
            </div>
          </section>
        )}

        <section className="bg-white p-8 rounded-[32px] border border-orange-100 shadow-lg">
          <div className="flex flex-col gap-8">
            {/* Giới tính & Độ tuổi */}
            <div className="flex flex-col md:flex-row md:items-center gap-4 md:gap-8">
              <label className="md:w-48 shrink-0 text-[10px] font-black text-orange-300 uppercase tracking-widest mb-0">Giới tính & Độ tuổi</label>
              <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
                <select value={gender} onChange={(e) => setGender(e.target.value)} className="bg-orange-50 border border-orange-100 rounded-xl p-3 text-[13px] font-bold text-orange-800 outline-none w-full hover:border-orange-400 transition-colors cursor-pointer">
                  {GENDERS.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
                </select>
                <select value={age} onChange={(e) => setAge(e.target.value)} className="bg-orange-50 border border-orange-100 rounded-xl p-3 text-[13px] font-bold text-orange-800 outline-none w-full hover:border-orange-400 transition-colors cursor-pointer">
                  {AGES.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
                </select>
              </div>
            </div>

            {/* Giọng (Accent) */}
            <div className="flex flex-col md:flex-row md:items-center gap-4 md:gap-8">
              <label className="md:w-48 shrink-0 text-[10px] font-black text-orange-300 uppercase tracking-widest mb-0">Giọng (Accent)</label>
              <div className="flex-1">
                <select value={accent} onChange={(e) => setAccent(e.target.value)} className="w-full bg-orange-50 border border-orange-100 rounded-xl p-3 text-[13px] font-bold text-orange-800 outline-none hover:border-orange-400 transition-colors cursor-pointer">
                  {ACCENTS.map(acc => <option key={acc.value} value={acc.value}>{acc.label}</option>)}
                </select>
              </div>
            </div>

            {/* Cao độ & Phong cách */}
            <div className="flex flex-col md:flex-row md:items-center gap-4 md:gap-8">
              <label className="md:w-48 shrink-0 text-[10px] font-black text-orange-300 uppercase tracking-widest mb-0">Cao độ & Phong cách</label>
              <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
                <select value={pitch} onChange={(e) => setPitch(e.target.value)} className="bg-orange-50 border border-orange-100 rounded-xl p-3 text-[13px] font-bold text-orange-800 outline-none w-full hover:border-orange-400 transition-colors cursor-pointer">
                  {PITCHES.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
                </select>
                <select value={style} onChange={(e) => setStyle(e.target.value)} className="bg-orange-50 border border-orange-100 rounded-xl p-3 text-[13px] font-bold text-orange-800 outline-none w-full hover:border-orange-400 transition-colors cursor-pointer">
                  {STYLES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </div>
            </div>
          </div>
          <div className="mt-8 pt-6 border-t border-orange-50">
             <div className="bg-orange-50 p-4 rounded-2xl border border-orange-100 flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <span className="text-[9px] font-black text-orange-400 uppercase block mb-1">Instruct Preview</span>
                  <textarea 
                    value={instruct} 
                    onChange={(e) => setInstruct(e.target.value)} 
                    rows={2}
                    className="w-full bg-transparent text-xs text-orange-600 font-bold italic outline-none resize-none" 
                  />
                </div>
                <Settings size={16} className="text-orange-200 shrink-0 mt-1" />
              </div>
          </div>
        </section>

        <button
          onClick={handleGenerate}
          disabled={isGenerating || !text}
          className={`w-full py-6 rounded-[32px] text-2xl font-black flex items-center justify-center gap-4 shadow-2xl transition-all active:scale-[0.98] ${isGenerating ? 'bg-orange-200 text-orange-400 cursor-not-allowed' : 'bg-gradient-to-r from-orange-500 to-yellow-400 hover:from-orange-600 hover:to-yellow-500 text-white shadow-orange-200 hover:-translate-y-1'}`}
        >
          {isGenerating ? <><RefreshCw className="animate-spin" size={32} /> ĐANG TẠO MẪU...</> : <><Play size={32} fill="currentColor" /> TẠO AUDIO MỚI</>}
        </button>

        {error && <div className="bg-red-50 border-2 border-red-100 text-red-600 p-6 rounded-3xl text-xs font-bold animate-shake">{error}</div>}

        {currentAudioUrl && (
          <div className="bg-white border-2 border-orange-200 p-8 rounded-[40px] animate-in zoom-in duration-500 shadow-2xl flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black text-orange-500 uppercase tracking-widest flex items-center gap-2"><Volume2 size={18}/> Audio Ready</span>
              <a href={currentAudioUrl} download className="p-3 bg-orange-500 rounded-2xl hover:bg-orange-600 text-white shadow-lg shadow-orange-200 transition-all hover:scale-110"><Download size={24} /></a>
            </div>
            <audio controls src={currentAudioUrl} autoPlay className="w-full h-12" />
          </div>
        )}
      </div>

      <div className="lg:col-span-4 bg-yellow-400/10 backdrop-blur-xl border-l-2 border-orange-100 flex flex-col h-full rounded-l-[48px] shadow-2xl overflow-hidden">
        <div className="p-10 border-b border-orange-100 shrink-0">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-black flex items-center gap-3 text-orange-600 uppercase italic">Library</h2>
            <button onClick={fetchRecentAudios} className="p-2 hover:bg-orange-200 rounded-xl text-orange-500 transition-all"><RefreshCw size={20}/></button>
          </div>
          <p className="text-[10px] text-orange-400 font-bold uppercase mt-2 tracking-widest flex items-center gap-2">
            <Sparkles size={10} /> Smart Data Loading Enabled
          </p>
        </div>
        <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-hide">
          {recentAudios.length === 0 ? (
            <div className="text-center py-40 opacity-20">
              <Music size={64} className="mx-auto mb-4" />
              <p className="font-black text-xs uppercase tracking-widest">Library Empty</p>
            </div>
          ) : (
            recentAudios.map((audio, i) => (
              <div 
                key={i} 
                onClick={() => handleSelectItem(audio)}
                className={`p-6 rounded-[28px] border-2 transition-all cursor-pointer group ${refAudio?.url === audio.url ? 'bg-white border-orange-400 shadow-xl scale-[1.02]' : 'bg-white/50 border-orange-50 hover:border-orange-200 hover:bg-white'}`}
              >
                <div className="flex items-center gap-4">
                  <div className={`p-3 rounded-xl transition-all ${refAudio?.url === audio.url ? 'bg-orange-500 text-white shadow-orange-200 shadow-lg' : 'bg-orange-50 text-orange-300 group-hover:bg-orange-500 group-hover:text-white'}`}><Play size={16} fill="currentColor" /></div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-black truncate text-orange-900 group-hover:text-orange-600">{audio.name}</p>
                      <button onClick={(e) => handleDeleteAudio(e, audio)} className="p-2 hover:bg-red-100 rounded-lg text-red-300 hover:text-red-500 transition-all shrink-0"><Trash2 size={14} /></button>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                       <p className="text-[8px] font-black uppercase text-orange-300">Reference Wave</p>
                       {audio.metadata?.created_at && <span className="text-[8px] text-orange-200 font-bold tracking-tighter">● {audio.metadata.created_at}</span>}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
