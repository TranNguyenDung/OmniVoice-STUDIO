import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/audio': 'http://localhost:8000',
      '/generate': 'http://localhost:8000',
      '/list_audios': 'http://localhost:8000',
      '/upload_media': 'http://localhost:8000',
      '/generate_video': 'http://localhost:8000',
      '/media': 'http://localhost:8000',
      '/video/output': 'http://localhost:8000',
    }
  }
})
