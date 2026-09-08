import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

/**
 * The frontend never talks to Binance and never holds a secret. It talks to the
 * AKILI backend only, and in development it does so through this proxy rather
 * than cross-origin: the backend has no CORS middleware, and adding one would be
 * a backend change this milestone does not need.
 *
 * Proxying also keeps `GET /api/v1/binance/connect` usable. That route answers a
 * 302 to Binance, so the browser has to navigate to it at the top level; a
 * same-origin path lets it do that and follow the redirect normally.
 *
 * `envDir: '..'` is deliberate: AKILI keeps a single `.env` at the repository
 * root, so `VITE_*` values are read from there. Only `VITE_`-prefixed values
 * ever reach the bundle, and none of them is a credential.
 */
const BACKEND_URL = process.env.AKILI_BACKEND_URL ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  envDir: '..',
  server: {
    port: 5173,
    proxy: {
      '/api': { target: BACKEND_URL, changeOrigin: true },
      '/health': { target: BACKEND_URL, changeOrigin: true },
      '/.well-known': { target: BACKEND_URL, changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: true,
  },
})
