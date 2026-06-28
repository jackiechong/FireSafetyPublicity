<template>
  <div class="dashboard">
    <section class="topbar">
      <div>
        <h1>培训数据总览</h1>
        <p>{{ scopeText }} · {{ periodLabel }}培训运行情况</p>
      </div>
      <div class="top-actions">
        <el-radio-group v-model="periodMode" @change="onPeriodModeChange">
          <el-radio-button label="year">年</el-radio-button>
          <el-radio-button label="month">月</el-radio-button>
        </el-radio-group>
        <el-date-picker
          v-model="periodValue"
          :type="periodMode"
          :format="periodMode === 'year' ? 'YYYY年' : 'YYYY年MM月'"
          :value-format="periodMode === 'year' ? 'YYYY' : 'YYYY-MM'"
          :clearable="false"
          style="width: 140px"
          @change="loadAll"
        />
        <el-button type="primary" @click="loadAll">刷新</el-button>
      </div>
    </section>

    <section class="metrics">
      <div class="metric-panel primary">
        <span>{{ periodMode === "year" ? "年度" : "月度" }}培训时长</span>
        <strong>{{ formatTrainingHours(totalMinutes) }}</strong>
        <small>{{ totalSessions }} 场培训</small>
      </div>
      <div class="metric-panel">
        <span>参训人次</span>
        <strong>{{ attendanceTotal }}</strong>
        <small>按培训签到累计</small>
      </div>
      <div class="metric-panel">
        <span>已登记人员</span>
        <strong>{{ personTotal }}</strong>
        <small>{{ orgTotal }} 个单位纳入管理</small>
      </div>
      <div class="metric-panel">
        <span>{{ periodMode === "year" ? "本月培训" : "本期培训" }}</span>
        <strong>{{ monthSessions }}</strong>
        <small>{{ formatTrainingHours(monthMinutes) }}</small>
      </div>
    </section>

    <section class="main-grid">
      <div class="panel span-2">
        <div class="panel-head">
          <h2>区县培训时长排行</h2>
          <span>按当前周期累计学时</span>
        </div>
        <div ref="districtChartRef" class="chart large" />
      </div>

      <div class="panel">
        <div class="panel-head">
          <h2>培训主题分布</h2>
          <span>人数占比</span>
        </div>
        <div ref="topicChartRef" class="chart" />
      </div>

      <div class="panel">
        <div class="panel-head">
          <h2>今日与本月</h2>
          <span>运行快照</span>
        </div>
        <div class="snapshot-list">
          <div>
            <b>{{ todaySessions }}</b>
            <span>今日培训场次</span>
          </div>
          <div>
            <b>{{ todayPeople }}</b>
            <span>今日参训人数</span>
          </div>
          <div>
            <b>{{ activeSessions }}</b>
            <span>当前活动场次</span>
          </div>
          <div>
            <b>{{ topicStats.length }}</b>
            <span>已使用主题</span>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <h2>人员类别</h2>
          <span>按参训人数</span>
        </div>
        <div class="rank-list">
          <div v-for="item in categoryRanks" :key="item.name" class="rank-row">
            <span>{{ item.name }}</span>
            <strong>{{ item.value }}人</strong>
          </div>
          <el-empty v-if="!categoryRanks.length" description="暂无类别数据" />
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <h2>单位覆盖</h2>
          <span>按参训人数</span>
        </div>
        <div class="rank-list">
          <div v-for="item in orgRanks" :key="item.organization_id" class="rank-row">
            <span>{{ item.organization_name }}</span>
            <strong>{{ item.person_count }}人</strong>
          </div>
          <el-empty v-if="!orgRanks.length" description="暂无单位数据" />
        </div>
      </div>

      <div class="panel span-2">
        <div class="panel-head">
          <h2>近期培训会议</h2>
          <span>最近 8 场</span>
        </div>
        <el-table :data="recentTrainings" size="small" border>
          <el-table-column prop="title" label="培训名称" min-width="180" />
          <el-table-column prop="topic_name" label="主题" min-width="120">
            <template #default="{ row }">{{ row.topic_name || "未分类" }}</template>
          </el-table-column>
          <el-table-column label="时间" width="150">
            <template #default="{ row }">{{ fmt(row.start_at) }}</template>
          </el-table-column>
          <el-table-column prop="brigade_name" label="主办单位" min-width="120" />
          <el-table-column prop="person_count" label="人数" width="80" />
        </el-table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import * as echarts from "echarts";
import http from "../api/http";
import { formatTrainingHours } from "../utils/duration";

const periodMode = ref("year");
const periodValue = ref(String(new Date().getFullYear()));
const currentAdmin = ref(null);
const districtStats = ref([]);
const topicStats = ref([]);
const trainings = ref([]);
const persons = ref([]);
const orgs = ref([]);
const categoryRanks = ref([]);
const orgRanks = ref([]);

const districtChartRef = ref(null);
const topicChartRef = ref(null);
let districtChart;
let topicChart;

const scopeText = computed(() => (currentAdmin.value?.role === "detachment" ? "葫芦岛支队" : "本大队"));
const periodLabel = computed(() => {
  const raw = String(periodValue.value || "");
  return periodMode.value === "year" ? `${raw} 年度` : `${raw.replace("-", " 年 ")} 月`;
});
const totalMinutes = computed(() => districtStats.value.reduce((s, x) => s + Number(x.total_minutes || 0), 0));
const totalSessions = computed(() => districtStats.value.reduce((s, x) => s + Number(x.session_count || 0), 0));
const personTotal = computed(() => persons.value.length);
const orgTotal = computed(() => orgs.value.length);
const attendanceTotal = computed(() => trainings.value.reduce((s, x) => s + Number(x.person_count || 0), 0));
const recentTrainings = computed(() => [...trainings.value].sort((a, b) => String(b.start_at).localeCompare(String(a.start_at))).slice(0, 8));
const activeSessions = computed(() => recentTrainings.value.filter((x) => x.is_active !== false).length);

const todayRange = computed(() => {
  const d = new Date();
  const start = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const end = new Date(start);
  end.setDate(start.getDate() + 1);
  return [start, end];
});

const monthRange = computed(() => {
  const d = normalizePeriodStart();
  const start = new Date(d.getFullYear(), d.getMonth(), 1);
  const end = new Date(start);
  end.setMonth(start.getMonth() + 1);
  return [start, end];
});

const todaySessions = computed(() => trainings.value.filter((x) => inRange(x.start_at, todayRange.value)).length);
const todayPeople = computed(() => trainings.value.filter((x) => inRange(x.start_at, todayRange.value)).reduce((s, x) => s + Number(x.person_count || 0), 0));
const monthSessions = computed(() => trainings.value.filter((x) => inRange(x.start_at, monthRange.value)).length);
const monthMinutes = computed(() => trainings.value.filter((x) => inRange(x.start_at, monthRange.value)).reduce((s, x) => s + Number(x.duration_minutes || 0) * Number(x.person_count || 0), 0));

function normalizePeriodStart() {
  const raw = String(periodValue.value || "");
  if (periodMode.value === "month") {
    const [y, m] = raw.split("-").map(Number);
    return new Date(y, (m || 1) - 1, 1);
  }
  return new Date(Number(raw), 0, 1);
}

function periodParams() {
  const startDate = normalizePeriodStart();
  const endDate = new Date(startDate);
  if (periodMode.value === "month") endDate.setMonth(startDate.getMonth() + 1);
  else endDate.setFullYear(startDate.getFullYear() + 1);
  const y = startDate.getFullYear();
  const m = String(startDate.getMonth() + 1).padStart(2, "0");
  const d = String(startDate.getDate()).padStart(2, "0");
  const ey = endDate.getFullYear();
  const em = String(endDate.getMonth() + 1).padStart(2, "0");
  const ed = String(endDate.getDate()).padStart(2, "0");
  return {
    start: `${y}-${m}-${d}T00:00:00`,
    end: `${ey}-${em}-${ed}T00:00:00`,
  };
}

async function onPeriodModeChange() {
  const now = new Date();
  periodValue.value = periodMode.value === "year"
    ? String(now.getFullYear())
    : `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  await loadAll();
}

function fmt(v) {
  return v ? String(v).replace("T", " ").slice(0, 16) : "";
}

function inRange(iso, range) {
  if (!iso) return false;
  const t = new Date(iso).getTime();
  return t >= range[0].getTime() && t < range[1].getTime();
}

async function loadAll() {
  const params = periodParams();
  const [me, districts, topics, summary, people, organizations, jobs] = await Promise.all([
    http.get("/api/admin/me"),
    http.get("/api/admin/stats/by-district", { params }),
    http.get("/api/admin/stats/by-topic", { params }),
    http.get("/api/admin/stats/training-summary", { params }),
    http.get("/api/admin/persons"),
    http.get("/api/admin/organizations"),
    http.get("/api/admin/job-titles"),
  ]);
  currentAdmin.value = me.data;
  districtStats.value = districts.data || [];
  topicStats.value = topics.data || [];
  trainings.value = summary.data || [];
  persons.value = people.data || [];
  orgs.value = organizations.data || [];
  await loadCategoryRanks(jobs.data || [], params);
  await loadOrgRanks();
  await renderCharts();
}

async function loadCategoryRanks(jobs, params) {
  const names = [...new Set([...(persons.value || []).map((p) => p.person_category || p.job_title).filter(Boolean), ...(jobs || []).map((j) => j.name)])].slice(0, 8);
  const rows = await Promise.all(
    names.map(async (name) => {
      try {
        const { data } = await http.get("/api/admin/stats/by-job-title", { params: { ...params, job_title: name } });
        return { name, value: data.total_person_count || 0 };
      } catch {
        return { name, value: 0 };
      }
    })
  );
  categoryRanks.value = rows.filter((x) => x.value > 0).sort((a, b) => b.value - a.value).slice(0, 6);
}

async function loadOrgRanks() {
  const districts = districtStats.value.map((d) => d.district_id).filter((id) => Number(id) > 0).slice(0, 10);
  const rows = [];
  for (const district_id of districts) {
    try {
      const { data } = await http.get("/api/admin/stats/orgs-by-district", { params: { ...periodParams(), district_id } });
      rows.push(...(data || []));
    } catch {
      /* ignore one district */
    }
  }
  orgRanks.value = rows.sort((a, b) => Number(b.person_count || 0) - Number(a.person_count || 0)).slice(0, 6);
}

async function renderCharts() {
  await nextTick();
  renderDistrictChart();
  renderTopicChart();
}

function renderDistrictChart() {
  if (!districtChartRef.value) return;
  if (!districtChart) districtChart = echarts.init(districtChartRef.value);
  const list = [...districtStats.value].sort((a, b) => Number(b.total_minutes || 0) - Number(a.total_minutes || 0));
  districtChart.setOption({
    grid: { left: 56, right: 24, top: 24, bottom: 54 },
    tooltip: { trigger: "axis", formatter: (items) => `${items[0].name}<br/>${formatTrainingHours(items[0].value)}` },
    xAxis: { type: "category", data: list.map((x) => x.district_name), axisLabel: { interval: 0, rotate: 25 } },
    yAxis: { type: "value", axisLabel: { formatter: (v) => (Number(v) / 60).toFixed(0) } },
    series: [{ type: "bar", data: list.map((x) => x.total_minutes), barMaxWidth: 34, itemStyle: { color: "#2563eb" } }],
  }, { notMerge: true });
}

function renderTopicChart() {
  if (!topicChartRef.value) return;
  if (!topicChart) topicChart = echarts.init(topicChartRef.value);
  const data = topicStats.value.map((x) => ({ name: x.topic_name, value: x.person_count }));
  topicChart.setOption({
    tooltip: { trigger: "item", formatter: "{b}<br/>{c}人 ({d}%)" },
    legend: { bottom: 0, type: "scroll" },
    series: [{ type: "pie", radius: ["46%", "68%"], center: ["50%", "44%"], data }],
  }, { notMerge: true });
}

onMounted(loadAll);
onUnmounted(() => {
  districtChart?.dispose();
  topicChart?.dispose();
});
</script>

<style scoped>
.dashboard {
  color: #172033;
}
.topbar {
  align-items: center;
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}
h1 {
  font-size: 24px;
  margin: 0 0 6px;
}
p {
  color: #667085;
  margin: 0;
}
.top-actions {
  align-items: center;
  display: flex;
  gap: 10px;
}
.metrics {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 14px;
}
.metric-panel,
.panel {
  background: #fff;
  border: 1px solid #e6eaf2;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(19, 31, 55, 0.05);
}
.metric-panel {
  display: flex;
  flex-direction: column;
  min-height: 96px;
  padding: 16px;
}
.metric-panel.primary {
  background: #102a43;
  color: #fff;
}
.metric-panel span,
.metric-panel small {
  color: #667085;
  font-size: 13px;
}
.metric-panel.primary span,
.metric-panel.primary small {
  color: #d6e4f0;
}
.metric-panel strong {
  font-size: 26px;
  line-height: 1.25;
  margin: 8px 0;
}
.main-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.panel {
  min-height: 260px;
  padding: 16px;
}
.span-2 {
  grid-column: span 2;
}
.panel-head {
  align-items: baseline;
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}
h2 {
  font-size: 16px;
  margin: 0;
}
.panel-head span {
  color: #7b8794;
  font-size: 12px;
}
.chart {
  height: 220px;
  width: 100%;
}
.chart.large {
  height: 280px;
}
.snapshot-list {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.snapshot-list div {
  background: #f6f8fb;
  border-radius: 8px;
  padding: 14px;
}
.snapshot-list b {
  color: #0f766e;
  display: block;
  font-size: 24px;
  margin-bottom: 6px;
}
.snapshot-list span {
  color: #667085;
  font-size: 13px;
}
.rank-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.rank-row {
  align-items: center;
  background: #f8fafc;
  border-radius: 8px;
  display: flex;
  gap: 12px;
  justify-content: space-between;
  min-height: 38px;
  padding: 0 12px;
}
.rank-row span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rank-row strong {
  color: #b45309;
  flex: 0 0 auto;
}
@media (max-width: 1180px) {
  .metrics,
  .main-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
