const { request } = require("../../utils/request");
const cfg = require("../../utils/config");
const FALLBACK_ORG_TYPE_LABELS = {
  emergency: "应急",
  education: "教育",
  civil_affairs: "民政",
  culture_tourism: "文旅",
  health: "卫建",
  commerce: "商务",
  industry_agriculture: "农业农村",
  development_reform: "发改",
  other_department: "其他部门",
  department: "其他部门",
  enterprise: "其他部门",
};

function resolveQrUrl(payload) {
  if (!payload) return "";
  const s = String(payload);
  if (/^https?:\/\//i.test(s)) return s;
  const base = (cfg.apiBase || "").replace(/\/$/, "");
  if (s.startsWith("session_id=") && base) {
    return `${base}/api/wxoa/login?${s}`;
  }
  return s;
}

Page({
  data: {
    adminInfo: null,
    districtList: [],
    districtNames: [],
    districtIndex: 0,
    districtId: null,
    orgList: [],
    orgLabels: [],
    orgIndex: 0,
    topicList: [],
    topicNames: [],
    topicIndex: 0,
    topicId: null,
    title: "",
    durationMinutes: "60",
    location: "",
    creating: false,
    trainings: [],
    qrInfo: null,
    qrUrl: "",
    orgTypeLabels: FALLBACK_ORG_TYPE_LABELS,
  },

  onShow() {
    const app = getApp();
    if (!app.globalData.token) {
      wx.redirectTo({ url: "/pages/index/index" });
      return;
    }
    this.init();
  },

  async init() {
    try {
      const adminInfo = await request({ url: "/api/mp/admin/me" });
      this.setData({ adminInfo });
      const app = getApp();
      app.globalData.isAdmin = true;
    } catch (e) {
      wx.showModal({
        title: "需要绑定",
        content: "请先在「管理员绑定」页输入网站生成的绑定码",
        showCancel: false,
        success: () => wx.redirectTo({ url: "/pages/admin/bind" }),
      });
      return;
    }
    await Promise.all([this.loadOrgTypes(), this.loadTopics(), this.loadDistricts(), this.loadTrainings()]);
  },

  async loadOrgTypes() {
    try {
      const list = await request({ url: "/api/mp/org-types" });
      const labels = { ...FALLBACK_ORG_TYPE_LABELS };
      (list || []).forEach((item) => {
        if (item.code) labels[item.code] = item.name;
      });
      this.setData({ orgTypeLabels: labels });
    } catch (e) {
      this.setData({ orgTypeLabels: FALLBACK_ORG_TYPE_LABELS });
    }
  },

  async loadTopics() {
    try {
      const list = await request({ url: "/api/mp/training-topics" });
      this.setData({
        topicList: list || [],
        topicNames: (list || []).map((x) => x.name),
        topicIndex: 0,
        topicId: list && list.length ? list[0].id : null,
      });
    } catch (e) {
      this.setData({ topicList: [], topicNames: [], topicId: null });
    }
  },

  async loadDistricts() {
    const list = await request({ url: "/api/mp/admin/districts" });
    const names = (list || []).map((d) => d.name);
    this.setData({
      districtList: list || [],
      districtNames: names,
      districtIndex: 0,
      districtId: list && list.length ? list[0].id : null,
    });
    if (this.data.districtId) await this.loadOrgs();
  },

  async loadOrgs() {
    const { districtId } = this.data;
    if (!districtId) return;
    const list = await request({
      url: `/api/mp/admin/organizations?district_id=${districtId}&q=`,
    });
    const labels = (list || []).map((o) => {
      const typeName = this.data.orgTypeLabels[o.org_type] || o.org_type || "其他部门";
      return `${o.name}（${typeName}）`;
    });
    this.setData({
      orgList: list || [],
      orgLabels: labels,
      orgIndex: 0,
    });
  },

  async loadTrainings() {
    const list = await request({ url: "/api/mp/admin/trainings" });
    const trainings = (list || []).map((t) => ({
      ...t,
      start_at: (t.start_at || "").replace("T", " ").slice(0, 16),
    }));
    this.setData({ trainings });
  },

  onDistrictChange(e) {
    const idx = Number(e.detail.value);
    const d = this.data.districtList[idx];
    this.setData({ districtIndex: idx, districtId: d ? d.id : null });
    this.loadOrgs();
  },

  onOrgChange(e) {
    this.setData({ orgIndex: Number(e.detail.value) });
  },
  onTopicChange(e) {
    const idx = Number(e.detail.value);
    const topic = this.data.topicList[idx];
    this.setData({ topicIndex: idx, topicId: topic ? topic.id : null });
  },

  onTitle(e) {
    this.setData({ title: e.detail.value });
  },
  onDuration(e) {
    this.setData({ durationMinutes: e.detail.value });
  },
  onLocation(e) {
    this.setData({ location: e.detail.value });
  },

  async onCreate() {
    const { title, orgList, orgIndex, durationMinutes, location, topicId } = this.data;
    const org = orgList[orgIndex];
    if (!title.trim()) {
      wx.showToast({ title: "请输入标题", icon: "none" });
      return;
    }
    if (!org) {
      wx.showToast({ title: "请选择单位", icon: "none" });
      return;
    }
    this.setData({ creating: true });
    try {
      const data = await request({
        url: "/api/mp/admin/trainings/quick",
        method: "POST",
        data: {
          title: title.trim(),
          organization_id: org.id,
          topic_id: topicId || undefined,
          duration_minutes: Number(durationMinutes) || 60,
          location: (location || "").trim() || undefined,
        },
      });
      wx.showToast({ title: "已创建", icon: "success" });
      this.setData({ title: "", location: "" });
      await this.loadTrainings();
      this.showQrData(data);
    } catch (e) {
      wx.showToast({ title: e.message || "创建失败", icon: "none" });
    } finally {
      this.setData({ creating: false });
    }
  },

  async onShowQr(e) {
    const id = e.currentTarget.dataset.id;
    try {
      const data = await request({ url: `/api/mp/admin/trainings/${id}/qrcode-info` });
      this.showQrData(data);
    } catch (err) {
      wx.showToast({ title: err.message || "加载失败", icon: "none" });
    }
  },

  async onEndTraining(e) {
    const id = e.currentTarget.dataset.id;
    if (!id) return;
    wx.showModal({
      title: "提前结束",
      content: "结束后学员将不能再加入本场培训，确定继续吗？",
      success: async (res) => {
        if (!res.confirm) return;
        try {
          await request({
            url: `/api/mp/admin/trainings/${id}`,
            method: "PATCH",
            data: { is_active: false },
          });
          wx.showToast({ title: "已结束", icon: "success" });
          await this.loadTrainings();
        } catch (err) {
          wx.showToast({ title: err.message || "操作失败", icon: "none" });
        }
      },
    });
  },

  async onDeleteTraining(e) {
    const id = e.currentTarget.dataset.id;
    if (!id) return;
    wx.showModal({
      title: "删除培训",
      content: "删除后本场培训和签到记录都会被删除，确定继续吗？",
      success: async (res) => {
        if (!res.confirm) return;
        try {
          await request({
            url: `/api/mp/admin/trainings/${id}`,
            method: "DELETE",
          });
          wx.showToast({ title: "已删除", icon: "success" });
          await this.loadTrainings();
        } catch (err) {
          wx.showToast({ title: err.message || "删除失败", icon: "none" });
        }
      },
    });
  },

  showQrData(data) {
    this.setData({
      qrInfo: data,
      qrUrl: resolveQrUrl(data.qr_payload),
    });
  },

  copyQr() {
    const url = this.data.qrUrl;
    if (!url) return;
    wx.setClipboardData({
      data: url,
      success: () => wx.showToast({ title: "已复制", icon: "success" }),
    });
  },

  closeQr() {
    this.setData({ qrInfo: null, qrUrl: "" });
  },

  noop() {},

  goStats() {
    wx.navigateTo({ url: "/pages/admin/stats" });
  },
});
