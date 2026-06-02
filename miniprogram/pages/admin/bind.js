const { request } = require("../../utils/request");

Page({
  data: {
    code: "",
    loading: false,
    bound: false,
    adminUsername: "",
    adminRoleText: "",
    adminBrigadeName: "",
    failCount: 0,
    locked: false,
  },

  onShow() {
    const app = getApp();
    if (!app.globalData.token) {
      wx.redirectTo({ url: "/pages/index/index" });
      return;
    }
    this.checkBound();
  },

  async checkBound() {
    try {
      const me = await request({ url: "/api/mp/me" });
      if (me.is_admin) {
        this.setData({
          bound: true,
          adminUsername: me.admin_username || "",
          adminRoleText: me.admin_role === "detachment" ? "支队" : "大队",
          adminBrigadeName: me.admin_brigade_name || "",
        });
        const app = getApp();
        app.globalData.isAdmin = true;
      }
    } catch (e) {
      // ignore
    }
  },

  onCodeInput(e) {
    if (this.data.locked) return;
    this.setData({ code: (e.detail.value || "").replace(/\D/g, "").slice(0, 8) });
  },

  async onSubmit() {
    if (this.data.locked) {
      wx.showToast({ title: "输入错误次数过多，请重新生成绑定码", icon: "none" });
      return;
    }
    const code = this.data.code.trim();
    if (code.length !== 8) {
      wx.showToast({ title: "请输入8位绑定码", icon: "none" });
      return;
    }
    this.setData({ loading: true });
    try {
      const res = await request({
        url: "/api/mp/admin/wx-bind",
        method: "POST",
        data: { code },
      });
      const app = getApp();
      app.globalData.isAdmin = true;
      this.setData({
        bound: true,
        adminUsername: res.admin_username,
        adminRoleText: res.admin_role === "detachment" ? "支队" : "大队",
        adminBrigadeName: res.admin_brigade_name || "",
      });
      wx.showToast({ title: "绑定成功", icon: "success" });
    } catch (e) {
      const nextFailCount = this.data.failCount + 1;
      const locked = nextFailCount >= 5;
      this.setData({ failCount: nextFailCount, locked });
      wx.showToast({
        title: locked ? "输入错误次数过多，请重新生成绑定码" : e.message || "绑定失败",
        icon: "none",
      });
    } finally {
      this.setData({ loading: false });
    }
  },

  goTraining() {
    wx.navigateTo({ url: "/pages/admin/index" });
  },
});
