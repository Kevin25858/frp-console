import path from "path"
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  base: '/static/',
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    extensions: ['.mjs', '.js', '.ts', '.jsx', '.tsx', '.json'],
  },
  server: {
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:7600',
        changeOrigin: true,
        configure: (_proxy, _options) => {
          _proxy.on('proxyReq', (_proxyReq, req, _res) => {
            console.log('[Proxy] Request:', req.method, req.url, 'Headers:', req.headers.cookie);
          });
          _proxy.on('proxyRes', (proxyRes, _req, _res) => {
            const cookies = proxyRes.headers['set-cookie'];
            if (cookies) {
              console.log('[Proxy] Response cookies:', cookies);
              proxyRes.headers['set-cookie'] = cookies.map(cookie => {
                // Fix cookie format to work with cross-origin requests
                return cookie
                  .replace(/Path=\/;?\s*/i, 'Path=/; ')
                  .replace(/Domain=\.?(\S*);?\s*/i, '')
                  .replace(/SameSite=\w+/i, 'SameSite=Lax');
              });
            }
          });
        }
      },
      '/login': {
        target: 'http://127.0.0.1:7600',
        changeOrigin: true,
        configure: (_proxy, _options) => {
          _proxy.on('proxyRes', (proxyRes, _req, _res) => {
            const cookies = proxyRes.headers['set-cookie'];
            if (cookies) {
              console.log('[Proxy] Login cookies:', cookies);
              proxyRes.headers['set-cookie'] = cookies.map(cookie => {
                // Fix cookie format to work with cross-origin requests
                return cookie
                  .replace(/Path=\/;?\s*/i, 'Path=/; ')
                  .replace(/Domain=\.?(\S*);?\s*/i, '')
                  .replace(/SameSite=\w+/i, 'SameSite=Lax');
              });
            }
          });
        }
      }
    }
  }
})
