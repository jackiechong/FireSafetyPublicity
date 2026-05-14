import axios from "axios";

/** 与请求路径 `/api/admin/...` 拼接；若环境变量写成 `http://host:port/api` 会得到 `/api/api/...` → 404，这里去掉末尾的 /api */
function normalizeApiBase() {
  let raw = (import.meta.env.VITE_API_BASE || "").trim();
  if (!raw) return "";
  raw = raw.replace(/\/+$/, "");
  if (raw.endsWith("/api")) {
    raw = raw.slice(0, -4);
  }
  return raw;
}

const http = axios.create({
  baseURL: normalizeApiBase(),
  timeout: 30000,
});

http.interceptors.request.use((config) => {
  const token = localStorage.getItem("admin_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("admin_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default http;
