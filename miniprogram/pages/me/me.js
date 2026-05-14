const { request } = require("../../utils/request");

Page({
  data: {
    person: {},
    list: [],
  },
  onShow() {
    const app = getApp();
    if (!app.globalData.token) {
      wx.redirectTo({ url: "/pages/index/index" });
      return;
    }
    this.load();
  },
  async load() {
    try {
      const [me, trainings] = await Promise.all([
        request({ url: "/api/mp/me" }),
        request({ url: "/api/mp/trainings" }),
      ]);
      const list = (trainings || []).map((t) => ({
        ...t,
        start_at: (t.start_at || "").replace("T", " ").slice(0, 16),
      }));
      this.setData({ person: me, list });
      const ok =
        me.name &&
        me.phone &&
        me.district_id &&
        me.organization_id;
      if (!ok) {
        wx.redirectTo({ url: "/pages/bind/bind" });
      }
    } catch (e) {
      wx.showToast({ title: e.message || "加载失败", icon: "none" });
    }
  },
  logout() {
    const app = getApp();
    app.setToken("");
    wx.redirectTo({ url: "/pages/index/index" });
  },
});
