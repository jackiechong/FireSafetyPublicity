import axios from "axios";

/** H5 (公众号网页授权) 专用 axios。与 admin 后台用的 http 拆开，
 *  Authorization 头使用 localStorage.mp_token，401 时回到公众号网页授权入口。 */
function normalizeApiBase() {
  let raw = (import.meta.env.VITE_API_BASE || "").trim();
  if (!raw) return "";
  raw = raw.replace(/\/+$/, "");
  if (raw.endsWith("/api")) {
    raw = raw.slice(0, -4);
  }
  return raw;
}

const mpHttp = axios.create({
  baseURL: normalizeApiBase(),
  timeout: 30000,
});

mpHttp.interceptors.request.use((config) => {
  const token = localStorage.getItem("mp_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

mpHttp.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("mp_token");
    }
    return Promise.reject(err);
  }
);

export default mpHttp;
