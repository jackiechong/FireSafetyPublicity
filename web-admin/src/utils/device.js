/**
 * 是否应使用手机端数据看板 /m（与桌面后台区分）。
 * 以 UA 为主，避免仅缩窄桌面浏览器窗口就被当成手机。
 */
export function prefersMobileDashboard() {
  if (typeof window === "undefined") return false;
  try {
    if (localStorage.getItem("prefer_desktop") === "1") return false;
  } catch {
    /* ignore */
  }
  const ua = navigator.userAgent || "";
  if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua)) {
    return true;
  }
  // iPadOS 13+ 桌面模式常带 Macintosh + 触摸屏
  if (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1) {
    return true;
  }
  return false;
}
