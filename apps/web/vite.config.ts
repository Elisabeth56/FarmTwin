import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss()],
  // `--mode demo` builds the in-browser demo into the website at /demo/ (src/demo/server.ts)
  base: mode === 'demo' ? '/demo/' : '/',
  build: mode === 'demo' ? { outDir: '../site/public/demo', emptyOutDir: true } : {},
  server: {
    host: '127.0.0.1',   // bind to IPv4 explicitly (ADR-007)
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: false,
      },
    },
  },
}))
