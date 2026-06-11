const { request } = require("../../utils/request");

Page({
  data: {
    person: {},
    list: [],
    knowledgeCategories: [
      { value: "knowledge", label: "消防知识" },
      { value: "law", label: "法律法规" },
      { value: "system", label: "制度" },
      { value: "equipment", label: "器材使用" },
    ],
    activeKnowledge: "",
    knowledgeList: [],
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
      const app = getApp();
      app.globalData.isAdmin = !!me.is_admin;
      this.setData({ person: me, list });
      const ok =
        me.name &&
        me.phone &&
        me.district_id &&
        me.organization_id;
      if (!ok) {
        wx.redirectTo({ url: "/pages/bind/bind" });
      } else {
        this.loadKnowledge("knowledge");
      }
    } catch (e) {
      wx.showToast({ title: e.message || "加载失败", icon: "none" });
    }
  },
  goAdminEntry() {
    if (this.data.person && this.data.person.is_admin) {
      this.goAdminTraining();
      return;
    }
    this.goAdminBind();
  },
  goAdminBind() {
    wx.navigateTo({ url: "/pages/admin/bind" });
  },
  goAdminTraining() {
    wx.navigateTo({ url: "/pages/admin/index" });
  },
  goAdminStats() {
    wx.navigateTo({ url: "/pages/admin/stats" });
  },
  goCheckin() {
    wx.navigateTo({ url: "/pages/checkin/checkin" });
  },
  async loadKnowledge(category) {
    try {
      const list = await request({ url: `/api/mp/knowledge-articles?category=${category}` });
      this.setData({ activeKnowledge: category, knowledgeList: list || [] });
    } catch (e) {
      this.setData({ activeKnowledge: category, knowledgeList: [] });
    }
  },
  onPickKnowledge(e) {
    this.loadKnowledge(e.currentTarget.dataset.category);
  },
  logout() {
    const app = getApp();
    app.setToken("");
    wx.redirectTo({ url: "/pages/index/index" });
  },
});
