import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

const apiProxyTarget = process.env.VITE_PROXY_API_TARGET || 'http://43.201.160.163'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    strictPort: false,
    fs: {
      allow: ['..']
    },
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
        rewrite: (path) => path
      },
      '/chrome': {
        target: 'http://127.0.0.1:9222',
        changeOrigin: true,
        ws: true,
        rewrite: (path) => path.replace(/^\/chrome/, '')
      }
    }
  }
})
