import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const apiProxy = {
  "/api": {
    target: "http://127.0.0.1:18080",
    changeOrigin: true,
  },
  "/health": {
    target: "http://127.0.0.1:18080",
    changeOrigin: true,
  },
};

export default defineConfig({
  plugins: [vue()],
  server: {
    // 固定 IPv4，避免只监听 ::1 时部分环境访问 127.0.0.1 失败
    host: "127.0.0.1",
    port: 5173,
    // 5173 已被占用时自动尝试 5174、5175…，避免「Port already in use」
    strictPort: false,
    proxy: apiProxy,
  },
  // npm run build && vite preview 时默认无 /api 代理，会 404；与 dev 共用代理
  preview: {
    host: "127.0.0.1",
    port: 4173,
    strictPort: true,
    proxy: apiProxy,
  },
});
