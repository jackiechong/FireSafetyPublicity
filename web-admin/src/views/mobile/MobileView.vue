<template>
  <div class="m-page">
    <header class="m-page__head">
      <div class="eyebrow">数据看板</div>
      <h1 class="m-page__title">培训运行总览</h1>
      <p class="m-page__desc">{{ periodLabel }} · {{ scopeLabel }} · 按区县汇总实名培训数据</p>
    </header>

    <section class="card m-panel">
      <div class="m-panel__head">
        <h2>统计周期</h2>
        <span class="sub">{{ periodLabel }}</span>
      </div>
      <div class="m-panel__body">
        <el-radio-group v-model="periodMode" class="m-seg" @change="onPeriodModeChange">
          <el-radio-button label="year">年</el-radio-button>
          <el-radio-button label="month">月</el-radio-button>
          <el-radio-button label="date">日</el-radio-button>
        </el-radio-group>
        <el-date-picker
          v-model="periodValue"
          :type="periodMode"
          :clearable="false"
          :format="periodFormat"
          :value-format="periodValueFormat"
          class="m-date"
          @change="onPeriodChange"
        />
      </div>
    </section>

    <div class="mkpi-grid">
      <article class="mkpi">
        <div class="mkpi__label"><AppIcon name="clock" :size="13" />培训总时长</div>
        <div class="mkpi__value num">{{ hoursValue }}<small>小时</small></div>
        <div class="mkpi__foot">{{ hasDistrict ? "本区县合计" : "全市合计" }}</div>
      </article>
      <article class="mkpi">
        <div class="mkpi__label"><AppIcon name="calendar" :size="13" />培训场次</div>
        <div class="mkpi__value num">{{ sessionsValue }}<small>场</small></div>
        <div class="mkpi__foot">含进行中与已结束</div>
      </article>
      <article class="mkpi">
        <div class="mkpi__label"><AppIcon name="users" :size="13" />场均时长</div>
        <div class="mkpi__value num">{{ avgMinutesLabel }}</div>
        <div class="mkpi__foot">按当前统计周期</div>
      </article>
      <article class="mkpi">
        <div class="mkpi__label"><AppIcon name="layers" :size="13" />覆盖区县</div>
        <div class="mkpi__value num">{{ districtStats.length }}<small>个</small></div>
        <div class="mkpi__foot">最长 {{ topDistrictName }} {{ topHours }} 小时</div>
      </article>
    </div>

    <section class="card m-panel">
      <div class="m-panel__head">
        <h2>区县培训时长</h2>
        <span class="sub">按小时</span>
      </div>
      <div class="m-panel__body m-panel__body--chart">
        <div ref="chartRef" class="m-chart" />
      </div>
    </section>

    <section class="card m-panel">
      <div class="m-panel__head">
        <h2>筛选</h2>
        <span class="sub">选择区县看类型占比</span>
      </div>
      <div class="m-panel__body">
        <div class="m-field">
          <span class="m-field__label">区县</span>
          <el-select
            v-model="districtId"
            clearable
            placeholder="全部区县"
            class="m-w-full"
            @change="onDistrictChange"
          >
            <el-option v-for="d in districts" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </div>
        <div v-if="false" class="m-field">
          <span class="m-field__label">单位</span>
          <el-select
            v-model="orgId"
            clearable
            filterable
            placeholder="选择单位查看培训人员"
            class="m-w-full"
            @change="onOrgChange"
          >
            <el-option
              v-for="o in orgs"
              :key="o.organization_id"
              :label="`${o.organization_name} · ${formatTrainingHours(o.total_minutes)}`"
              :value="o.organization_id"
            />
          </el-select>
        </div>
      </div>
    </section>

    <section v-if="districtId" class="card m-panel">
      <div class="m-panel__head">
        <h2>类型时长占比</h2>
        <span class="sub">{{ districtName }}</span>
      </div>
      <div class="m-panel__body m-panel__body--chart">
        <div ref="pieRef" class="m-chart m-chart--sm" />
      </div>
    </section>

    <section v-if="orgId && persons.length" class="card m-panel">
      <div class="m-panel__head">
        <h2>参训人员</h2>
        <span class="sub">{{ persons.length }} 人</span>
      </div>
      <div class="m-panel__body">
        <div class="m-list">
          <div v-for="p in persons" :key="p.person_id" class="m-listrow">
            <div class="m-listrow__main">
              <span class="m-listrow__title">{{ p.name || "—" }}</span>
              <span class="m-listrow__meta num">{{ p.phone }}</span>
            </div>
            <div class="m-listrow__foot">
              <span>{{ p.session_count }} 次</span>
              <span class="m-dot">·</span>
              <span>{{ formatTrainingHours(p.total_minutes) }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section v-if="orgId && !personLoading && persons.length === 0" class="card m-panel">
      <div class="empty">
        <div class="empty__art"><AppIcon name="users" :size="26" /></div>
        <h4>该单位暂无参训记录</h4>
        <p>换个统计周期，或先在管理端登记培训后再看。</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import * as echarts from "echarts";
import http from "../../api/http";
import AppIcon from "../../components/AppIcon.vue";
import { formatMinutesAxisHours, formatTrainingHours, formatTrainingMinutes } from "../../utils/duration";

const districts = ref([]);
const districtStats = ref([]);
const districtId = ref();
const orgs = ref([]);
const typeStats = ref([]);
const orgId = ref();
const persons = ref([]);
const personLoading = ref(false);
const periodMode = ref("year");
const periodValue = ref(String(new Date().getFullYear()));
const appliedPeriodMode = ref("year");
const appliedPeriodValue = ref(new Date());

const chartRef = ref(null);
const pieRef = ref(null);
let barChart;
let pieChart;

const totalMinutes = computed(() => {
  if (districtId.value) {
    return typeStats.value.reduce((s, o) => s + o.total_minutes, 0);
  }
  return districtStats.value.reduce((s, d) => s + d.total_minutes, 0);
});

const totalMinutesLabel = computed(() => formatTrainingHours(totalMinutes.value));

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

function normalizePeriodValue(mode, value) {
  if (value instanceof Date && !Number.isNaN(value.getTime())) return value;
  const raw = String(value || "");
  if (!raw) return null;
  if (mode === "year") {
    const y = Number(raw);
    if (!Number.isFinite(y)) return null;
    return new Date(y, 0, 1);
  }
  if (mode === "month") {
    const [y, m] = raw.split("-").map(Number);
    if (!Number.isFinite(y) || !Number.isFinite(m)) return null;
    return new Date(y, (m || 1) - 1, 1);
  }
  const [y, m, d] = raw.split("-").map(Number);
  if (!Number.isFinite(y) || !Number.isFinite(m) || !Number.isFinite(d)) return null;
  return new Date(y, (m || 1) - 1, d || 1);
}

function apiDate(dt) {
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, "0");
  const d = String(dt.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}T00:00:00`;
}

function statsParams(extra = {}) {
  const start = normalizePeriodValue(appliedPeriodMode.value, appliedPeriodValue.value) || new Date();
  const end = new Date(start);
  if (appliedPeriodMode.value === "year") end.setFullYear(start.getFullYear() + 1);
  else if (appliedPeriodMode.value === "month") end.setMonth(start.getMonth() + 1);
  else end.setDate(start.getDate() + 1);
  return { ...extra, start: apiDate(start), end: apiDate(end) };
}

const sessionCount = computed(() => {
  if (districtId.value != null && districtId.value !== "") {
    const did = Number(districtId.value);
    const d = districtStats.value.find((x) => Number(x.district_id) === did);
    return d ? d.session_count : "—";
  }
  return districtStats.value.reduce((s, d) => s + d.session_count, 0);
});

/* ---------- 以下为纯展示派生值，不改动取数逻辑 ---------- */
const hasDistrict = computed(() => districtId.value != null && districtId.value !== "");

const districtName = computed(() => {
  const did = Number(districtId.value);
  return districts.value.find((d) => Number(d.id) === did)?.name || "本区县";
});

const scopeLabel = computed(() => (hasDistrict.value ? districtName.value : "全市"));

const periodLabel = computed(() => {
  const dt = normalizePeriodValue(appliedPeriodMode.value, appliedPeriodValue.value);
  if (!dt) return "全部周期";
  const y = dt.getFullYear();
  if (appliedPeriodMode.value === "year") return `${y} 年`;
  if (appliedPeriodMode.value === "month") return `${y} 年 ${dt.getMonth() + 1} 月`;
  return `${y} 年 ${dt.getMonth() + 1} 月 ${dt.getDate()} 日`;
});

const hoursValue = computed(() => (Number(totalMinutes.value || 0) / 60).toFixed(1));

const sessionsValue = computed(() => {
  const n = Number(sessionCount.value);
  return Number.isFinite(n) ? n : 0;
});

const avgMinutesLabel = computed(() => {
  if (!sessionsValue.value) return "—";
  return formatTrainingMinutes(Math.round(Number(totalMinutes.value || 0) / sessionsValue.value));
});

const topDistrict = computed(() => {
  const list = [...(districtStats.value || [])];
  if (!list.length) return null;
  return list.reduce((a, b) => (Number(b.total_minutes) > Number(a.total_minutes) ? b : a));
});

const topHours = computed(() => (Number(topDistrict.value?.total_minutes || 0) / 60).toFixed(1));

const topDistrictName = computed(() => topDistrict.value?.district_name || "暂无数据");

/* ---------- 图表主题：统一取设计令牌 ---------- */
function cssVar(name, fallback) {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function chartColors() {
  return {
    brand: cssVar("--brand-500", "#1b6da3"),
    ink: cssVar("--ink-500", "#5a6e82"),
    inkStrong: cssVar("--ink-800", "#17334f"),
    line: cssVar("--line", "#dde4eb"),
    lineSoft: cssVar("--line-soft", "#eaeff4"),
    surface: cssVar("--surface", "#ffffff"),
  };
}

function chartPalette() {
  return [
    cssVar("--brand-500", "#1b6da3"),
    cssVar("--fire-500", "#d0342c"),
    cssVar("--ok-500", "#16794c"),
    cssVar("--warn-500", "#9a6207"),
    cssVar("--info-500", "#1f6fa8"),
    cssVar("--brand-700", "#114368"),
    cssVar("--ink-400", "#7d8fa1"),
    cssVar("--fire-600", "#b8261e"),
    cssVar("--ok-600", "#12673f"),
  ];
}

async function loadMeta() {
  const [dRes, sRes] = await Promise.all([
    http.get("/api/admin/districts"),
    http.get("/api/admin/stats/by-district", { params: statsParams() }),
  ]);
  districts.value = dRes.data;
  districtStats.value = sRes.data;
}

function renderBar() {
  if (!chartRef.value) return;
  if (!barChart) barChart = echarts.init(chartRef.value);
  const c = chartColors();
  const list = districtStats.value.length ? districtStats.value : [];
  const vals = list.map((d) => d.total_minutes);
  barChart.setOption(
    {
      tooltip: {
        trigger: "axis",
        backgroundColor: c.surface,
        borderColor: c.line,
        textStyle: { color: c.inkStrong, fontSize: 12 },
        formatter: (items) => {
          const p = items[0];
          return `${p.name}<br/>${formatTrainingHours(p.value)}`;
        },
      },
      grid: { left: 6, right: 10, top: 26, bottom: 4, containLabel: true },
      xAxis: {
        type: "category",
        data: list.map((d) => d.district_name),
        axisTick: { show: false },
        axisLine: { lineStyle: { color: c.line } },
        axisLabel: { color: c.ink, fontSize: 10, rotate: 40, margin: 8 },
      },
      yAxis: {
        type: "value",
        splitLine: { lineStyle: { color: c.lineSoft, type: "dashed" } },
        axisLabel: {
          color: c.ink,
          fontSize: 10,
          formatter: (v) => formatMinutesAxisHours(v),
        },
      },
      series: [
        {
          type: "bar",
          data: vals,
          itemStyle: { color: c.brand, borderRadius: [3, 3, 0, 0] },
          barMaxWidth: 26,
          label: {
            show: true,
            position: "top",
            distance: 4,
            fontSize: 10,
            color: c.ink,
            formatter: (p) => formatMinutesAxisHours(p.value),
          },
        },
      ],
    },
    true
  );
}

function renderPie() {
  if (!pieRef.value) return;
  const c = chartColors();
  const palette = chartPalette();
  const list = typeStats.value.filter((o) => o.total_minutes > 0);
  if (!pieChart) pieChart = echarts.init(pieRef.value);
  if (!list.length) {
    pieChart.setOption(
      {
        color: palette,
        series: [{ type: "pie", radius: ["38%", "62%"], data: [] }],
        title: {
          text: "暂无时长数据",
          left: "center",
          top: "middle",
          textStyle: { fontSize: 13, color: c.ink, fontWeight: 400 },
        },
      },
      true
    );
    return;
  }
  pieChart.setOption(
    {
      color: palette,
      tooltip: {
        trigger: "item",
        backgroundColor: c.surface,
        borderColor: c.line,
        textStyle: { color: c.inkStrong, fontSize: 12 },
        formatter: (p) => `${p.name}<br/>${formatTrainingHours(p.value)} (${p.percent}%)`,
      },
      series: [
        {
          type: "pie",
          radius: ["42%", "66%"],
          center: ["50%", "52%"],
          avoidLabelOverlap: true,
          itemStyle: { borderColor: c.surface, borderWidth: 2 },
          label: { show: false },
          labelLine: { show: false },
          emphasis: {
            label: { show: true, fontSize: 12, fontWeight: 600, color: c.inkStrong, formatter: "{b}\n{d}%" },
          },
          data: list.map((o) => ({ name: o.org_type_name, value: o.total_minutes })),
        },
      ],
    },
    true
  );
}

async function onDistrictChange() {
  orgId.value = undefined;
  persons.value = [];
  orgs.value = [];
  typeStats.value = [];
  await nextTick();
  pieChart?.dispose();
  pieChart = null;
  if (districtId.value == null || districtId.value === "") {
    await loadMeta();
    renderBar();
    return;
  }
  const did = Number(districtId.value);
  try {
    const { data: orgList } = await http.get("/api/admin/organizations", {
      params: { district_id: did },
    });
    const { data: statsList } = await http.get("/api/admin/stats/orgs-by-district", {
      params: statsParams({ district_id: did }),
    });
    const statsMap = new Map((statsList || []).map((x) => [x.organization_id, x]));
    orgs.value = (orgList || []).map((o) => {
      const s = statsMap.get(o.id);
      return {
        organization_id: o.id,
        organization_name: o.name,
        total_minutes: s?.total_minutes ?? 0,
        person_count: s?.person_count ?? 0,
      };
    });
    const { data: types } = await http.get("/api/admin/stats/types-by-district", {
      params: statsParams({ district_id: did }),
    });
    typeStats.value = types || [];
  } catch (e) {
    console.error(e);
    orgs.value = [];
    typeStats.value = [];
  }
  await nextTick();
  renderPie();
}

async function onOrgChange() {
  persons.value = [];
  if (!orgId.value) return;
  personLoading.value = true;
  try {
    const { data } = await http.get("/api/admin/stats/persons-by-organization", {
      params: statsParams({ organization_id: Number(orgId.value) }),
    });
    persons.value = data;
  } finally {
    personLoading.value = false;
  }
}

async function onPeriodChange() {
  const picked = normalizePeriodValue(periodMode.value, periodValue.value);
  if (!picked) return;
  appliedPeriodMode.value = periodMode.value;
  appliedPeriodValue.value = periodValue.value;
  persons.value = [];
  await loadMeta();
  if (districtId.value) await onDistrictChange();
  else renderBar();
}

function onPeriodModeChange() {
  periodValue.value = null;
}

watch(
  () => districtStats.value,
  () => nextTick().then(renderBar)
);

onMounted(async () => {
  await loadMeta();
  await nextTick();
  renderBar();
  window.addEventListener("resize", () => {
    barChart?.resize();
    pieChart?.resize();
  });
});

onUnmounted(() => {
  barChart?.dispose();
  pieChart?.dispose();
  barChart = null;
  pieChart = null;
});
</script>

<style scoped>
.m-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

/* ---------- 页头 ---------- */
.m-page__head {
  padding: 2px 2px 0;
  min-width: 0;
}
.m-page__title {
  margin-top: 3px;
  font-size: var(--fs-20);
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--ink-900);
}
.m-page__desc {
  margin-top: 3px;
  font-size: var(--fs-12);
  line-height: 1.5;
  color: var(--ink-500);
}

/* ---------- 卡片面板 ---------- */
.m-panel {
  overflow: hidden;
  min-width: 0;
}
.m-panel__head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--line-soft);
}
.m-panel__head h2 {
  font-size: var(--fs-14);
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--ink-900);
}
.m-panel__head .sub {
  margin-left: auto;
  min-width: 0;
  font-size: var(--fs-11);
  color: var(--ink-500);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.m-panel__body {
  padding: 12px 14px 14px;
  min-width: 0;
}
.m-panel__body--chart {
  padding: 8px 8px 10px;
}

/* ---------- KPI（两列小卡） ---------- */
.mkpi-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  min-width: 0;
}
.mkpi {
  min-width: 0;
  padding: 12px 12px 10px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
}
.mkpi__label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: var(--fs-11);
  letter-spacing: 0.02em;
  color: var(--ink-500);
}
.mkpi__label svg {
  width: 13px;
  height: 13px;
  flex: none;
  color: var(--ink-400);
}
.mkpi__value {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-top: 6px;
  font-family: var(--font-num);
  font-variant-numeric: tabular-nums;
  font-size: var(--fs-26);
  font-weight: 600;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: var(--ink-900);
}
.mkpi__value small {
  font-family: var(--font);
  font-size: var(--fs-12);
  font-weight: 500;
  color: var(--ink-500);
}
.mkpi__foot {
  margin-top: 5px;
  font-size: var(--fs-11);
  color: var(--ink-500);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---------- 周期 segmented ---------- */
.m-seg {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2px;
  width: 100%;
  padding: 3px;
  background: var(--surface-3);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
}
.m-seg :deep(.el-radio-button) {
  display: block;
  min-width: 0;
}
.m-seg :deep(.el-radio-button__inner) {
  width: 100%;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
  border: 0;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--ink-600);
  font-size: var(--fs-13);
  box-shadow: none;
}
.m-seg :deep(.el-radio-button__inner:hover) {
  color: var(--ink-900);
}
.m-seg :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: var(--surface);
  color: var(--ink-900);
  font-weight: 600;
  box-shadow: inset 0 -3px 0 var(--fire-500), 0 1px 2px rgba(11, 27, 43, 0.1);
}
.m-date {
  width: 100%;
  margin-top: 10px;
}
.m-date :deep(.el-input__wrapper) {
  min-height: 44px;
}

/* ---------- 表单 ---------- */
.m-field {
  min-width: 0;
}
.m-field + .m-field {
  margin-top: 12px;
}
.m-field__label {
  display: block;
  margin-bottom: 6px;
  font-size: var(--fs-12);
  font-weight: 500;
  color: var(--ink-600);
}
.m-field :deep(.el-select__wrapper),
.m-field :deep(.el-input__wrapper) {
  min-height: 44px;
}
.m-w-full {
  width: 100%;
}

/* ---------- 图表 ---------- */
.m-chart {
  width: 100%;
  height: 240px;
  min-width: 0;
}
.m-chart--sm {
  height: 220px;
}

/* ---------- 人员列表 ---------- */
.m-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.m-listrow {
  min-width: 0;
  padding: 10px 12px;
  background: var(--surface-2);
  border: 1px solid var(--line-soft);
  border-radius: var(--r-md);
}
.m-listrow__main {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}
.m-listrow__title {
  min-width: 0;
  font-size: var(--fs-14);
  font-weight: 500;
  color: var(--ink-900);
  overflow-wrap: anywhere;
}
.m-listrow__meta {
  flex: none;
  font-size: var(--fs-12);
  color: var(--ink-500);
}
.m-listrow__foot {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  font-size: var(--fs-12);
  color: var(--ink-500);
}
.m-dot {
  color: var(--ink-300);
}
</style>
