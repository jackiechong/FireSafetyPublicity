const { request } = require("../../utils/request");

const OTHER_ORG_FLAG = "__OTHER__";

Page({
  data: {
    districtList: [],
    districtNames: [],
    districtIndex: 0,
    districtId: null,

    orgList: [], // [{id, name, org_type}]
    orgPickerLabels: [], // 显示用：每行单位名 + 类型，最后一项「其他单位（手动添加）」
    orgIndex: -1,
    selectedOrg: null, // {id, name, org_type} 或 null
    showCustomOrg: false,
    customOrgName: "",
    customOrgType: "other_department",
    customOrgTypeIndex: 0,
    customOrgTypeOptions: ["应急", "教育", "民政", "文旅", "卫建", "商务", "工农业农村", "发改", "其他部门"],
    customOrgTypeValues: [
      "emergency",
      "education",
      "civil_affairs",
      "culture_tourism",
      "health",
      "commerce",
      "industry_agriculture",
      "development_reform",
      "other_department",
    ],

    name: "",
    phone: "",
    jobTitle: "",

    loading: false,
    redirectSessionId: 0,
  },

  async onLoad(options = {}) {
    const app = getApp();
    if (!app.globalData.token) {
      wx.redirectTo({ url: "/pages/index/index" });
      return;
    }
    this.setData({ redirectSessionId: Number(options.session_id || 0) });
    await this.loadDistricts();
  },

  async loadDistricts() {
    try {
      const list = await request({ url: "/api/mp/districts" });
      const names = (list || []).map((d) => d.name);
      this.setData({
        districtList: list || [],
        districtNames: names,
        districtIndex: 0,
        districtId: list && list.length ? list[0].id : null,
      });
      if (this.data.districtId) await this.loadOrgs();
    } catch (e) {
      wx.showToast({ title: e.message || "加载区县失败", icon: "none" });
    }
  },

  async loadOrgs() {
    const { districtId } = this.data;
    if (!districtId) return;
    try {
      const list = await request({
        url: `/api/mp/organizations?district_id=${districtId}&q=`,
      });
      const labels = (list || []).map(
        (o) => `${o.name}（${this.orgTypeName(o.org_type)}）`
      );
      labels.push("其他单位（手动添加）");
      this.setData({
        orgList: list || [],
        orgPickerLabels: labels,
        orgIndex: -1,
        selectedOrg: null,
        showCustomOrg: false,
        customOrgName: "",
      });
    } catch (e) {
      wx.showToast({ title: e.message || "加载单位失败", icon: "none" });
    }
  },

  onDistrictChange(e) {
    const idx = Number(e.detail.value);
    const d = this.data.districtList[idx];
    this.setData({
      districtIndex: idx,
      districtId: d ? d.id : null,
    });
    this.loadOrgs();
  },

  onOrgPick(e) {
    const idx = Number(e.detail.value);
    const isOther = idx === this.data.orgList.length;
    if (isOther) {
      this.setData({
        orgIndex: idx,
        selectedOrg: { id: OTHER_ORG_FLAG, name: "其他单位（手动添加）", org_type: "other_department" },
        showCustomOrg: true,
      });
    } else {
      const o = this.data.orgList[idx];
      this.setData({
        orgIndex: idx,
        selectedOrg: o ? { id: o.id, name: o.name, org_type: o.org_type } : null,
        showCustomOrg: false,
        customOrgName: "",
      });
    }
  },

  onCustomOrgName(e) {
    this.setData({ customOrgName: e.detail.value });
  },

  onCustomOrgTypeChange(e) {
    const idx = Number(e.detail.value);
    this.setData({
      customOrgTypeIndex: idx,
      customOrgType: this.data.customOrgTypeValues[idx] || "other_department",
    });
  },

  orgTypeName(value) {
    const idx = this.data.customOrgTypeValues.indexOf(value);
    return idx >= 0 ? this.data.customOrgTypeOptions[idx] : "其他部门";
  },

  onName(e) {
    this.setData({ name: e.detail.value });
  },
  onPhone(e) {
    this.setData({ phone: e.detail.value });
  },
  onJobTitle(e) {
    this.setData({ jobTitle: e.detail.value });
  },

  async submit() {
    const {
      name,
      phone,
      districtId,
      selectedOrg,
      jobTitle,
      showCustomOrg,
      customOrgName,
      customOrgType,
    } = this.data;
    if (!districtId) {
      wx.showToast({ title: "请选择区县", icon: "none" });
      return;
    }
    if (!selectedOrg) {
      wx.showToast({ title: "请选择所在单位", icon: "none" });
      return;
    }
    const cleanPhone = String(phone || "").trim();
    if (!name.trim()) {
      wx.showToast({ title: "请填写姓名", icon: "none" });
      return;
    }
    if (!/^1\d{10}$/.test(cleanPhone)) {
      wx.showToast({ title: "输入号码有误，请重新输入", icon: "none" });
      return;
    }
    if (showCustomOrg && !customOrgName.trim()) {
      wx.showToast({ title: "请输入新单位名称", icon: "none" });
      return;
    }
    this.setData({ loading: true });
    try {
      let organization_id = selectedOrg.id;
      if (showCustomOrg) {
        const created = await request({
          url: "/api/mp/organizations",
          method: "POST",
          data: {
            district_id: districtId,
            name: customOrgName.trim(),
            org_type: customOrgType,
          },
        });
        organization_id = created.id;
      }
      await request({
        url: "/api/mp/profile",
        method: "POST",
        data: {
          name: name.trim(),
          phone: cleanPhone,
          district_id: districtId,
          organization_id,
          job_title: jobTitle.trim() || undefined,
        },
      });
      wx.showToast({ title: "注册成功" });
      const target = this.data.redirectSessionId
        ? `/pages/checkin/checkin?session_id=${this.data.redirectSessionId}`
        : "/pages/me/me";
      setTimeout(() => wx.redirectTo({ url: target }), 400);
    } catch (e) {
      wx.showToast({ title: e.message || "保存失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },
});
