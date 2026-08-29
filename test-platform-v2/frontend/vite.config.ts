import { fileURLToPath, URL } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import { API_V1_PROXY_PATTERN, API_V2_PROXY_PATTERN } from './config/devProxy'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const devPort = Number(env.VITE_DEV_PORT || 5173)
  const proxyTarget = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [react()],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    build: {
      chunkSizeWarningLimit: 1200,
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor-react': ['react', 'react-dom', 'react-router', 'zustand'],
            'vendor-http': ['axios'],
          },
        },
      },
    },
    server: {
      port: devPort,
      proxy: {
        [API_V1_PROXY_PATTERN]: { target: proxyTarget, changeOrigin: true, ws: true },
        [API_V2_PROXY_PATTERN]: { target: proxyTarget, changeOrigin: true, ws: true },
      },
    },
  }
})
