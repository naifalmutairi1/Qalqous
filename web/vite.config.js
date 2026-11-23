import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// open: true -> the browser opens by itself after `npm run dev`.
export default defineConfig({
  plugins: [react()],
  server: { open: true },
});
