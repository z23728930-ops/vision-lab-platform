// defect-detection-frontend/vite.config.js

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendUrl = env.VITE_BACKEND_URL || 'http://127.0.0.1:8001'

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      }
    },
    server: {
      proxy: {
        '/api': { target: backendUrl, changeOrigin: true, ws: true },
        '/static_uploads': { target: backendUrl, changeOrigin: true }
      }
    }
  }
})