const { request } = require("../../utils/request");

const PIE_COLORS = ["#3949ab", "#00897b", "#f9a825", "#d81b60", "#5e35b1", "#039be5", "#7cb342", "#fb8c00", "#6d4c41"];

function pad(n) {
  return String(n).padStart(2, "0");
}

function dateValue(d = new Date()) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function formatHours(minutes) {
  return `${(Number(minutes || 0) / 60).toFixed(1)}小时`;
}

function formatDateTime(value) {
  if (!value) return "";
  return String(value).replace("T", " ").slice(0, 16);
}

function periodBounds(mode, value) {
  const parts = String(value || dateValue()).split("-").map(Number);
  const y = parts[0] || new Date().getFullYear();
  const m = parts[1] || 1;
  const d = parts[2] || 1;
  const start = new Date(y, mode === "year" ? 0 : m - 1, mode === "date" ? d : 1);
  const end = new Date(start);
  if (mode === "year") end.setFullYear(start.getFullYear() + 1);
  else if (mode === "month") end.setMonth(start.getMonth() + 1);
  else end.setDate(start.getDate() + 1);
  return {
    start: `${start.getFullYear()}-${pad(start.getMonth() + 1)}-${pad(start.getDate())}T00:00:00`,
    end: `${end.getFullYear()}-${pad(end.getMonth() + 1)}-${pad(end.getDate())}T00:00:00`,
  };
}

function normalizePickerValue(mode, value) {
  const raw = String(value || dateValue());
  if (mode === "year") return `${raw.slice(0, 4)}-01-01`;
  if (mode === "month") return `${raw.slice(0, 7)}-01`;
  return raw.length >= 10 ? raw.slice(0, 10) : dateValue();
}

function withPeriod(url, mode, value, extra = {}) {
  const params = { ...extra, ...periodBounds(mode, value) };
  const qs = Object.keys(params)
    .filter((k) => params[k] !== undefined && params[k] !== null && params[k] !== "")
    .map((k) => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`)
    .join("&");
  return `${url}?${qs}`;
}

function isNotFound(e) {
  return String((e && e.message) || e || "").toLowerCase().includes("not found");
}

function mergeTypeRows(groups) {
  const map = {};
  (groups || []).flat().forEach((row) => {
    const key = row.org_type_name || row.org_type || "其他部门";
    if (!map[key]) {
      map[key] = {
        org_type: row.org_type || key,
        org_type_name: key,
        total_minutes: 0,
        person_count: 0,
        organization_count: 0,
      };
    }
    map[key].total_minutes += Number(row.total_minutes || 0);
    map[key].person_count += Number(row.person_count || 0);
    map[key].organization_count += Number(row.organization_count || 0);
  });
  return Object.keys(map).sort().map((key) => map[key]);
}

Page({
  data: {
    loading: false,
    periodMode: "year",
    periodValue: dateValue(),
    periodLabel: "",
    periodFields: "year",
    districts: [],
    selectedDistrictId: 0,
    selectedDistrictName: "",
    typeStats: [],
    orgRows: [],
    selectedOrgId: 0,
    selectedOrgName: "",
    personRows: [],
    selectedPersonId: 0,
    selectedPersonName: "",
    trainingRows: [],
    totalMinutes: 0,
    totalMinutesText: "0.0小时",
    sessionCount: 0,
  },

  onShow() {
    this.syncPeriodUi();
    this.load();
  },

  syncPeriodUi() {
    const mode = this.data.periodMode;
    const value = normalizePickerValue(mode, this.data.periodValue || dateValue());
    const [y, m, d] = value.split("-");
    const label = mode === "year" ? `${y}年` : mode === "month" ? `${y}年${m}月` : `${y}年${m}月${d}日`;
    this.setData({
      periodLabel: label,
      periodFields: mode === "year" ? "year" : mode === "month" ? "month" : "day",
    });
  },

  async load() {
    this.setData({ loading: true });
    try {
      const districts = await request({
        url: withPeriod("/api/mp/admin/stats/by-district", this.data.periodMode, this.data.periodValue),
      });
      const districtRows = (districts || []).map((d) => ({
        ...d,
        total_minutes_text: formatHours(d.total_minutes),
      }));
      const cityMinutes = districtRows.reduce((s, d) => s + Number(d.total_minutes || 0), 0);
      const citySessions = districtRows.reduce((s, d) => s + Number(d.session_count || 0), 0);
      const list = [
        {
          district_id: 0,
          district_name: "葫芦岛市",
          total_minutes: cityMinutes,
          session_count: citySessions,
          total_minutes_text: formatHours(cityMinutes),
        },
        ...districtRows,
      ];
      const first = list[0];
      const currentStillExists = list.some((d) => Number(d.district_id) === Number(this.data.selectedDistrictId));
      const selected = currentStillExists
        ? list.find((d) => Number(d.district_id) === Number(this.data.selectedDistrictId))
        : first;
      this.setData({
        districts: list,
        selectedDistrictId: selected ? selected.district_id : 0,
        selectedDistrictName: selected ? selected.district_name : "葫芦岛市",
        selectedOrgId: 0,
        selectedOrgName: "",
        selectedPersonId: 0,
        selectedPersonName: "",
        personRows: [],
        trainingRows: [],
      });
      await this.loadDistrictDetail();
    } catch (e) {
      wx.showToast({ title: e.message || "加载失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  async loadDistrictDetail() {
    const districtId = this.data.selectedDistrictId;
    let types = [];
    try {
      types = await request({
        url: withPeriod("/api/mp/admin/stats/types-by-district", this.data.periodMode, this.data.periodValue, {
          district_id: districtId,
        }),
      });
    } catch (e) {
      if (Number(districtId) !== 0) throw e;
    }
    if (Number(districtId) === 0 && !(types || []).some((r) => Number(r.total_minutes || 0) > 0)) {
      types = await this.loadCitywideTypesFallback();
    }
    let orgs = [];
    try {
      orgs = await request({
        url: withPeriod("/api/mp/admin/stats/orgs-by-district", this.data.periodMode, this.data.periodValue, {
          district_id: districtId,
        }),
      });
    } catch (e) {
      if (isNotFound(e)) {
        wx.showToast({ title: "后端未更新，请重启服务器后端", icon: "none" });
      } else {
        wx.showToast({ title: e.message || "单位数据加载失败", icon: "none" });
      }
    }
    const total = (types || []).reduce((s, r) => s + Number(r.total_minutes || 0), 0);
    const typeStats = (types || [])
      .filter((r) => r.total_minutes > 0)
      .map((r, i) => ({
        ...r,
        color: PIE_COLORS[i % PIE_COLORS.length],
        total_minutes_text: formatHours(r.total_minutes),
        percent: total ? Math.round((Number(r.total_minutes || 0) / total) * 100) : 0,
      }));
    const orgRows = (orgs || [])
      .filter((o) => Number(o.total_minutes || 0) > 0 || Number(o.person_count || 0) > 0)
      .map((o) => ({ ...o, total_minutes_text: formatHours(o.total_minutes) }));
    const district = this.data.districts.find((d) => Number(d.district_id) === Number(districtId));
    this.setData({
      typeStats,
      orgRows,
      totalMinutes: district ? district.total_minutes : total,
      totalMinutesText: formatHours(district ? district.total_minutes : total),
      sessionCount: district ? district.session_count : 0,
      selectedOrgId: 0,
      selectedOrgName: "",
      selectedPersonId: 0,
      selectedPersonName: "",
      personRows: [],
      trainingRows: [],
    });
    this.drawPie();
  },

  async loadCitywideTypesFallback() {
    const rows = this.data.districts.filter((d) => Number(d.district_id) !== 0);
    const groups = [];
    for (let i = 0; i < rows.length; i += 1) {
      try {
        const data = await request({
          url: withPeriod("/api/mp/admin/stats/types-by-district", this.data.periodMode, this.data.periodValue, {
            district_id: rows[i].district_id,
          }),
        });
        groups.push(data || []);
      } catch (e) {
        // 单个县区失败不影响全市兜底汇总。
      }
    }
    return mergeTypeRows(groups);
  },

  drawPie() {
    const rows = this.data.typeStats;
    const ctx = wx.createCanvasContext("typePie", this);
    ctx.clearRect(0, 0, 320, 240);
    const total = rows.reduce((s, r) => s + Number(r.total_minutes || 0), 0);
    const cx = 160;
    const cy = 112;
    const radius = 82;
    if (!total) {
      ctx.setFillStyle("#999");
      ctx.setFontSize(14);
      ctx.fillText("暂无时长数据", 116, 116);
      ctx.draw();
      return;
    }
    let start = -Math.PI / 2;
    rows.forEach((r) => {
      const angle = (Number(r.total_minutes || 0) / total) * Math.PI * 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, radius, start, start + angle);
      ctx.closePath();
      ctx.setFillStyle(r.color);
      ctx.fill();
      start += angle;
    });
    ctx.beginPath();
    ctx.arc(cx, cy, 42, 0, Math.PI * 2);
    ctx.setFillStyle("#fff");
    ctx.fill();
    ctx.setFillStyle("#1a237e");
    ctx.setFontSize(13);
    ctx.fillText("类型占比", 134, 116);
    ctx.draw();
  },

  async onPeriodMode(e) {
    const mode = e.currentTarget.dataset.mode;
    this.setData({
      periodMode: mode,
      periodValue: normalizePickerValue(mode, this.data.periodValue),
    });
    this.syncPeriodUi();
    await this.load();
  },

  async onPeriodPick(e) {
    this.setData({ periodValue: normalizePickerValue(this.data.periodMode, e.detail.value) });
    this.syncPeriodUi();
    await this.load();
  },

  async onPickDistrict(e) {
    const id = Number(e.currentTarget.dataset.id);
    const d = this.data.districts.find((x) => Number(x.district_id) === id);
    this.setData({
      selectedDistrictId: id,
      selectedDistrictName: d ? d.district_name : "",
      typeStats: [],
      orgRows: [],
      selectedOrgId: 0,
      selectedOrgName: "",
      personRows: [],
      selectedPersonId: 0,
      selectedPersonName: "",
      trainingRows: [],
    });
    await this.loadDistrictDetail();
  },

  async onPickOrg(e) {
    const id = Number(e.currentTarget.dataset.id);
    const org = this.data.orgRows.find((x) => Number(x.organization_id) === id);
    this.setData({
      selectedOrgId: id,
      selectedOrgName: org ? org.organization_name : "",
      selectedPersonId: 0,
      selectedPersonName: "",
      personRows: [],
      trainingRows: [],
    });
    try {
      const persons = await request({
        url: withPeriod("/api/mp/admin/stats/persons-by-organization", this.data.periodMode, this.data.periodValue, {
          organization_id: id,
        }),
      });
      this.setData({
        personRows: (persons || []).map((p) => ({
          ...p,
          total_minutes_text: formatHours(p.total_minutes),
        })),
      });
    } catch (e) {
      wx.showToast({ title: isNotFound(e) ? "后端未更新，请重启服务器后端" : e.message || "人员数据加载失败", icon: "none" });
    }
  },

  async onPickPerson(e) {
    const id = Number(e.currentTarget.dataset.id);
    const person = this.data.personRows.find((x) => Number(x.person_id) === id);
    this.setData({
      selectedPersonId: id,
      selectedPersonName: person ? person.name : "",
      trainingRows: [],
    });
    try {
      const rows = await request({
        url: withPeriod("/api/mp/admin/stats/person-trainings", this.data.periodMode, this.data.periodValue, {
          person_id: id,
        }),
      });
      this.setData({
        trainingRows: (rows || []).map((r) => ({
          ...r,
          start_text: formatDateTime(r.start_at),
          duration_text: formatHours(r.duration_minutes),
        })),
      });
    } catch (e) {
      wx.showToast({ title: isNotFound(e) ? "后端未更新，请重启服务器后端" : e.message || "场次数据加载失败", icon: "none" });
    }
  },
});
