import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';

export default defineConfig({
  // Relative paths: the site works at byrodi.github.io/wynncard/ and at any other root.
  base: './',
  plugins: [svelte()],
  worker: { format: 'es' },
});
