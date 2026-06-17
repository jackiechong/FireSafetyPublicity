<template>
  <div class="page">
    <h2>统计数据</h2>
    <p class="tip">
      默认查看葫芦岛地区年度培训时长；可按年、月、日切换周期，场次和时长随选择同步变化。
    </p>

    <el-form :inline="true" class="period-toolbar">
      <el-form-item label="统计周期">
        <el-radio-group v-model="periodMode" @change="onPeriodModeChange">
          <el-radio-button label="year">年</el-radio-button>
          <el-radio-button label="month">月</el-radio-button>
          <el-radio-button label="date">日</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item>
        <el-date-picker
          v-model="periodValue"
          :type="periodMode"
          :clearable="false"
          :format="periodFormat"
          :value-format="periodValueFormat"
          placeholder="选择时间"
          style="width: 170px"
          @change="onPeriodChange"
        />
      </el-form-item>
    </el-form>

    <div class="search-bar">
      <el-autocomplete
        v-model="searchQ"
        :fetch-suggestions="querySearch"
        clearable
        highlight-first-item
        :debounce="250"
        popper-class="stats-search-suggest-popper"
        placeholder="搜索单位名称，或人员姓名 / 手机号"
        style="width: min(100%, 520px)"
        value-key="value"
        fit-input-width
        @select="handleSearchSelect"
      >
        <template #default="{ item }">
          <div class="ac-item">
            <el-tag size="small" :type="item.kind === 'organization' ? 'primary' : 'success'" effect="plain">
              {{ item.kind === "organization" ? "单位" : "人员" }}
            </el-tag>
            <span class="ac-title">{{ item.title }}</span>
            <div class="ac-sub">{{ item.subtitle }}</div>
          </div>
        </template>
      </el-autocomplete>
    </div>

    <el-row :gutter="16" class="summary-row">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="sum-card">
          <div class="sum-label">{{ districtFilter ? "当前区县培训时长" : "全市培训总时长" }}</div>
          <div class="sum-value">{{ displayTotalMinutesLabel }}</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="sum-card">
          <div class="sum-label">{{ districtFilter ? "当前区县培训场次" : "全市培训场次" }}</div>
          <div class="sum-value">{{ displaySessionCount }}</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="sum-card">
          <div class="sum-label">{{ districtFilter ? "涉及类型数" : "涉及区县数" }}</div>
          <div class="sum-value">{{ displayExtra }}</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="sum-card">
          <div class="sum-label">选中单位参训人数</div>
          <div class="sum-value">{{ orgPersonRows.length || "—" }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-form :inline="true" class="toolbar">
      <el-form-item label="区县">
        <el-select
          v-model="districtFilter"
          clearable
          placeholder="不选：全市区县对比"
          style="width: 220px"
          @change="onDistrictChange"
        >
          <el-option v-for="d in districtOptions" :key="d.id" :label="d.name" :value="d.id" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="false" label="单位">
        <el-select
          v-model="orgFilter"
          clearable
          filterable
          placeholder="选择单位查看参训人员"
          style="width: min(100%, 360px)"
          @change="onOrgChange"
        >
          <el-option
            v-for="o in orgsInDistrict"
            :key="o.organization_id"
            :label="`${o.organization_name}（${formatTrainingHours(o.total_minutes)} · ${o.person_count}人）`"
            :value="o.organization_id"
          />
        </el-select>
      </el-form-item>
    </el-form>

    <div ref="chartRef" class="chart" />

    <template v-if="districtFilter && orgFilter">
      <h3 class="sub-title">该单位参训人员（共 {{ orgPersonRows.length }} 人）</h3>
      <el-table :data="orgPersonRows" border stripe v-loading="orgPersonLoading" size="small" style="width: 100%">
        <el-table-column type="index" label="#" width="55" />
        <el-table-column prop="name" label="姓名" width="110" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="session_count" label="参训次数" width="100" />
        <el-table-column label="累计时长" min-width="140">
          <template #default="{ row }">
            {{ formatTrainingHours(row.total_minutes) }}
          </template>
        </el-table-column>
        <el-table-column v-if="canRebindPersons" label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openPersonRebind(row)">重绑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <el-dialog v-model="personRebindVisible" title="重新绑定人员身份" width="520px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="姓名">
          <el-input v-model="personRebindForm.name" maxlength="64" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="personRebindForm.phone" maxlength="11" />
        </el-form-item>
        <el-form-item label="区县">
          <el-select v-model="personRebindForm.district_id" style="width: 100%" disabled>
            <el-option v-for="d in districtOptions" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="单位">
          <el-select v-model="personRebindForm.organization_id" filterable style="width: 100%">
            <el-option
              v-for="o in orgsInDistrict"
              :key="o.organization_id"
              :label="o.organization_name"
              :value="o.organization_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="身份">
          <el-input v-model="personRebindForm.job_title" maxlength="64" placeholder="如：消防安全管理人" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="personRebindVisible = false">取消</el-button>
        <el-button type="primary" :loading="personRebindSaving" @click="submitPersonRebind">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from "vue";
import * as echarts from "echarts";
import { ElMessage } from "element-plus";
import http from "../api/http";
import { formatMinutesAxisHours, formatTrainingHours } from "../utils/duration";

const chartRef = ref(null);
let chart;

const searchQ = ref("");
const districtOptions = ref([]);
const districtData = ref([]);
const districtFilter = ref();
const orgsInDistrict = ref([]);
const typeStatsInDistrict = ref([]);
const orgFilter = ref();
const orgPersonRows = ref([]);
const orgPersonLoading = ref(false);
const currentAdmin = ref(null);
const personRebindVisible = ref(false);
const personRebindSaving = ref(false);
const personRebindId = ref(null);
const personRebindForm = reactive({
  name: "",
  phone: "",
  district_id: undefined,
  organization_id: undefined,
  job_title: "",
});
/** 仅在 stats/search-suggest 404（旧版后端）时提示一次 */
const searchLegacyHintShown = ref(false);
const periodMode = ref("year");
const periodValue = ref(new Date());

const canRebindPersons = computed(() => currentAdmin.value?.role === "detachment");

const periodFormat = computed(() => {
  if (periodMode.value === "year") return "YYYY年";
  if (periodMode.value === "month") return "YYYY年MM月";
  return "YYYY年MM月DD日";
});

const periodValueFormat = computed(() => {
  if (periodMode.value === "year") return "YYYY";
  if (periodMode.value === "month") return "YYYY-MM";
  return "YYYY-MM-DD";
});

const displayTotalMinutes = computed(() => {
  if (districtFilter.value) {
    return typeStatsInDistrict.value.reduce((s, o) => s + o.total_minutes, 0);
  }
  return districtData.value.reduce((s, d) => s + d.total_minutes, 0);
});

const displayTotalMinutesLabel = computed(() => formatTrainingHours(displayTotalMinutes.value));

const displaySessionCount = computed(() => {
  if (districtFilter.value != null && districtFilter.value !== "" && Number(districtFilter.value) > 0) {
    const did = Number(districtFilter.value);
    const d = districtData.value.find((x) => Number(x.district_id) === did);
    return d ? d.session_count : "—";
  }
  return districtData.value.reduce((s, d) => s + d.session_count, 0);
});

const displayExtra = computed(() => {
  if (districtFilter.value) {
    return typeStatsInDistrict.value.filter((x) => x.total_minutes > 0 || x.organization_count > 0).length;
  }
  return districtData.value.filter((d) => d.total_minutes > 0 || d.session_count > 0).length;
});

function normalizePeriodValue() {
  if (periodValue.value instanceof Date) return periodValue.value;
  const raw = String(periodValue.value || "");
  if (periodMode.value === "year") return new Date(Number(raw), 0, 1);
  if (periodMode.value === "month") {
    const [y, m] = raw.split("-").map(Number);
    return new Date(y, (m || 1) - 1, 1);
  }
  const [y, m, d] = raw.split("-").map(Number);
  return new Date(y, (m || 1) - 1, d || 1);
}

function apiDate(dt) {
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, "0");
  const d = String(dt.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}T00:00:00`;
}

function statsParams(extra = {}) {
  const start = normalizePeriodValue();
  const end = new Date(start);
  if (periodMode.value === "year") end.setFullYear(start.getFullYear() + 1);
  else if (periodMode.value === "month") end.setMonth(start.getMonth() + 1);
  else end.setDate(start.getDate() + 1);
  return {
    ...extra,
    start: apiDate(start),
    end: apiDate(end),
  };
}

/** Element Plus 会 await 该函数，并在拿到返回值后调用内部 cb；失败时须返回 [] 以结束 loading */
async function querySearch(queryString) {
  const q = (queryString || "").trim();
  if (q.length < 1) return [];
  try {
    const { data } = await http.get("/api/admin/stats/search-suggest", {
      params: { q, limit: 20 },
    });
    return (data || []).map((x) => ({ ...x, value: x.title }));
  } catch (e) {
    const status = e?.response?.status;
    if (status === 401) return [];

    // 旧版 uvicorn 未加载新路由时，search-suggest 为 404；改用已有「按名称筛选单位」接口
    if (status === 404) {
      if (!searchLegacyHintShown.value) {
        searchLegacyHintShown.value = true;
        ElMessage.warning({
          message:
            "后端仍是旧进程（统计搜索接口不存在）。已改为仅按单位名称联想；请在 backend 目录结束旧 uvicorn 后重新启动，以启用人员搜索等接口。",
          duration: 8000,
          showClose: true,
        });
      }
      try {
        const { data: orgs } = await http.get("/api/admin/organizations", { params: { q } });
        return (orgs || []).slice(0, 20).map((o) => {
          const dname =
            districtOptions.value.find((x) => Number(x.id) === Number(o.district_id))?.name || "";
          const ot = "其他部门";
          return {
            kind: "organization",
            id: o.id,
            title: o.name,
            subtitle: `${dname} · ${ot}`,
            organization_id: o.id,
            district_id: o.district_id,
            value: o.name,
          };
        });
      } catch (e2) {
        console.error(e2);
        ElMessage.error("单位联想失败，请确认后端已启动且可访问 /api/admin/organizations");
        return [];
      }
    }

    console.error(e);
    if (!e?.response) {
      ElMessage.error("无法连接后端 API（默认端口 18080）。请在 backend 目录启动 uvicorn 后刷新页面。");
    } else {
      ElMessage.error(`搜索失败（HTTP ${status}）`);
    }
    return [];
  }
}

async function loadOrgsForDistrict() {
  if (districtFilter.value == null || districtFilter.value === "") {
    orgsInDistrict.value = [];
    typeStatsInDistrict.value = [];
    return;
  }
  const did = Number(districtFilter.value);
  try {
    const { data: orgList } = await http.get("/api/admin/organizations", {
      params: { district_id: did },
    });
    let statsMap = new Map();
    try {
      const { data: statsList } = await http.get("/api/admin/stats/orgs-by-district", {
        params: statsParams({ district_id: did }),
      });
      statsMap = new Map((statsList || []).map((x) => [x.organization_id, x]));
    } catch (statsErr) {
      console.warn("orgs-by-district stats failed, showing orgs with zero stats", statsErr);
    }
    orgsInDistrict.value = (orgList || []).map((o) => {
      const s = statsMap.get(o.id);
      return {
        organization_id: o.id,
        organization_name: o.name,
        total_minutes: s?.total_minutes ?? 0,
        person_count: s?.person_count ?? 0,
      };
    });
    const { data: typeStats } = await http.get("/api/admin/stats/types-by-district", {
      params: statsParams({ district_id: did }),
    });
    typeStatsInDistrict.value = typeStats || [];
  } catch (e) {
    console.error(e);
    orgsInDistrict.value = [];
    typeStatsInDistrict.value = [];
  }
}

async function handleSearchSelect(item) {
  searchQ.value = "";
  const applyOrg = async () => {
    await loadOrgsForDistrict();
    orgFilter.value = item.organization_id;
    await onOrgChange();
    await renderChart();
  };

  if (item.kind === "organization") {
    if (item.district_id == null) {
      ElMessage.warning("未找到区县信息");
      return;
    }
    districtFilter.value = Number(item.district_id);
    await applyOrg();
    return;
  }

  if (item.kind === "person") {
    if (item.district_id == null || item.organization_id == null) {
      ElMessage.warning("该人员未关联区县或单位，无法跳转");
      return;
    }
    districtFilter.value = Number(item.district_id);
    await applyOrg();
  }
}

async function loadDistrictsMeta() {
  const { data } = await http.get("/api/admin/districts");
  districtOptions.value = [{ id: 0, name: "葫芦岛支队" }, ...(data || [])];
}

async function loadCurrentAdmin() {
  const { data } = await http.get("/api/admin/me");
  currentAdmin.value = data;
}

async function loadDistrictStats() {
  const { data } = await http.get("/api/admin/stats/by-district", { params: statsParams() });
  districtData.value = data;
}

function renderBarChart() {
  if (!chartRef.value) return;
  if (!chart) chart = echarts.init(chartRef.value);
  const list = districtData.value.length ? districtData.value : [];
  const names = list.map((d) => d.district_name);
  const vals = list.map((d) => d.total_minutes);
  chart.setOption(
    {
      title: { text: "各区县培训时长对比", left: "center", textStyle: { fontSize: 16 } },
      tooltip: {
        trigger: "axis",
        formatter: (items) => {
          const p = items[0];
          return `${p.name}<br/>${formatTrainingHours(p.value)}`;
        },
      },
      grid: { left: 56, right: 24, bottom: 88, top: 48 },
      xAxis: {
        type: "category",
        data: names,
        axisTick: { show: false, alignWithLabel: true },
        axisLine: { lineStyle: { color: "#ddd" } },
        axisLabel: {
          rotate: 0,
          interval: 0,
          fontSize: 12,
          lineHeight: 16,
          formatter: (name) => {
            const s = String(name);
            if (s.length <= 6) return s;
            const m = Math.ceil(s.length / 2);
            return `${s.slice(0, m)}\n${s.slice(m)}`;
          },
        },
      },
      yAxis: {
        type: "value",
        name: "",
        axisLabel: {
          formatter: (v) => formatMinutesAxisHours(v),
        },
      },
      series: [
        {
          type: "bar",
          data: vals,
          itemStyle: { color: "#3949ab" },
          barMaxWidth: 40,
          barCategoryGap: "32%",
          label: { show: false },
        },
      ],
    },
    { notMerge: true }
  );
}

function renderOrgPie() {
  if (!chartRef.value) return;
  if (!chart) chart = echarts.init(chartRef.value);
  const list = typeStatsInDistrict.value.filter((o) => o.total_minutes > 0);
  const did = districtFilter.value != null ? Number(districtFilter.value) : NaN;
  const distName = districtOptions.value.find((d) => Number(d.id) === did)?.name || "";
  if (!list.length) {
    chart.setOption(
      {
        title: {
          text: `${distName} — 暂无类型培训时长数据`,
          left: "center",
          subtext: "该区县暂无参训记录，或时长均为 0",
          textStyle: { fontSize: 16 },
        },
        tooltip: { trigger: "item" },
        series: [{ type: "pie", radius: ["38%", "65%"], data: [] }],
      },
      { notMerge: true }
    );
    return;
  }
  chart.setOption(
    {
      title: {
        text: `${distName} — 各类型培训时长占比`,
        left: "center",
        textStyle: { fontSize: 16 },
      },
      tooltip: {
        trigger: "item",
        formatter: (p) => `${p.name}<br/>${formatTrainingHours(p.value)} (${p.percent}%)`,
      },
      legend: { bottom: 0, type: "scroll" },
      series: [
        {
          type: "pie",
          radius: ["38%", "65%"],
          data: list.map((o) => ({ name: o.org_type_name, value: o.total_minutes })),
          emphasis: {
            itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: "rgba(0,0,0,0.2)" },
          },
        },
      ],
    },
    { notMerge: true }
  );
}

async function renderChart() {
  await nextTick();
  if (!districtFilter.value) {
    renderBarChart();
  } else {
    renderOrgPie();
  }
}

async function onDistrictChange() {
  orgFilter.value = undefined;
  orgPersonRows.value = [];
  if (!districtFilter.value) {
    await loadDistrictStats();
    await renderChart();
    return;
  }
  await loadOrgsForDistrict();
  await renderChart();
}

async function onPeriodChange() {
  orgPersonRows.value = [];
  await loadDistrictStats();
  if (districtFilter.value) {
    await loadOrgsForDistrict();
  }
  if (orgFilter.value) {
    await onOrgChange();
  }
  await renderChart();
}

async function onPeriodModeChange() {
  periodValue.value = new Date();
  await onPeriodChange();
}

async function onOrgChange() {
  orgPersonRows.value = [];
  if (!orgFilter.value) return;
  orgPersonLoading.value = true;
  try {
    const { data } = await http.get("/api/admin/stats/persons-by-organization", {
      params: statsParams({ organization_id: Number(orgFilter.value) }),
    });
    orgPersonRows.value = data;
  } finally {
    orgPersonLoading.value = false;
  }
}

function openPersonRebind(row) {
  personRebindId.value = row.person_id;
  personRebindForm.name = row.name || "";
  personRebindForm.phone = row.phone || "";
  personRebindForm.district_id = Number(districtFilter.value);
  personRebindForm.organization_id = Number(orgFilter.value);
  personRebindForm.job_title = "";
  personRebindVisible.value = true;
}

async function submitPersonRebind() {
  if (!personRebindId.value) return;
  if (!personRebindForm.name.trim()) {
    ElMessage.warning("请填写姓名");
    return;
  }
  if (!/^1\d{10}$/.test(String(personRebindForm.phone || "").trim())) {
    ElMessage.warning("输入号码有误，请重新输入");
    return;
  }
  if (!personRebindForm.district_id || !personRebindForm.organization_id) {
    ElMessage.warning("请选择区县和单位");
    return;
  }
  personRebindSaving.value = true;
  try {
    await http.patch(`/api/admin/persons/${personRebindId.value}/rebind`, {
      name: personRebindForm.name.trim(),
      phone: String(personRebindForm.phone || "").trim(),
      district_id: Number(personRebindForm.district_id),
      organization_id: Number(personRebindForm.organization_id),
      job_title: personRebindForm.job_title.trim() || undefined,
    });
    ElMessage.success("人员身份已重新绑定");
    personRebindVisible.value = false;
    await onOrgChange();
  } catch (e) {
    console.error(e);
  } finally {
    personRebindSaving.value = false;
  }
}

onMounted(async () => {
  await loadCurrentAdmin();
  await loadDistrictsMeta();
  await loadDistrictStats();
  await renderChart();
  window.addEventListener("resize", () => chart?.resize());
});

onUnmounted(() => {
  chart?.dispose();
  chart = null;
});
</script>

<style scoped>
.page {
  background: #fff;
  padding: 20px 24px;
  border-radius: 8px;
  min-height: 400px;
}
h2 {
  margin: 0 0 8px;
  font-size: 1.25rem;
}
.sub-title {
  margin: 24px 0 12px;
  font-size: 1.05rem;
}
.tip {
  color: #888;
  font-size: 13px;
  margin: 0 0 16px;
  line-height: 1.5;
}
.search-bar {
  margin-bottom: 20px;
}
.period-toolbar {
  margin: 16px 0 12px;
  padding: 12px 14px;
  background: #f8f9fd;
  border-radius: 8px;
}
.ac-item {
  padding: 6px 0;
  line-height: 1.4;
}
.ac-title {
  margin-left: 8px;
  font-weight: 500;
}
.ac-sub {
  margin-top: 4px;
  margin-left: 52px;
  font-size: 12px;
  color: #888;
}
.summary-row {
  margin-bottom: 20px;
}
.sum-card {
  text-align: center;
}
.sum-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
}
.sum-value {
  font-size: 22px;
  font-weight: 600;
  color: #1a237e;
}
.toolbar {
  margin-bottom: 8px;
}
.chart {
  width: 100%;
  height: 440px;
}
</style>

<!-- 联想下拉 teleport 到 body，需单独提高层级，避免被图表/卡片遮挡 -->
<style>
.stats-search-suggest-popper {
  z-index: 5000 !important;
}
</style>
