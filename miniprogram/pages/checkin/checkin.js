const { request } = require("../../utils/request");

function getSessionId(options = {}) {
  if (options.session_id) return Number(options.session_id);
  if (options.scene) {
    const scene = decodeURIComponent(options.scene);
    const match = scene.match(/(?:^|[?&])session_id=(\d+)/) || scene.match(/^(\d+)$/);
    if (match) return Number(match[1]);
  }
  return 0;
}

Page({
  data: {
    sessionId: 0,
    loading: false,
    result: null,
    error: "",
  },
  async onLoad(options) {
    const sessionId = getSessionId(options);
    this.setData({ sessionId });
    if (!sessionId) {
      this.setData({ error: "签到码无效，请重新扫码" });
      return;
    }
    await this.ensureLoginAndCheckin();
  },
  async ensureLoginAndCheckin() {
    const app = getApp();
    if (!app.globalData.token) {
      try {
        const login = await new Promise((resolve, reject) => {
          wx.login({ success: resolve, fail: reject });
        });
        const res = await request({
          url: "/api/mp/login",
          method: "POST",
          data: { code: login.code },
        });
        app.setToken(res.token);
        if (res.need_profile) {
          wx.redirectTo({ url: `/pages/bind/bind?session_id=${this.data.sessionId}` });
          return;
        }
      } catch (e) {
        this.setData({ error: e.message || "微信登录失败" });
        return;
      }
    }
    await this.submitCheckin();
  },
  async submitCheckin() {
    this.setData({ loading: true, error: "" });
    try {
      const result = await request({
        url: "/api/mp/checkin",
        method: "POST",
        data: { session_id: this.data.sessionId },
      });
      result.start_at = (result.start_at || "").replace("T", " ").slice(0, 16);
      this.setData({ result });
      wx.showToast({ title: result.already_checked ? "已签到" : "签到成功" });
    } catch (e) {
      if (String(e.message || "").includes("完成单位")) {
        wx.redirectTo({ url: `/pages/bind/bind?session_id=${this.data.sessionId}` });
        return;
      }
      this.setData({ error: e.message || "签到失败" });
    } finally {
      this.setData({ loading: false });
    }
  },
  goMe() {
    wx.redirectTo({ url: "/pages/me/me" });
  },
});
