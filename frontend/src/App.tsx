import React, { Component, ReactNode } from 'react';
import { createBrowserRouter, RouterProvider, Outlet } from 'react-router-dom';
import Dashboard from './Dashboard';
import SoundStudio from './SoundStudio';
import VideoStudio from './VideoStudio';
import CloneVoice from './CloneVoice';
import FFmpegStudio from './FFmpegStudio';
import Navbar from './Navbar';

class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean; error: Error | null }> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-red-50 flex items-center justify-center p-8">
          <div className="bg-white p-8 rounded-[32px] shadow-2xl max-w-lg">
            <h2 className="text-2xl font-black text-red-600 mb-4">Đã xảy ra lỗi</h2>
            <p className="text-red-500 text-sm font-mono bg-red-50 p-4 rounded-2xl border border-red-100 mb-4">
              {this.state.error?.message}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="bg-red-500 hover:bg-red-600 text-white px-6 py-3 rounded-2xl font-bold transition-colors"
            >
              Tải lại trang
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

const router = createBrowserRouter([
  {
    element: (
      <ErrorBoundary>
        <Navbar />
        <Outlet />
      </ErrorBoundary>
    ),
    children: [
      { path: '/', element: <Dashboard /> },
      { path: '/studio', element: <SoundStudio /> },
      { path: '/other', element: <VideoStudio /> },
      { path: '/ffmpeg', element: <FFmpegStudio /> },
      { path: '/clone', element: <CloneVoice /> },
    ],
  },
]);

function App() {
  return <RouterProvider router={router} />;
}

export default App;
