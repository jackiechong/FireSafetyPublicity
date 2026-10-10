const { request } = require("../../utils/request");

Page({
  data: {
    loading: true,
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

  onPullDownRefresh() {
    this.load(true);
  },

  async load(fromPullDown = false) {
    this.setData({ loading: true });
    try {
      const list = await request({ url: "/api/mp/trainings" });
      this.setData({
        list: (list || []).map((item) => ({
          ...item,
          start_at: String(item.start_at || "").replace("T", " ").slice(0, 16),
        })),
      });
    } catch (e) {
      wx.showToast({ title: e.message || "加载失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
      if (fromPullDown) wx.stopPullDownRefresh();
    }
  },
});
