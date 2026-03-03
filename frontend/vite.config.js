import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'mask-icon.svg'],
      manifest: {
        name: 'WildTrackAI Field Assistant',
        short_name: 'WildTrackAI',
        description: 'AI-powered wildlife footprint identification for field researchers',
        theme_color: '#f97316',
        background_color: '#0a0a0a',
        display: 'standalone',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' }
        ]
      }
    })
  ],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  build: {
    chunkSizeWarningLimit: 2000,
    target: 'es2015', // Better browser compatibility including Edge
    cssTarget: 'chrome61', // CSS compatibility for older browsers
  },
  optimizeDeps: {
    esbuildOptions: {
      target: 'es2015' // Ensure dependencies are transpiled for compatibility
    }
  }
})
