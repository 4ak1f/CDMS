import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/analyze':    { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/stats':      { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/system':     { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/feedback':   { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/history':    { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/incidents':  { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/calibration':{ target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/thresholds': { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/alerts':     { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/zones':      { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/logs':       { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/reports':    { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/cloud':      { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/session':    { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/ngrok':      { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/location':   { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/schedule':   { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/anomaly':    { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/auth':       { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/sms':        { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/deadman':    { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/analytics':  { target: 'https://localhost:8000', secure: false, changeOrigin: true },
      '/ws':         { target: 'https://localhost:8000', secure: false, changeOrigin: true, ws: true },
    }
  }
})
