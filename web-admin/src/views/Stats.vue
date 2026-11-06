<template>
  <div>
    <div class="page-head">
      <div class="page-head__main">
        <div class="eyebrow">统计分析</div>
        <h1 class="page-title">培训统计分析</h1>
        <p class="page-desc">{{ periodLabelText }} · {{ brigadeSelectedName }} · 场次、人数与时长随统计口径同步更新</p>
      </div>
      <div class="page-actions">
        <span class="badge badge--done">口径：{{ rankMetricLabel() }}</span>
      </div>
    </div>

    <div class="filterbar">
      <div class="field">
        <label>统计周期</label>
        <div class="seg">
          <button type="button" :class="{ 'is-on': periodMode === 'year' }" @click="setPeriodMode('year')">年</button>
          <button type="button" :class="{ 'is-on': periodMode === 'month' }" @click="setPeriodMode('month')">月</button>
          <button type="button" :class="{ 'is-on': periodMode === 'date' }" @click="setPeriodMode('date')">日</button>
        </div>
      </div>

      <div class="field">
        <label for="f-period">时间范围</label>
        <el-date-picker
          id="f-period"
          v-model="periodValue"
          :type="periodMode"
          :clearable="false"
          :format="periodFormat"
          :value-format="periodValueFormat"
          placeholder="选择时间"
          style="width: 170px"
          @change="onPeriodChange"
        />
      </div>

      <div class="field">
        <label for="f-brigade">培训主办单位</label>
        <el-select
          id="f-brigade"
          v-model="brigadeFilter"
          clearable
          placeholder="不选：全市对比"
          style="width: 200px"
          @change="onBrigadeChange"
        >
          <el-option v-for="b in brigadeOptions" :key="b.id" :label="b.name" :value="b.id" />
        </el-select>
      </div>

      <div class="field">
        <label>排行依据</label>
        <div class="seg">
          <button type="button" :class="{ 'is-on': rankMetric === 'duration' }" @click="setRankMetric('duration')">时长</button>
          <button type="button" :class="{ 'is-on': rankMetric === 'person' }" @click="setRankMetric('person')">人次</button>
        </div>
      </div>

      <div class="field" style="flex: 1; min-width: 240px">
        <label for="f-q">单位 / 人员</label>
        <el-autocomplete
          id="f-q"
          v-model="searchQ"
          :fetch-suggestions="querySearch"
          clearable
          highlight-first-item
          :debounce="250"
          popper-class="stats-search-suggest-popper"
          placeholder="搜索单位名称，或人员姓名 / 手机号"
          style="width: 100%"
          value-key="value"
          fit-input-width
          @select="handleSearchSelect"
        >
          <template #default="{ item }">
            <div class="ac-item">
              <span class="badge" :class="item.kind === 'organization' ? 'badge--live' : 'badge--ok'">
                {{ item.kind === "organization" ? "单位" : "人员" }}
              </span>
              <span class="ac-title">{{ item.title }}</span>
              <div class="ac-sub">{{ item.subtitle }}</div>
            </div>
          </template>
        </el-autocomplete>
      </div>

      <div style="display: flex; gap: 8px; margin-left: auto">
        <button class="btn btn--primary" @click="onPeriodChange">查询</button>
        <button class="btn btn--ghost" @click="resetFilters">重置</button>
      </div>
    </div>

    <div v-if="brigadeFilter" class="chips">
      <span class="chip">
        <b>主办单位</b>{{ brigadeSelectedName }}
        <button type="button" aria-label="移除主办单位条件" @click="clearBrigade">
          <AppIcon name="x" :size="11" />
        </button>
      </span>
      <span class="chip"><b>周期</b>{{ periodLabelText }}</span>
      <button class="chips__reset" type="button" @click="resetFilters">清除全部</button>
    </div>

    <div class="grid grid--kpi" style="margin-bottom: 20px">
      <article class="kpi kpi--accent">
        <div class="kpi__label">
          <AppIcon name="clock" :size="13" />{{ brigadeFilter ? "本单位培训时长" : "全市培训总时长" }}
        </div>
        <div class="kpi__value num">{{ (displayTotalMinutes / 60).toFixed(1) }}<small>小时</small></div>
        <div class="kpi__foot"><span>{{ periodLabelText }}累计</span></div>
      </article>

      <article
        class="kpi"
        :class="{ 'kpi--click': brigadeFilter }"
        :role="brigadeFilter ? 'button' : undefined"
        :tabindex="brigadeFilter ? 0 : undefined"
        @click="brigadeFilter && openBrigadeTrainings()"
        @keydown.enter="brigadeFilter && openBrigadeTrainings()"
      >
        <div class="kpi__label"><AppIcon name="calendar" :size="13" />培训场次</div>
        <div class="kpi__value num">{{ displaySessionCount }}<small>场</small></div>
        <div class="kpi__foot">
          <span>{{ brigadeFilter ? "点击查看场次明细" : `有记录单位 ${displayActiveBrigadeCount} 个` }}</span>
        </div>
      </article>

      <article class="kpi">
        <div class="kpi__label"><AppIcon name="users" :size="13" />培训人数</div>
        <div class="kpi__value num">{{ nf(displayPersonCount) }}<small>人</small></div>
        <div class="kpi__foot"><span>按参训签到记录累计</span></div>
      </article>

      <article class="kpi">
        <div class="kpi__label"><AppIcon name="building" :size="13" />全市有记录主办单位</div>
        <div class="kpi__value num">{{ displayActiveBrigadeCount }}<small>个</small></div>
        <div class="kpi__foot"><span>共 {{ brigadeOptions.length }} 个主办单位</span></div>
      </article>
    </div>

    <section class="card" style="margin-bottom: 20px">
      <div class="card__head">
        <h3>主办单位{{ rankMetric === "person" ? "人次" : "时长" }}排行</h3>
        <span class="sub">{{ periodLabelText }}</span>
        <div class="grow"></div>
        <span v-if="brigadeFilter" class="badge badge--live">{{ brigadeSelectedName }}</span>
        <span v-else class="badge badge--done">全市对比</span>
      </div>
      <div class="card__body" style="padding: 12px 16px 8px">
        <div ref="chartRef" class="chart" />
      </div>
    </section>

    <section v-if="brigadeFilter" class="card">
      <div class="card__head">
        <h3>当前主办单位培训场次</h3>
        <span class="sub">共 {{ displaySessionCount }} 场 · {{ nf(displayPersonCount) }} 人</span>
        <div class="grow"></div>
        <span class="badge badge--live">{{ brigadeSelectedName }}</span>
      </div>

      <div v-loading="brigadeTrainingLoading" class="tablewrap">
        <table class="tb">
          <thead>
            <tr>
              <th style="width: 56px">#</th>
              <th>会议名称</th>
              <th style="width: 150px">开展时间</th>
              <th class="num" style="width: 96px">培训人数</th>
              <th style="width: 140px">主题</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in brigadeTrainingRows" :key="`${row.title}-${i}`">
              <td class="num" style="color: var(--ink-400)">{{ i + 1 }}</td>
              <td class="cell-main">{{ row.title }}</td>
              <td class="num">{{ formatTime(row.start_at) }}</td>
              <td class="num">{{ row.person_count }}</td>
              <td>{{ row.topic_name || "未分类" }}</td>
            </tr>
            <tr v-if="!brigadeTrainingRows.length && !brigadeTrainingLoading">
              <td colspan="5">
                <div class="empty">
                  <div class="empty__art"><AppIcon name="calendar" :size="26" /></div>
                  <h4>本期没有培训场次</h4>
                  <p>切换统计周期或更换主办单位后重新查询。</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

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
        <button class="btn btn--ghost" @click="personRebindVisible = false">取消</button>
        <button class="btn btn--primary" :disabled="personRebindSaving" @click="submitPersonRebind">
          {{ personRebindSaving ? "保存中…" : "保存" }}
        </button>
      </template>
    </el-dialog>

    <el-dialog v-model="brigadeTrainingVisible" title="当前主办单位培训场次" width="760px" destroy-on-close>
      <div v-loading="brigadeTrainingLoading">
        <table class="tb">
          <thead>
            <tr>
              <th>会议名称</th>
              <th style="width: 150px">开展时间</th>
              <th class="num" style="width: 88px">人数</th>
              <th style="width: 130px">主题</th>
              <th style="width: 130px">主办单位</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in brigadeTrainingRows" :key="`dlg-${row.title}-${i}`">
              <td class="cell-main">{{ row.title }}</td>
              <td class="num">{{ formatTime(row.start_at) }}</td>
              <td class="num">{{ row.person_count }}</td>
              <td>{{ row.topic_name || "未分类" }}</td>
              <td>{{ row.brigade_name || "—" }}</td>
            </tr>
            <tr v-if="!brigadeTrainingRows.length">
              <td colspan="5">
                <div class="empty" style="padding: 32px 20px">
                  <h4>暂无场次</h4>
                  <p>该主办单位在当前周期内没有培训记录。</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <template #footer>
        <button class="btn btn--ghost" @click="brigadeTrainingVisible = false">关闭</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from "vue";
import * as echarts from "echarts";
import { ElMessage } from "element-plus";
import http from "../api/http";
import AppIcon from "../components/AppIcon.vue";
import { formatMinutesAxisHours, formatTrainingHours } from "../utils/duration";

const chartRef = ref(null);
let chart;

const searchQ = ref("");
const districtOptions = ref([]);
const districtData = ref([]);
const districtFilter = ref();
const brigadeOptions = ref([]);
const brigadeData = ref([]);
const brigadeFilter = ref();
const rankMetric = ref("duration");
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
/** 统计区间默认取「当前自然年/月/日」，避免直接用 new Date() 变成「今天→明年今天」 */
function defaultPeriodValue(mode) {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  if (mode === "year") return String(y);
  if (mode === "month") return `${y}-${m}`;
  return `${y}-${m}-${String(now.getDate()).padStart(2, "0")}`;
}
const periodValue = ref(defaultPeriodValue("year"));
const brigadeTrainingVisible = ref(false);
const brigadeTrainingLoading = ref(false);
const brigadeTrainingRows = ref([]);

const canRebindPersons = computed(() => currentAdmin.value?.role === "detachment");

const nf = (n) => Number(n || 0).toLocaleString("zh-CN");

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
  if (brigadeFilter.value) {
    return selectedBrigadeStats.value?.total_minutes || 0;
  }
  return brigadeData.value.reduce((s, item) => s + Number(item.total_minutes || 0), 0);
});

const displayTotalMinutesLabel = computed(() => formatTrainingHours(displayTotalMinutes.value));

const displaySessionCount = computed(() => {
  if (brigadeFilter.value) {
    return selectedBrigadeStats.value?.session_count || 0;
  }
  return brigadeData.value.reduce((s, item) => s + Number(item.session_count || 0), 0);
});

const selectedBrigadeStats = computed(() => {
  const id = Number(brigadeFilter.value);
  return brigadeData.value.find((item) => Number(item.brigade_id) === id);
});

const displayPersonCount = computed(() => {
  if (brigadeFilter.value) return selectedBrigadeStats.value?.person_count || 0;
  return brigadeData.value.reduce((s, item) => s + Number(item.person_count || 0), 0);
});

const displayActiveBrigadeCount = computed(() => {
  return brigadeData.value.filter((item) => Number(item.session_count || 0) > 0).length;
});

/* ---- 展示辅助：统计口径文案 / 周期切换 / 主办单位名称 / 重置 ---- */
const periodLabelText = computed(() => {
  const d = normalizePeriodValue();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  if (periodMode.value === "year") return `${y} 年度`;
  if (periodMode.value === "month") return `${y} 年 ${m} 月`;
  return `${y} 年 ${m} 月 ${String(d.getDate()).padStart(2, "0")} 日`;
});

const brigadeSelectedName = computed(() => {
  if (!brigadeFilter.value) return "全市";
  const hit = brigadeOptions.value.find((b) => Number(b.id) === Number(brigadeFilter.value));
  return hit?.name || "已选主办单位";
});

function setPeriodMode(mode) {
  if (periodMode.value === mode) return;
  periodMode.value = mode;
  onPeriodModeChange();
}

function setRankMetric(metric) {
  if (rankMetric.value === metric) return;
  rankMetric.value = metric;
  renderChart();
}

function clearBrigade() {
  brigadeFilter.value = undefined;
  onBrigadeChange();
}

function resetFilters() {
  brigadeFilter.value = undefined;
  searchQ.value = "";
  periodMode.value = "year";
  periodValue.value = defaultPeriodValue("year");
  onPeriodChange();
}

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

function formatTime(iso) {
  return iso ? String(iso).replace("T", " ").slice(0, 16) : "";
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
            brigade_id: o.brigade_id,
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
  if (item.brigade_id == null) {
    ElMessage.warning("该记录未关联培训主办单位");
    return;
  }
  brigadeFilter.value = Number(item.brigade_id);
  await onBrigadeChange();
}

async function loadDistrictsMeta() {
  const { data } = await http.get("/api/admin/districts");
  districtOptions.value = [{ id: 0, name: "葫芦岛支队" }, ...(data || [])];
}

async function loadBrigadesMeta() {
  const { data } = await http.get("/api/admin/brigades");
  brigadeOptions.value = data || [];
}

async function loadCurrentAdmin() {
  const { data } = await http.get("/api/admin/me");
  currentAdmin.value = data;
}

async function loadDistrictStats() {
  const { data } = await http.get("/api/admin/stats/by-district", { params: statsParams() });
  districtData.value = data;
}

async function loadBrigadeStats() {
  const { data } = await http.get("/api/admin/stats/by-brigade", { params: statsParams() });
  brigadeData.value = data || [];
}

function renderBarChart() {
  if (!chartRef.value) return;
  if (!chart) chart = echarts.init(chartRef.value);
  const list = [...brigadeData.value].sort((a, b) => rankValue(b) - rankValue(a));
  const names = list.map((item) => item.brigade_name);
  const vals = list.map((item) => rankValue(item));
  chart.setOption(
    {
      tooltip: {
        trigger: "axis",
        formatter: (items) => {
          const p = items[0];
          return `${p.name}<br/>${formatRankValue(p.value)}`;
        },
      },
      grid: { left: 56, right: 24, bottom: 88, top: 24 },
      xAxis: {
        type: "category",
        data: names,
        axisTick: { show: false, alignWithLabel: true },
        axisLine: { lineStyle: { color: "#eaeff4" } },
        axisLabel: {
          rotate: 0,
          interval: 0,
          fontSize: 12,
          lineHeight: 16,
          color: "#5a6e82",
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
          color: "#5a6e82",
          formatter: (v) => rankMetric.value === "person" ? `${v} 人次` : formatMinutesAxisHours(v),
        },
        splitLine: { lineStyle: { color: "#eaeff4", type: "dashed" } },
      },
      series: [
        {
          type: "bar",
          data: vals,
          itemStyle: { color: "#1b6da3", borderRadius: [3, 3, 0, 0] },
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
        color: ["#114368", "#1b6da3", "#16794c", "#9a6207", "#d0342c", "#5a6e82"],
        title: {
          text: `${distName} — 暂无类型培训时长数据`,
          left: "center",
          subtext: "该区县暂无参训记录，或时长均为 0",
          textStyle: { fontSize: 15, fontWeight: 600, color: "#114368" },
          subtextStyle: { color: "#5a6e82" },
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
      color: ["#114368", "#1b6da3", "#16794c", "#9a6207", "#d0342c", "#5a6e82"],
      title: {
        text: `${distName} — 各类型培训时长占比`,
        left: "center",
        textStyle: { fontSize: 15, fontWeight: 600, color: "#114368" },
      },
      tooltip: {
        trigger: "item",
        formatter: (p) => `${p.name}<br/>${formatTrainingHours(p.value)} (${p.percent}%)`,
      },
      legend: { bottom: 0, type: "scroll", textStyle: { color: "#5a6e82" } },
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
  renderBarChart();
}

function rankValue(item) {
  return Number(rankMetric.value === "person" ? item.person_count : item.total_minutes) || 0;
}

function rankMetricLabel() {
  return rankMetric.value === "person" ? "培训人次" : "培训时长";
}

function formatRankValue(value) {
  return rankMetric.value === "person" ? `${value} 人次` : formatTrainingHours(value);
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
  await loadBrigadeStats();
  if (brigadeFilter.value) await loadBrigadeTrainings();
  await renderChart();
}

async function onPeriodModeChange() {
  periodValue.value = defaultPeriodValue(periodMode.value);
  await onPeriodChange();
}

async function loadBrigadeTrainings() {
  brigadeTrainingRows.value = [];
  if (!brigadeFilter.value) return;
  brigadeTrainingLoading.value = true;
  try {
    const { data } = await http.get("/api/admin/stats/trainings-by-brigade", {
      params: statsParams({ brigade_id: Number(brigadeFilter.value) }),
    });
    brigadeTrainingRows.value = data || [];
  } finally {
    brigadeTrainingLoading.value = false;
  }
}

async function onBrigadeChange() {
  await loadBrigadeTrainings();
  await renderChart();
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

async function openBrigadeTrainings() {
  if (!brigadeFilter.value || Number(brigadeFilter.value) <= 0) {
    ElMessage.info("请先选择培训主办单位");
    return;
  }
  brigadeTrainingVisible.value = true;
  await loadBrigadeTrainings();
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
  await loadBrigadesMeta();
  await loadBrigadeStats();
  await renderChart();
  window.addEventListener("resize", () => chart?.resize());
});

onUnmounted(() => {
  chart?.dispose();
  chart = null;
});
</script>

<style scoped>
.chart {
  width: 100%;
  height: 420px;
}
.kpi--click {
  cursor: pointer;
}
.kpi--click:focus-visible {
  outline: 2px solid var(--brand-500);
  outline-offset: 2px;
}
.ac-item {
  padding: 6px 0;
  line-height: 1.4;
}
.ac-title {
  margin-left: 8px;
  font-weight: 500;
  color: var(--ink-900);
}
.ac-sub {
  margin-top: 2px;
  margin-left: 52px;
  font-size: var(--fs-12);
  color: var(--ink-500);
}
</style>

<!-- 联想下拉 teleport 到 body，需单独提高层级，避免被图表/卡片遮挡 -->
<style>
.stats-search-suggest-popper {
  z-index: 5000 !important;
}
</style>
