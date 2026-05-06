import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './Dashboard';
import SoundStudio from './SoundStudio';
import VideoStudio from './VideoStudio';
import CloneVoice from './CloneVoice';
import FFmpegStudio from './FFmpegStudio';
import Navbar from './Navbar';

function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/studio" element={<SoundStudio />} />
        <Route path="/other" element={<VideoStudio />} />
        <Route path="/ffmpeg" element={<FFmpegStudio />} />
        <Route path="/clone" element={<CloneVoice />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
