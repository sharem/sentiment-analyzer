// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import { loadEnv } from "vite";


function getConfig() {
  const mode = process.env.NODE_ENV || 'development';
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

export default defineConfig(getConfig());
