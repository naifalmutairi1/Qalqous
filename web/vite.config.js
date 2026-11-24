import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// open: true -> the browser opens by itself after `npm run dev`.
// proxy: requests to /api go to the Python API on this laptop, so the browser sees one address
// (no CORS setup needed).
export default defineConfig({
  plugins: [react()],
  server: {
    open: true,
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
});
