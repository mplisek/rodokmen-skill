import { defineConfig } from 'astro/config';

export default defineConfig({
  trailingSlash: 'always',
  build: { format: 'directory' },
  // Složka projektu může ležet za odkazem (junction/symlink, např. OneDrive přes C:\onedrive). Bez toho Vite porovná
  // dva zápisy téže cesty a stránky ztratí odkaz na styly (CSS).
  vite: { resolve: { preserveSymlinks: true } },
});
