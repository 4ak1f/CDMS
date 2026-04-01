import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/analyze': {
        target: 'https://localhost:8000',
        secure: false,
        changeOrigin: true
      },
      '/history': {
        target: 'https://localhost:8000',
        secure: false,
        changeOrigin: true
      },
      '/stats': {
        target: 'https://localhost:8000',
        secure: false,
        changeOrigin: true
      },
      '/alerts': {
        target: 'https://localhost:8000',
        secure: false,
        changeOrigin: true
      },
      '/reports': {
        target: 'https://localhost:8000',
        secure: false,
        changeOrigin: true
      },
      '/thresholds': {
        target: 'https://localhost:8000',
        secure: false,
        changeOrigin: true
      },
      '/ws': {
        target: 'wss://localhost:8000',
        ws: true,
        secure: false,
        changeOrigin: true
      }
    }
  }
})