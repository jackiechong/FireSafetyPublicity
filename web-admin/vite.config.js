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

const devPort = Number(process.env.DEV_PORT || 5300);

export default defineConfig({
  plugins: [vue()],
  server: {
    // 固定 IPv4，避免只监听 ::1 时部分环境访问 127.0.0.1 失败
    host: "127.0.0.1",
    // 默认 5300；需要换端口时用 DEV_PORT=xxxx npm run dev，或直接改这里
    port: devPort,
    // 端口被占用时直接报错，避免悄悄漂移到 5301、5302 后找不到地址
    strictPort: true,
    proxy: apiProxy,
    // 编辑器/工具写入时的临时目录会触发 EBUSY，直接忽略
    watch: {
      ignored: ["**/.*.tmpdir/**", "**/.*.tmpdir", "**/*.tmp"],
    },
  },
  // npm run build && vite preview 时默认无 /api 代理，会 404；与 dev 共用代理
  preview: {
    host: "127.0.0.1",
    port: 4173,
    strictPort: true,
    proxy: apiProxy,
  },
});
