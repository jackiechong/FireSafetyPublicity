const TOKEN_KEY = "admin_token";
const ISSUED_KEY = "admin_token_at";
const REMEMBER_MS = 7 * 24 * 60 * 60 * 1000;

/** 勾选「7 天内免登录」用 localStorage（带签发时间），否则用 sessionStorage（关掉标签页即失效）。 */
export function setToken(token, remember = true) {
  clearToken();
  if (remember) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(ISSUED_KEY, String(Date.now()));
  } else {
    sessionStorage.setItem(TOKEN_KEY, token);
  }
}

export function getToken() {
  const persistent = localStorage.getItem(TOKEN_KEY);
  if (persistent) {
    const issued = Number(localStorage.getItem(ISSUED_KEY) || 0);
    if (issued && Date.now() - issued > REMEMBER_MS) {
      clearToken();
      return "";
    }
    return persistent;
  }
  return sessionStorage.getItem(TOKEN_KEY) || "";
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ISSUED_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
}
