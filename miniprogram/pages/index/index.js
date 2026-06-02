const { request } = require("../../utils/request");

Page({
  data: { loading: false },
  onShow() {
    const app = getApp();
    if (app.globalData.token) {
      wx.redirectTo({ url: "/pages/me/me" });
    }
  },
  async onLogin() {
    this.setData({ loading: true });
    try {
      const login = await new Promise((resolve, reject) => {
        wx.login({ success: resolve, fail: reject });
      });
      const res = await request({
        url: "/api/mp/login",
        method: "POST",
        data: { code: login.code },
      });
      const app = getApp();
      app.setToken(res.token);
      app.globalData.isAdmin = !!res.is_admin;
      if (res.need_profile) {
        wx.redirectTo({ url: "/pages/bind/bind" });
      } else {
        wx.redirectTo({ url: "/pages/me/me" });
      }
    } catch (e) {
      wx.showToast({ title: e.message || "登录失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },
});
