import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/analyze': 'http://localhost:8000',
      '/history': 'http://localhost:8000',
      '/stats':   'http://localhost:8000',
      '/alerts':  'http://localhost:8000',
      '/reports': 'http://localhost:8000',
      '/ws':      { target: 'ws://localhost:8000', ws: true }
    }
  }
})