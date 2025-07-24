import { defineConfig } from 'vite'
import preact from '@preact/preset-vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [preact()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://192.168.194.33:8020',
        changeOrigin: true,
        secure: false,
        ws: true,
        followRedirects: true,
        rewrite: (path) => path,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('proxy error', err);
          });
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            if (!req.complete && !req.socket.destroyed) {
              console.log('Sending Request to the Target:', req.method, req.url);
              try {
                proxyReq.setHeader('Origin', 'http://192.168.194.33:5173');
              } catch (error) {
                console.warn('Could not set header:', error.message);
              }
            }
          });
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            console.log('Received Response from the Target:', proxyRes.statusCode, req.url);
          });
        },
      }
    },
    cors: true
  },
  build: {
    minify: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['preact', 'preact-router'],
          util: ['axios']
        }
      }
    }
  }
}) 