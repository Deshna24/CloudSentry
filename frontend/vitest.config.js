import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'happy-dom',
    environmentOptions: { happyDOM: { url: process.env.VITE_API_URL || 'http://127.0.0.1:8000' } },
    include: ['src/**/*.test.jsx'],
    testTimeout: 30000,
  },
});
