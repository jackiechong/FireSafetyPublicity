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
    activeList: [],
    selectedSessionId: 0,
  },
  async onLoad(options) {
    const sessionId = getSessionId(options);
    this.setData({ sessionId, selectedSessionId: sessionId || 0 });
    await this.ensureLoginAndLoad();
  },
  async ensureLoginAndLoad() {
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
          const q = this.data.sessionId ? `?session_id=${this.data.sessionId}` : "";
          wx.redirectTo({ url: `/pages/bind/bind${q}` });
          return;
        }
      } catch (e) {
        this.setData({ error: e.message || "微信登录失败" });
        return;
      }
    }
    await this.loadActiveTrainings();
  },
  async loadActiveTrainings() {
    this.setData({ loading: true, error: "", result: null });
    try {
      const list = await request({ url: "/api/mp/active-trainings" });
      const activeList = (list || []).map((t) => ({
        ...t,
        start_at: (t.start_at || "").replace("T", " ").slice(0, 16),
      }));
      const exists = activeList.some((t) => Number(t.session_id) === Number(this.data.selectedSessionId));
      this.setData({
        activeList,
        selectedSessionId: exists ? this.data.selectedSessionId : activeList.length === 1 ? activeList[0].session_id : 0,
        error: activeList.length ? "" : "今天暂无可加入的培训场次",
      });
    } catch (e) {
      if (String(e.message || "").includes("完成单位")) {
        const q = this.data.sessionId ? `?session_id=${this.data.sessionId}` : "";
        wx.redirectTo({ url: `/pages/bind/bind${q}` });
        return;
      }
      this.setData({ error: e.message || "加载培训场次失败" });
    } finally {
      this.setData({ loading: false });
    }
  },
  onPickTraining(e) {
    this.setData({ selectedSessionId: Number(e.currentTarget.dataset.id) || 0 });
  },
  async submitCheckin() {
    if (!this.data.selectedSessionId) {
      wx.showToast({ title: "请选择培训场次", icon: "none" });
      return;
    }
    this.setData({ loading: true, error: "" });
    try {
      const result = await request({
        url: "/api/mp/checkin",
        method: "POST",
        data: { session_id: this.data.selectedSessionId },
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
