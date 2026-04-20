import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      workbox: {
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/tile\.openstreetmap\.org\/.*/,
            handler: "CacheFirst",
            options: {
              cacheName: "osm-tiles",
              expiration: { maxEntries: 2000, maxAgeSeconds: 604800 },
            },
          },
          {
            urlPattern: /\/footprints\//,
            handler: "CacheFirst",
            options: { cacheName: "building-footprints" },
          },
          {
            urlPattern: /\/api\//,
            handler: "NetworkFirst",
            options: { cacheName: "api-cache", networkTimeoutSeconds: 3 },
          },
        ],
      },
      manifest: {
        name: "Crisis Damage Reporter",
        short_name: "CrisisReport",
        description: "Report crisis damage in real time — works offline",
        theme_color: "#1a56db",
        background_color: "#ffffff",
        display: "standalone",
        icons: [
          { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
        ],
      },
    }),
  ],
  server: { port: 3000 },
});
