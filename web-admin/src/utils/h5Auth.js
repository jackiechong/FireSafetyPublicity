/** 公众号网页授权回跳后的 token 处理与重新登录。 */
import mpHttp from "../api/mpHttp";

/** 把 URL 里的 `?token=...` 取出来存 localStorage，并从地址栏清掉它。 */
export function captureTokenFromUrl() {
  try {
    const url = new URL(window.location.href);
    const t = url.searchParams.get("token");
    if (!t) return;
    localStorage.setItem("mp_token", t);
    url.searchParams.delete("token");
    const cleaned = url.pathname + (url.search || "") + (url.hash || "");
    window.history.replaceState({}, "", cleaned);
  } catch {
    /* ignore */
  }
}

/** 跳到后端登录入口；session_id 用于授权完成后回到签到页时携带。 */
export function redirectToWxAuth(sessionIdHint) {
  const here = new URL(window.location.href);
  const next = here.pathname; // 仅保留路径，session_id 单独传
  const params = new URLSearchParams();
  params.set("next", next);
  const sid = sessionIdHint ?? here.searchParams.get("session_id");
  if (sid) params.set("session_id", String(sid));
  window.location.replace(`/api/wxoa/login?${params.toString()}`);
}

/** 进入 H5 页面时调用：捕获 token / 用 /me 校验登录态 / 401 时跳授权。 */
export async function ensureH5Login(sessionIdHint) {
  captureTokenFromUrl();
  const token = localStorage.getItem("mp_token");
  if (!token) {
    redirectToWxAuth(sessionIdHint);
    return null;
  }
  try {
    const { data } = await mpHttp.get("/api/mp/me");
    return data;
  } catch (e) {
    if (e?.response?.status === 401) {
      redirectToWxAuth(sessionIdHint);
      return null;
    }
    throw e;
  }
}
