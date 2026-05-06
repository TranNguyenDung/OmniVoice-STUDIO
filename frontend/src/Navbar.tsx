import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Mic, LayoutDashboard, Film, Music, Clapperboard } from 'lucide-react';

const navItems = [
  { path: '/', label: 'Home', icon: LayoutDashboard },
  { path: '/studio', label: 'Sound Studio', icon: Mic },
  { path: '/other', label: 'Video Creator', icon: Clapperboard },
  { path: '/ffmpeg', label: 'FFmpeg Studio', icon: Film },
  { path: '/clone', label: 'Record', icon: Music },
];

export default function Navbar() {
  const location = useLocation();

  return (
    <nav className="bg-white border-b border-orange-100 shadow-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <div className="bg-orange-500 p-2 rounded-xl">
              <Mic className="text-white" size={20} />
            </div>
            <span className="font-black text-orange-900">OmniVoice</span>
          </Link>

          <div className="flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-black transition-all ${
                    isActive
                      ? 'bg-orange-500 text-white shadow-lg shadow-orange-200'
                      : 'text-orange-600 hover:bg-orange-50'
                  }`}
                >
                  <Icon size={16} />
                  <span className="hidden md:inline">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}
