const { request } = require("../../utils/request");

Page({
  data: {
    districtList: [],
    districtNames: [],
    districtIndex: 0,
    districtId: null,

    orgList: [],
    orgKeyword: "",
    selectedOrg: null,
    customOrgType: "other_department",
    customOrgTypeIndex: 0,
    customOrgTypeOptions: [],
    customOrgTypeValues: [],

    jobTitleOptions: [],
    jobTitleIndex: -1,
    jobTitle: "",

    name: "",
    phone: "",

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
    await Promise.all([this.loadDictionaries(), this.loadDistricts()]);
  },

  async loadDictionaries() {
    try {
      const [types, titles] = await Promise.all([
        request({ url: "/api/mp/org-types" }),
        request({ url: "/api/mp/job-titles" }),
      ]);
      const typeRows = types && types.length ? types : [{ code: "other_department", name: "其他部门" }];
      this.setData({
        customOrgTypeOptions: typeRows.map((x) => x.name),
        customOrgTypeValues: typeRows.map((x) => x.code),
        customOrgType: typeRows[0].code || "other_department",
        customOrgTypeIndex: 0,
        jobTitleOptions: (titles || []).map((x) => x.name),
      });
    } catch (e) {
      wx.showToast({ title: e.message || "加载类型失败", icon: "none" });
    }
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
      if (this.data.districtId) await this.loadOrgs("");
    } catch (e) {
      wx.showToast({ title: e.message || "加载区县失败", icon: "none" });
    }
  },

  async loadOrgs(keyword) {
    const { districtId } = this.data;
    if (!districtId) return;
    try {
      const q = encodeURIComponent(String(keyword || "").trim());
      const list = await request({
        url: `/api/mp/organizations?district_id=${districtId}&q=${q}`,
      });
      this.setData({ orgList: list || [] });
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
      orgKeyword: "",
      selectedOrg: null,
      orgList: [],
    });
    this.loadOrgs("");
  },

  onOrgInput(e) {
    const value = e.detail.value;
    this.setData({ orgKeyword: value, selectedOrg: null });
    this.loadOrgs(value);
  },

  onPickOrg(e) {
    const id = Number(e.currentTarget.dataset.id);
    const org = this.data.orgList.find((x) => Number(x.id) === id);
    if (!org) return;
    this.setData({
      selectedOrg: org,
      orgKeyword: org.name,
    });
  },

  onCustomOrgTypeChange(e) {
    const idx = Number(e.detail.value);
    this.setData({
      customOrgTypeIndex: idx,
      customOrgType: this.data.customOrgTypeValues[idx] || "other_department",
    });
  },

  onJobTitleChange(e) {
    const idx = Number(e.detail.value);
    this.setData({
      jobTitleIndex: idx,
      jobTitle: this.data.jobTitleOptions[idx] || "",
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

  async submit() {
    const {
      name,
      phone,
      districtId,
      selectedOrg,
      orgKeyword,
      jobTitle,
      customOrgType,
    } = this.data;
    if (!districtId) {
      wx.showToast({ title: "请选择区县", icon: "none" });
      return;
    }
    const cleanOrgName = String(orgKeyword || "").trim();
    if (!cleanOrgName) {
      wx.showToast({ title: "请输入所在单位", icon: "none" });
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
    if (!String(jobTitle || "").trim()) {
      wx.showToast({ title: "请选择职务/岗位", icon: "none" });
      return;
    }
    this.setData({ loading: true });
    try {
      let organization_id = selectedOrg && selectedOrg.name === cleanOrgName ? selectedOrg.id : 0;
      if (!organization_id) {
        const created = await request({
          url: "/api/mp/organizations",
          method: "POST",
          data: {
            district_id: districtId,
            name: cleanOrgName,
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
          job_title: jobTitle.trim(),
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
