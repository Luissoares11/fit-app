import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // reachable from your phone on the local network
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})