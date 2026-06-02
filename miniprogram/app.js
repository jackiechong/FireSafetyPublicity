App({
  globalData: {
    token: "",
    isAdmin: false,
    apiBase: "https://hld-xfpx.xyz", // 在 utils/config.js 填写后端地址
  },
  onLaunch() {
    const cfg = require("./utils/config");
    this.globalData.apiBase = cfg.apiBase;
    const t = wx.getStorageSync("mp_token");
    if (t) this.globalData.token = t;
  },
  setToken(token) {
    this.globalData.token = token;
    if (token) wx.setStorageSync("mp_token", token);
    else wx.removeStorageSync("mp_token");
  },
});
