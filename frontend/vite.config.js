import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  // Load env file from the current directory based on `mode`
  const env = loadEnv(mode, process.cwd(), '');

  return {
    root: './', // Assumes this file is INSIDE the frontend folder
    build: {
      outDir: 'dist', // Keeps the build folder inside the frontend directory for Vercel
      emptyOutDir: true,
    },
    server: {
      port: 3000,
      proxy: {
        // This helps avoid CORS issues during local development
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:10000',
          changeOrigin: true,
        },
      },
    },
  };
});