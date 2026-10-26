// Site-internal URLs, honouring the build's base path (set with SITE_BASE; see astro.config.mjs).
const root = (import.meta.env.BASE_URL as string).replace(/\/+$/, '');

export const url = (path: string): string => `${root}/${path.replace(/^\/+/, '')}`;
