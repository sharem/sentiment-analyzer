// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import { loadEnv } from "vite";


function getConfig() {
  const { BACKEND_URL : backendUrl } = loadEnv(mode, process.cwd(), '');

  if (!backendUrl) {
    throw new Error(
      '🚨 BACKEND_URL is not defined! Please add `BACKEND_URL=http://…` to your .env'
    );
  }

  return {
    integrations: [react()],
    vite: {
      server: {
        host: true,
        proxy: {
          '/api': {
            target: backendUrl,
            changeOrigin: true,
          },
        },
      },
    },
  };
}

const { command = 'serve', mode = process.env.NODE_ENV || 'development' } = process.env;
export default defineConfig(getConfig());
