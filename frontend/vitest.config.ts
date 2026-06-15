import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.ts'],
    css: false,
    // Chỉ chạy unit test trong src/. Thư mục e2e/ dành cho Playwright (npm run test:e2e).
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
});
