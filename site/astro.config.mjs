import { defineConfig } from 'astro/config';

// Static output. The base path is a build setting: SITE_BASE (default '/') and, optionally, SITE_URL.
// GitHub Pages project sites use the repository name, for example SITE_BASE=/Bellwether-Project/
const raw = process.env.SITE_BASE || '/';
const base = `/${raw.replace(/^\/+|\/+$/g, '')}${raw.replace(/^\/+|\/+$/g, '') ? '/' : ''}`;

export default defineConfig({
  output: 'static',
  site: process.env.SITE_URL || undefined,
  base,
  build: { format: 'directory' },
  compressHTML: false, // keep authored whitespace around inline elements
});
