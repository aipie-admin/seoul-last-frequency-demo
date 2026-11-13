import { defineConfig } from 'vite';
export default defineConfig({ base: '/seoul-last-frequency-demo/', build: { assetsInlineLimit: 0, target: 'es2020' }, server: { host: true }, preview: { host: true, allowedHosts: true } });
