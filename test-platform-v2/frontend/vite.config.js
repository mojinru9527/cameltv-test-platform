import { fileURLToPath, URL } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    build: {
        chunkSizeWarningLimit: 1200,
        rollupOptions: {
            output: {
                manualChunks: {
                    'vendor-react': ['react', 'react-dom', 'react-router-dom', 'zustand'],
                    'vendor-http': ['axios'],
                },
            },
        },
    },
    server: {
        port: 5173,
        proxy: {
            '/api': { target: 'http://localhost:8000', changeOrigin: true },
        },
    },
});
