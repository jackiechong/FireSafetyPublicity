<template>
  <div>
    <div class="page-head">
      <div class="page-head__main">
        <div class="eyebrow">数据概览</div>
        <h1 class="page-title">全市培训运行总览</h1>
        <p class="page-desc">{{ scopeText }} · {{ periodLabel }} · 数据截至 {{ updatedAt }}</p>
      </div>
      <div class="page-actions">
        <div class="seg">
          <button :class="{ 'is-on': periodMode === 'year' }" @click="setMode('year')">按年</button>
          <button :class="{ 'is-on': periodMode === 'month' }" @click="setMode('month')">按月</button>
        </div>
        <el-date-picker
          v-model="periodValue"
          :type="periodMode"
          :format="periodMode === 'year' ? 'YYYY年' : 'YYYY年MM月'"
          :value-format="periodMode === 'year' ? 'YYYY' : 'YYYY-MM'"
          :clearable="false"
          style="width: 132px"
          @change="loadAll"
        />
        <button class="btn btn--ghost" @click="loadAll">
          <AppIcon name="refresh" :size="15" />刷新
        </button>
      </div>
    </div>

    <div class="grid grid--kpi" style="margin-bottom: 20px">
      <article class="kpi kpi--accent">
        <div class="kpi__label"><AppIcon name="clock" :size="13" />{{ periodMode === "year" ? "年度" : "月度" }}培训时长</div>
        <div class="kpi__value num">{{ hours }}<small>小时</small></div>
        <div class="kpi__foot">
          <span>{{ totalSessions }} 场培训 · 场均 {{ avgHours }} 小时</span>
        </div>
      </article>

      <article class="kpi">
        <div class="kpi__label"><AppIcon name="calendar" :size="13" />培训场次</div>
        <div class="kpi__value num">{{ totalSessions }}<small>场</small></div>
        <div class="kpi__foot"><span>进行中 {{ activeSessions }} 场</span></div>
      </article>

      <article class="kpi">
        <div class="kpi__label"><AppIcon name="users" :size="13" />参训人次</div>
        <div class="kpi__value num">{{ nf(attendanceTotal) }}<small>人次</small></div>
        <div class="kpi__foot"><span>实名签到累计</span></div>
      </article>

      <article class="kpi">
        <div class="kpi__label"><AppIcon name="building" :size="13" />覆盖单位</div>
        <div class="kpi__value num">{{ nf(orgTotal) }}<small>家</small></div>
        <div class="kpi__foot"><span>已登记人员 {{ nf(personTotal) }} 人</span></div>
      </article>
    </div>

    <div class="grid grid--2-1" style="margin-bottom: 20px">
      <section class="card">
        <div class="card__head">
          <h3>大队{{ rankMetric === "person" ? "人次" : "培训时长" }}排行</h3>
          <span class="sub">{{ periodLabel }} · 含葫芦岛支队</span>
          <div class="grow"></div>
          <div class="seg">
            <button :class="{ 'is-on': rankMetric === 'duration' }" @click="rankMetric = 'duration'">时长</button>
            <button :class="{ 'is-on': rankMetric === 'person' }" @click="rankMetric = 'person'">人次</button>
          </div>
        </div>
        <div class="card__body">
          <div v-if="brigadeRanks.length" class="rank rank--aligned">
            <div v-for="(row, i) in brigadeRanks" :key="row.brigade_name" class="rank__row">
              <span class="rank__no num">{{ String(i + 1).padStart(2, "0") }}</span>
              <span class="rank__name" :title="row.brigade_name">{{ row.brigade_name }}</span>
              <span class="rank__track">
                <span class="rank__fill" :style="{ width: pct(row.value, brigadeMax) + '%' }"></span>
              </span>
              <span class="rank__val">
                {{ rankMetric === "person" ? nf(row.value) : (row.value / 60).toFixed(1) }}<small>{{ rankMetric === "person" ? "人次" : "小时" }}</small>
                <small> · {{ row.session_count }}场</small>
              </span>
            </div>
          </div>
          <div v-else class="empty">
            <div class="empty__art"><AppIcon name="chart" :size="26" /></div>
            <h4>本期暂无培训数据</h4>
            <p>切换统计周期，或先在培训记录中登记一场培训。</p>
          </div>
        </div>
      </section>

      <section class="card">
        <div class="card__head">
          <h3>培训主题分布</h3>
          <div class="grow"></div>
          <span class="sub">按场次</span>
        </div>
        <div class="card__body">
          <div v-if="topicRanks.length" class="rank rank--stack">
            <div v-for="(row, i) in topicRanks" :key="row.name" class="rank__row">
              <span class="rank__no num">{{ String(i + 1).padStart(2, "0") }}</span>
              <span class="rank__name" :title="row.name">{{ row.name }}</span>
              <span class="rank__val">{{ row.pct }}<small>%</small><small> · {{ row.count }}场</small></span>
              <span class="rank__track">
                <span class="rank__fill" :style="{ width: row.pct + '%' }"></span>
              </span>
            </div>
          </div>
          <div v-else class="empty">
            <div class="empty__art"><AppIcon name="layers" :size="26" /></div>
            <h4>暂无主题分布</h4>
            <p>培训登记时选择主题分类后，这里会按场次汇总。</p>
          </div>
        </div>
      </section>
    </div>

    <div class="grid grid--2-1" style="margin-bottom: 20px">
      <section class="card">
        <div class="card__head">
          <h3>月度培训场次</h3>
          <span class="sub">{{ chartYear }} 年{{ peakMonth ? ` · 峰值出现在 ${peakMonth} 月` : "" }}</span>
          <div class="grow"></div>
          <router-link class="linkbtn" to="/stats">查看统计<AppIcon name="chevron" :size="12" /></router-link>
        </div>
        <div class="card__body" style="padding: 12px 16px 8px">
          <ColumnChart :values="monthValues" :labels="monthLabels" unit="场" aria-label="月度培训场次趋势" />
        </div>
      </section>

      <section class="card">
        <div class="card__head">
          <h3>今日运行快照</h3>
          <div class="grow"></div>
          <span class="badge badge--live">实时</span>
        </div>
        <div class="card__body">
          <div class="snap">
            <div class="snap__cell"><b class="num">{{ todaySessions }}</b><span>今日培训场次</span></div>
            <div class="snap__cell"><b class="num">{{ todayPeople }}</b><span>今日参训人数</span></div>
            <div class="snap__cell is-live"><b class="num">{{ activeSessions }}</b><span>进行中场次</span></div>
            <div class="snap__cell"><b class="num">{{ topicRanks.length }}</b><span>已使用主题</span></div>
          </div>

          <div style="margin-top: 16px; display: grid; gap: 8px">
            <router-link class="todo" to="/trainings">
              <span class="todo__dot" style="background: #d0342c"></span>
              <span class="todo__txt">
                <b>{{ overdueSessions }} 场培训超过 2 小时未结束</b>
                <span>建议核对后手动结束</span>
              </span>
              <AppIcon name="chevron" :size="14" />
            </router-link>
            <router-link class="todo" to="/orgs">
              <span class="todo__dot" style="background: #9a6207"></span>
              <span class="todo__txt">
                <b>{{ orgsMissingContact }} 家单位缺少联系人</b>
                <span>影响培训通知送达</span>
              </span>
              <AppIcon name="chevron" :size="14" />
            </router-link>
            <router-link class="todo" to="/persons">
              <span class="todo__dot" style="background: #1f6fa8"></span>
              <span class="todo__txt">
                <b>已登记人员 {{ nf(personTotal) }} 人</b>
                <span>覆盖 {{ nf(orgTotal) }} 家单位</span>
              </span>
              <AppIcon name="chevron" :size="14" />
            </router-link>
          </div>
        </div>
      </section>
    </div>

    <section class="card">
      <div class="card__head">
        <h3>近期培训会议</h3>
        <span class="sub">最近 {{ recentTrainings.length }} 场</span>
        <div class="grow"></div>
        <router-link class="btn btn--ghost btn--sm" to="/trainings">全部记录</router-link>
      </div>
      <div class="tablewrap">
        <table class="tb">
          <thead>
            <tr>
              <th>培训主题</th>
              <th style="width: 160px">主题分类</th>
              <th style="width: 92px">状态</th>
              <th style="width: 120px">主办单位</th>
              <th style="width: 118px">开始时间</th>
              <th class="num" style="width: 76px">时长</th>
              <th class="num" style="width: 70px">参训</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in recentTrainings" :key="row.id">
              <td>
                <span class="cell-main">{{ row.title }}</span>
                <span v-if="row.location" class="cell-sub"><AppIcon name="pin" :size="12" />{{ row.location }}</span>
              </td>
              <td>{{ row.topic_name || "未分类" }}</td>
              <td>
                <span class="badge" :class="row.is_active === false ? 'badge--done' : 'badge--live'">
                  {{ row.is_active === false ? "已结束" : "进行中" }}
                </span>
              </td>
              <td>{{ row.brigade_name || "—" }}</td>
              <td class="num">{{ fmt(row.start_at) }}</td>
              <td class="num">{{ row.duration_minutes }} 分</td>
              <td class="num">{{ row.person_count }}</td>
            </tr>
            <tr v-if="!recentTrainings.length">
              <td colspan="7">
                <div class="empty">
                  <div class="empty__art"><AppIcon name="calendar" :size="26" /></div>
                  <h4>还没有培训记录</h4>
                  <p>登记第一场培训后，这里会显示最近的运行情况。</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import http from "../api/http";
import AppIcon from "../components/AppIcon.vue";
import ColumnChart from "../components/ColumnChart.vue";

const periodMode = ref("year");
const periodValue = ref(String(new Date().getFullYear()));
const rankMetric = ref("duration");

const currentAdmin = ref(null);
const brigadeStats = ref([]);
const topicStats = ref([]);
const periodTrainings = ref([]);
const yearTrainings = ref([]);
const persons = ref([]);
const orgs = ref([]);
const updatedAt = ref("—");

const MONTHS = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"];

const scopeText = computed(() => (currentAdmin.value?.role === "detachment" ? "葫芦岛支队" : "本大队"));
const periodLabel = computed(() => {
  const raw = String(periodValue.value || "");
  return periodMode.value === "year" ? `${raw} 年度` : `${raw.replace("-", " 年 ")} 月`;
});

const totalMinutes = computed(() => brigadeStats.value.reduce((s, x) => s + Number(x.total_minutes || 0), 0));
const totalSessions = computed(() => brigadeStats.value.reduce((s, x) => s + Number(x.session_count || 0), 0));
const attendanceTotal = computed(() => periodTrainings.value.reduce((s, x) => s + Number(x.person_count || 0), 0));
const personTotal = computed(() => persons.value.length);
const orgTotal = computed(() => orgs.value.length);
const hours = computed(() => (totalMinutes.value / 60).toFixed(1));
const avgHours = computed(() => (totalSessions.value ? (totalMinutes.value / 60 / totalSessions.value).toFixed(2) : "0.00"));

const activeSessions = computed(() => yearTrainings.value.filter((x) => x.is_active !== false).length);
const overdueSessions = computed(() => {
  const now = Date.now();
  return yearTrainings.value.filter((x) => {
    if (x.is_active === false || !x.start_at) return false;
    return now - new Date(x.start_at).getTime() > 2 * 3600 * 1000;
  }).length;
});
const orgsMissingContact = computed(() => orgs.value.filter((o) => !o.contact_name).length);

const brigadeRanks = computed(() =>
  [...brigadeStats.value]
    .sort((a, b) => rankValue(b) - rankValue(a))
    .slice(0, 10)
    .map((x) => ({ ...x, value: rankValue(x) }))
);
const brigadeMax = computed(() => Math.max(1, ...brigadeRanks.value.map((x) => x.value)));

function rankValue(item) {
  return Number(rankMetric.value === "person" ? item.person_count : item.total_minutes) || 0;
}

const topicRanks = computed(() => {
  // 按「场次」统计：直接用年度培训清单分组，避免统计接口口径不一致
  const byTopic = new Map();
  for (const t of yearTrainings.value) {
    const name = t.topic_name || "未分类";
    byTopic.set(name, (byTopic.get(name) || 0) + 1);
  }
  const total = yearTrainings.value.length || 1;
  return [...byTopic.entries()]
    .map(([name, count]) => ({ name, count, pct: Math.round((count / total) * 100) }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6);
});

const chartYear = computed(() => {
  const raw = String(periodValue.value || "");
  return periodMode.value === "year" ? raw : raw.slice(0, 4);
});

const monthValues = computed(() => {
  const counts = new Array(12).fill(0);
  for (const t of yearTrainings.value) {
    if (!t.start_at) continue;
    const m = new Date(t.start_at).getMonth();
    if (m >= 0 && m < 12) counts[m] += 1;
  }
  return counts;
});
const monthLabels = computed(() => MONTHS);
const peakMonth = computed(() => {
  const max = Math.max(...monthValues.value);
  if (!max) return 0;
  return monthValues.value.indexOf(max) + 1;
});

const todaySessions = computed(() => {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(end.getDate() + 1);
  return yearTrainings.value.filter((x) => inRange(x.start_at, start, end)).length;
});
const todayPeople = computed(() => {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(end.getDate() + 1);
  return yearTrainings.value
    .filter((x) => inRange(x.start_at, start, end))
    .reduce((s, x) => s + Number(x.person_count || 0), 0);
});

const recentTrainings = computed(() =>
  [...yearTrainings.value]
    .sort((a, b) => String(b.start_at).localeCompare(String(a.start_at)))
    .slice(0, 6)
);

function inRange(iso, start, end) {
  if (!iso) return false;
  const t = new Date(iso).getTime();
  return t >= start.getTime() && t < end.getTime();
}

function nf(n) {
  return Number(n || 0).toLocaleString("zh-CN");
}

function fmt(v) {
  return v ? String(v).replace("T", " ").slice(0, 16) : "—";
}

function pct(v, max) {
  return Math.round((Number(v || 0) / (max || 1)) * 1000) / 10;
}

function periodParams() {
  const raw = String(periodValue.value || "");
  if (periodMode.value === "month") {
    const [y, m] = raw.split("-").map(Number);
    const start = new Date(y, (m || 1) - 1, 1);
    const end = new Date(y, (m || 1), 1);
    return { start: toIso(start), end: toIso(end) };
  }
  const y = Number(raw);
  return { start: toIso(new Date(y, 0, 1)), end: toIso(new Date(y + 1, 0, 1)) };
}

function yearParams() {
  const y = Number(chartYear.value);
  return { start: toIso(new Date(y, 0, 1)), end: toIso(new Date(y + 1, 0, 1)) };
}

function toIso(d) {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T00:00:00`;
}

function setMode(mode) {
  if (periodMode.value === mode) return;
  periodMode.value = mode;
  const now = new Date();
  periodValue.value =
    mode === "year" ? String(now.getFullYear()) : `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  loadAll();
}

async function loadAll() {
  const params = periodParams();
  const yParams = yearParams();
  try {
    const [me, brigades, topics, periodSummary, yearSummary, people, organizations] = await Promise.all([
      http.get("/api/admin/me"),
      http.get("/api/admin/stats/by-brigade", { params }),
      http.get("/api/admin/stats/by-topic", { params }),
      http.get("/api/admin/stats/training-summary", { params }),
      http.get("/api/admin/stats/training-summary", { params: yParams }),
      http.get("/api/admin/persons"),
      http.get("/api/admin/organizations"),
    ]);
    currentAdmin.value = me.data;
    brigadeStats.value = brigades.data || [];
    topicStats.value = topics.data || [];
    periodTrainings.value = periodSummary.data || [];
    yearTrainings.value = yearSummary.data || [];
    persons.value = people.data || [];
    orgs.value = organizations.data || [];
    updatedAt.value = new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  } catch (e) {
    console.error(e);
  }
}

onMounted(loadAll);
</script>
