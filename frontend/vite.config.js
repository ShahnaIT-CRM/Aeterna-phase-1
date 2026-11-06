import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In production Django serves the build under /static/, so assets must be prefixed with it.
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'build' ? '/static/' : '/',
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000', '/media': 'http://localhost:8000' },
  },
}))
