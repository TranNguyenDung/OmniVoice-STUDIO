import React from 'react';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import Dashboard from './Dashboard';
import SoundStudio from './SoundStudio';
import VideoStudio from './VideoStudio';
import { ArrowLeft, Construction } from 'lucide-react';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/studio" element={<SoundStudio />} />
        <Route path="/other" element={<VideoStudio />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
