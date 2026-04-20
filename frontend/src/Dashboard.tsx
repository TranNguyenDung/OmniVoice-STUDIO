import React from 'react';
import { Mic, Sparkles, Music, Shield, Zap, ArrowRight, LayoutDashboard, Settings, Copy } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const FeatureCard = ({ icon: Icon, title, description }: { icon: any, title: string, description: string }) => (
  <div className="bg-white p-8 rounded-[32px] border border-orange-100 shadow-lg hover:shadow-xl transition-all hover:-translate-y-1">
    <div className="bg-orange-500 w-12 h-12 rounded-2xl flex items-center justify-center mb-6 shadow-lg shadow-orange-200">
      <Icon className="text-white" size={24} />
    </div>
    <h3 className="text-xl font-black text-orange-900 mb-3">{title}</h3>
    <p className="text-orange-600/70 text-sm leading-relaxed font-medium">{description}</p>
  </div>
);

export default function Dashboard() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-orange-50 font-sans text-orange-950 overflow-x-hidden">
      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-6 pt-20 pb-12">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-yellow-100 rounded-full border border-yellow-200 mb-6">
            <Sparkles className="text-orange-500" size={16} />
            <span className="text-xs font-black text-orange-600 uppercase tracking-widest">The Future of Voice Synthesis</span>
          </div>
          <h1 className="text-6xl md:text-7xl font-black tracking-tight mb-6 italic">
            OmniVoice <span className="text-orange-500 not-italic">STUDIO</span>
          </h1>
          <p className="text-xl text-orange-800/60 max-w-2xl mx-auto font-bold leading-relaxed">
            Giải pháp tạo giọng nói AI đột phá với khả năng sao chép giọng nói tức thì và điều chỉnh cảm xúc linh hoạt.
          </p>
        </div>

        {/* Navigation Buttons */}
        <div className="flex flex-col md:flex-row gap-6 justify-center mb-24">
          <button
            onClick={() => navigate('/studio')}
            className="group relative bg-orange-500 hover:bg-orange-600 text-white px-10 py-6 rounded-[32px] text-xl font-black flex items-center gap-4 shadow-2xl shadow-orange-200 transition-all active:scale-[0.98] hover:-translate-y-1"
          >
            <div className="bg-white/20 p-2 rounded-xl">
              <Mic size={28} />
            </div>
            <span>Bắt đầu Tạo Âm Thanh</span>
            <ArrowRight className="group-hover:translate-x-1 transition-transform" />
          </button>

          <button
            onClick={() => navigate('/clone')}
            className="group bg-white hover:bg-orange-100 text-orange-600 px-10 py-6 rounded-[32px] text-xl font-black flex items-center gap-4 border-2 border-orange-200 shadow-xl transition-all active:scale-[0.98] hover:-translate-y-1"
          >
            <div className="bg-orange-100 p-2 rounded-xl">
              <Mic size={28} />
            </div>
            <span>Record Audio</span>
          </button>

          <button
            onClick={() => navigate('/other')}
            className="group bg-white hover:bg-orange-100 text-orange-600 px-10 py-6 rounded-[32px] text-xl font-black flex items-center gap-4 border-2 border-orange-200 shadow-xl transition-all active:scale-[0.98] hover:-translate-y-1"
          >
            <div className="bg-orange-100 p-2 rounded-xl">
              <LayoutDashboard size={28} />
            </div>
            <span>Ghép Audio & Video</span>
            
          </button>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-20">
          <FeatureCard 
            icon={Zap} 
            title="Tạo giọng tức thì" 
            description="Chuyển đổi văn bản thành giọng nói chất lượng cao chỉ trong vài giây với công nghệ xử lý song song hiện đại."
          />
          <FeatureCard 
            icon={Music} 
            title="Sao chép giọng nói" 
            description="Chỉ cần một đoạn âm thanh mẫu ngắn, OmniVoice có thể tái tạo chính xác tông giọng và phong cách nói."
          />
          <FeatureCard 
            icon={Settings} 
            title="Tùy chỉnh linh hoạt" 
            description="Điều chỉnh giới tính, độ tuổi, cao độ và cảm xúc (thì thầm, trang trọng...) một cách dễ dàng."
          />
          <FeatureCard 
            icon={Shield} 
            title="Bảo mật dữ liệu" 
            description="Toàn bộ dữ liệu âm thanh và văn bản của bạn được xử lý an toàn và bảo mật tuyệt đối."
          />
          <FeatureCard 
            icon={LayoutDashboard} 
            title="Thư viện thông minh" 
            description="Quản lý các bản thu và mẫu giọng nói một cách khoa học với hệ thống metadata tự động."
          />
          <FeatureCard 
            icon={Sparkles} 
            title="Chất lượng Studio" 
            description="Âm thanh đầu ra đạt chuẩn phòng thu, trong trẻo và tự nhiên như người thật nói."
          />
        </div>

        {/* Footer info */}
        <div className="text-center text-orange-300 font-bold text-sm tracking-widest uppercase">
          © 2026 OmniVoice STUDIO • All Rights Reserved
        </div>
      </div>
    </div>
  );
}
