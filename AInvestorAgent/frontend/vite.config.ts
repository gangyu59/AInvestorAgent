import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 先不装 Tailwind 插件，保持最小化
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173
  }
});
