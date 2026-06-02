const { request } = require("../../utils/request");

function formatMinutes(minutes) {
  const n = Number(minutes || 0);
  if (n >= 1440) {
    const days = Math.floor(n / 1440);
    const rest = n % 1440;
    return rest ? `${days}天${Math.round(rest / 60)}小时` : `${days}天`;
  }
  if (n >= 60) return `${Math.floor(n / 60)}小时${n % 60 ? `${n % 60}分` : ""}`;
  return `${n}分钟`;
}

Page({
  data: {
    loading: false,
    districts: [],
    selectedDistrictId: 0,
    selectedDistrictName: "",
    typeStats: [],
    totalMinutes: 0,
    totalMinutesText: "0分钟",
    sessionCount: 0,
  },

  onShow() {
    this.load();
  },

  async load() {
    this.setData({ loading: true });
    try {
      const districts = await request({ url: "/api/mp/admin/stats/by-district" });
      const list = (districts || []).map((d) => ({
        ...d,
        total_minutes_text: formatMinutes(d.total_minutes),
      }));
      const first = list[0];
      this.setData({
        districts: list,
        selectedDistrictId: this.data.selectedDistrictId || (first ? first.district_id : 0),
        selectedDistrictName: this.data.selectedDistrictName || (first ? first.district_name : ""),
      });
      if (this.data.selectedDistrictId) await this.loadTypes();
    } catch (e) {
      wx.showToast({ title: e.message || "加载失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  async loadTypes() {
    const districtId = this.data.selectedDistrictId;
    if (!districtId) return;
    const rows = await request({ url: `/api/mp/admin/stats/types-by-district?district_id=${districtId}` });
    const total = (rows || []).reduce((s, r) => s + Number(r.total_minutes || 0), 0);
    const typeStats = (rows || [])
      .filter((r) => r.total_minutes > 0 || r.organization_count > 0)
      .map((r) => ({
        ...r,
        total_minutes_text: formatMinutes(r.total_minutes),
        percent: total ? Math.round((Number(r.total_minutes || 0) / total) * 100) : 0,
      }));
    const district = this.data.districts.find((d) => Number(d.district_id) === Number(districtId));
    this.setData({
      typeStats,
      totalMinutes: district ? district.total_minutes : total,
      totalMinutesText: formatMinutes(district ? district.total_minutes : total),
      sessionCount: district ? district.session_count : 0,
    });
  },

  async onPickDistrict(e) {
    const id = Number(e.currentTarget.dataset.id);
    const d = this.data.districts.find((x) => Number(x.district_id) === id);
    this.setData({
      selectedDistrictId: id,
      selectedDistrictName: d ? d.district_name : "",
      typeStats: [],
    });
    await this.loadTypes();
  },

  formatMinutes,
});
