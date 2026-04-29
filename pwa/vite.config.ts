import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      workbox: {
        // Activate new service worker immediately without waiting for tabs to close
        skipWaiting: true,
        clientsClaim: true,
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
            // Only cache GET API responses — never intercept POST/PUT (report submissions)
            // so auth headers are always sent directly and never affected by SW caching.
            urlPattern: ({ request, url }) =>
              url.pathname.includes("/api/") && request.method === "GET",
            handler: "NetworkFirst",
            options: { cacheName: "api-cache", networkTimeoutSeconds: 5 },
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
