import React from 'react';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import Dashboard from './Dashboard';
import SoundStudio from './SoundStudio';
import { ArrowLeft, Construction } from 'lucide-react';

// Một trang tạm thời cho chức năng chưa thiết kế
const OtherPage = () => {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-orange-50 flex flex-col items-center justify-center p-6 text-center">
      <div className="bg-white p-12 rounded-[48px] shadow-2xl border-2 border-orange-100 max-w-md">
        <div className="bg-orange-100 w-24 h-24 rounded-full flex items-center justify-center mx-auto mb-8">
          <Construction className="text-orange-500" size={48} />
        </div>
        <h2 className="text-3xl font-black text-orange-900 mb-4 italic">Đang phát triển</h2>
        <p className="text-orange-600 font-bold mb-10 leading-relaxed">
          Chức năng này đang được chúng tôi thiết kế và sẽ sớm ra mắt trong thời gian tới. Quay lại sau nhé!
        </p>
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-3 bg-orange-500 text-white px-8 py-4 rounded-2xl font-black hover:bg-orange-600 transition-all shadow-lg shadow-orange-200 active:scale-95"
        >
          <ArrowLeft size={20} />
          Quay lại Dashboard
        </button>
      </div>
    </div>
  );
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/studio" element={<SoundStudio />} />
        <Route path="/other" element={<OtherPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
