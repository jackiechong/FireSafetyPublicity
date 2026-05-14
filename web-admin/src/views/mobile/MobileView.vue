<template>
  <div class="m-page">
    <h1 class="m-title">数据概览</h1>
    <p class="m-desc">触摸优化，便于外出时查看培训统计与参训人员。</p>

    <div class="m-cards">
      <div class="m-card">
        <div class="m-card-label">{{ districtId ? "本区县时长" : "全市培训总时长" }}</div>
        <div class="m-card-val">{{ totalMinutesLabel }}</div>
      </div>
      <div class="m-card">
        <div class="m-card-label">{{ districtId ? "本区县场次" : "全市培训总场次" }}</div>
        <div class="m-card-val">{{ sessionCount }}</div>
      </div>
    </div>

    <section class="m-block">
      <div class="m-block-title">区县培训时长</div>
      <div ref="chartRef" class="m-chart" />
    </section>

    <section class="m-block">
      <div class="m-block-title">筛选</div>
      <el-select
        v-model="districtId"
        clearable
        placeholder="选择区县看区内单位"
        class="m-select"
        @change="onDistrictChange"
      >
        <el-option v-for="d in districts" :key="d.id" :label="d.name" :value="d.id" />
      </el-select>
      <el-select
        v-if="districtId"
        v-model="orgId"
        clearable
        filterable
        placeholder="选择单位查看培训人员"
        class="m-select"
        style="margin-top: 10px"
        @change="onOrgChange"
      >
        <el-option
          v-for="o in orgs"
          :key="o.organization_id"
          :label="`${o.organization_name} · ${formatTrainingMinutes(o.total_minutes)}`"
          :value="o.organization_id"
        />
      </el-select>
    </section>

    <section v-if="districtId" class="m-block">
      <div class="m-block-title">县区内单位时长占比</div>
      <div ref="pieRef" class="m-chart m-chart-sm" />
    </section>

    <section v-if="orgId && persons.length" class="m-block">
      <div class="m-block-title">参训人员（{{ persons.length }} 人）</div>
      <div class="m-list">
        <div v-for="(p, i) in persons" :key="p.person_id" class="m-row">
          <div class="m-row-main">
            <span class="m-name">{{ p.name || "—" }}</span>
            <span class="m-phone">{{ p.phone }}</span>
          </div>
          <div class="m-row-meta">
            <span>{{ p.session_count }} 次</span>
            <span class="dot">·</span>
            <span>{{ formatTrainingMinutes(p.total_minutes) }}</span>
          </div>
        </div>
      </div>
    </section>

    <el-empty v-if="orgId && !personLoading && persons.length === 0" description="该单位暂无参训记录" />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import * as echarts from "echarts";
import http from "../../api/http";
import { formatMinutesAxisDays, formatTrainingMinutes } from "../../utils/duration";

const districts = ref([]);
const districtStats = ref([]);
const districtId = ref();
const orgs = ref([]);
const orgId = ref();
const persons = ref([]);
const personLoading = ref(false);

const chartRef = ref(null);
const pieRef = ref(null);
let barChart;
let pieChart;

const totalMinutes = computed(() => {
  if (districtId.value) {
    return orgs.value.reduce((s, o) => s + o.total_minutes, 0);
  }
  return districtStats.value.reduce((s, d) => s + d.total_minutes, 0);
});

const totalMinutesLabel = computed(() => formatTrainingMinutes(totalMinutes.value));

const sessionCount = computed(() => {
  if (districtId.value != null && districtId.value !== "") {
    const did = Number(districtId.value);
    const d = districtStats.value.find((x) => Number(x.district_id) === did);
    return d ? d.session_count : "—";
  }
  return districtStats.value.reduce((s, d) => s + d.session_count, 0);
});

async function loadMeta() {
  const [dRes, sRes] = await Promise.all([
    http.get("/api/admin/districts"),
    http.get("/api/admin/stats/by-district"),
  ]);
  districts.value = dRes.data;
  districtStats.value = sRes.data;
}

function renderBar() {
  if (!chartRef.value) return;
  if (!barChart) barChart = echarts.init(chartRef.value);
  const list = districtStats.value.length ? districtStats.value : [];
  const vals = list.map((d) => d.total_minutes);
  barChart.setOption({
    tooltip: {
      trigger: "axis",
      formatter: (items) => {
        const p = items[0];
        return `${p.name}<br/>${formatTrainingMinutes(p.value)}`;
      },
    },
    grid: { left: 44, right: 12, bottom: 56, top: 28 },
    xAxis: { type: "category", data: list.map((d) => d.district_name), axisLabel: { rotate: 35, fontSize: 11 } },
    yAxis: {
      type: "value",
      name: "",
      nameTextStyle: { fontSize: 10 },
      splitLine: { lineStyle: { type: "dashed" } },
      axisLabel: {
        fontSize: 10,
        formatter: (v) => formatMinutesAxisDays(v),
      },
    },
    series: [
      {
        type: "bar",
        data: vals,
        itemStyle: { color: "#3949ab" },
        barMaxWidth: 36,
        label: {
          show: true,
          position: "top",
          fontSize: 10,
          formatter: (p) => formatTrainingMinutes(p.value),
        },
      },
    ],
  });
}

function renderPie() {
  if (!pieRef.value) return;
  const list = orgs.value.filter((o) => o.total_minutes > 0);
  if (!pieChart) pieChart = echarts.init(pieRef.value);
  if (!list.length) {
    pieChart.setOption({ series: [{ type: "pie", radius: ["40%", "68%"], data: [] }], title: { text: "暂无时长数据", left: "center", top: "middle", textStyle: { fontSize: 14, color: "#999" } } });
    return;
  }
  const did = districtId.value != null ? Number(districtId.value) : NaN;
  const distName = districts.value.find((d) => Number(d.id) === did)?.name || "";
  pieChart.setOption({
    title: { text: `${distName} 单位占比`, left: "center", top: 0, textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: "item",
      formatter: (p) => `${p.name}<br/>${formatTrainingMinutes(p.value)} (${p.percent}%)`,
    },
    series: [
      {
        type: "pie",
        radius: ["38%", "62%"],
        center: ["50%", "55%"],
        data: list.map((o) => ({ name: o.organization_name, value: o.total_minutes })),
      },
    ],
  });
}

async function onDistrictChange() {
  orgId.value = undefined;
  persons.value = [];
  orgs.value = [];
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
    let statsMap = new Map();
    try {
      const { data: statsList } = await http.get("/api/admin/stats/orgs-by-district", {
        params: { district_id: did },
      });
      statsMap = new Map((statsList || []).map((x) => [x.organization_id, x]));
    } catch (statsErr) {
      console.warn("orgs-by-district stats failed, showing orgs with zero stats", statsErr);
    }
    orgs.value = (orgList || []).map((o) => {
      const s = statsMap.get(o.id);
      return {
        organization_id: o.id,
        organization_name: o.name,
        total_minutes: s?.total_minutes ?? 0,
        person_count: s?.person_count ?? 0,
      };
    });
  } catch (e) {
    console.error(e);
    orgs.value = [];
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
      params: { organization_id: Number(orgId.value) },
    });
    persons.value = data;
  } finally {
    personLoading.value = false;
  }
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
  padding-bottom: 24px;
}
.m-title {
  margin: 0 0 8px;
  font-size: 1.35rem;
  color: #1a237e;
}
.m-desc {
  margin: 0 0 16px;
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}
.m-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 16px;
}
.m-card {
  background: #fff;
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 2px 8px rgba(26, 35, 126, 0.08);
}
.m-card-label {
  font-size: 12px;
  color: #888;
}
.m-card-val {
  margin-top: 6px;
  font-size: 1.5rem;
  font-weight: 700;
  color: #3949ab;
}
.m-block {
  background: #fff;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.m-block-title {
  font-weight: 600;
  margin-bottom: 10px;
  color: #333;
  font-size: 15px;
}
.m-chart {
  width: 100%;
  height: 260px;
}
.m-chart-sm {
  height: 240px;
}
.m-select {
  width: 100%;
}
.m-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.m-row {
  border: 1px solid #eee;
  border-radius: 10px;
  padding: 12px;
  background: #fafafa;
}
.m-row-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.m-name {
  font-weight: 600;
  color: #222;
}
.m-phone {
  font-size: 13px;
  color: #666;
}
.m-row-meta {
  margin-top: 6px;
  font-size: 13px;
  color: #888;
}
.dot {
  margin: 0 4px;
}
</style>
