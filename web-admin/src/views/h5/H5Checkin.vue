<template>
  <div v-if="state === 'loading'" class="h5-loading">加载中…</div>

  <div v-else-if="state === 'pick'" class="h5-card">
    <h3 class="h5-pick-title">选择培训场次</h3>
    <p class="h5-pick-tip">已按您所在区县优先排列当前开放扫码的活动场次。</p>
    <el-alert v-if="!activeList.length" type="warning" show-icon :closable="false" title="暂无可签到的活动培训" description="请确认现场已开始培训且未到结束时间，或稍后再试。" />
    <template v-else>
      <el-select v-model="pickedSessionId" placeholder="请选择场次" class="h5-pick-select" filterable>
        <el-option
          v-for="t in activeList"
          :key="t.session_id"
          :label="pickLabel(t)"
          :value="t.session_id"
        />
      </el-select>
      <button class="h5-btn-primary" :disabled="!pickedSessionId || picking" @click="submitPickCheckin">
        {{ picking ? "提交中…" : "确认签到" }}
      </button>
      <p v-if="pickError" class="h5-err">{{ pickError }}</p>
    </template>
    <button class="h5-btn-secondary" @click="goMe">我的培训记录</button>
  </div>

  <div v-else-if="state === 'ok'" class="h5-card h5-ok">
    <div class="h5-ok-icon">✔</div>
    <div class="h5-ok-text">
      {{ result.already_checked ? "您之前已签到" : "签到成功" }}
    </div>
    <div class="h5-ok-sub">
      <div><b>培训：</b>{{ result.title }}</div>
      <div><b>主办单位：</b>{{ result.organization_name }}</div>
      <div v-if="result.location"><b>地点：</b>{{ result.location }}</div>
      <div><b>开始时间：</b>{{ formatTime(result.start_at) }}</div>
      <div><b>课时：</b>{{ formatMin(result.duration_minutes) }}</div>
      <div v-if="me"><b>本人：</b>{{ me.name || "（未填）" }} · {{ me.organization_name || "" }}</div>
    </div>
    <button class="h5-btn-secondary" @click="goMe">我的培训记录</button>
  </div>

  <div v-else class="h5-card h5-err-card">
    <div class="h5-err-title">无法签到</div>
    <div class="h5-err-body">{{ errorMsg }}</div>
    <button class="h5-btn-secondary" @click="retry">重试</button>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import mpHttp from "../../api/mpHttp";
import { ensureH5Login } from "../../utils/h5Auth";
import { formatTrainingMinutes } from "../../utils/duration";

const state = ref("loading"); // loading | pick | ok | error
const result = ref(null);
const me = ref(null);
const errorMsg = ref("");

const activeList = ref([]);
const pickedSessionId = ref(undefined);
const picking = ref(false);
const pickError = ref("");

function getSessionIdFromUrl() {
  try {
    return Number(new URL(window.location.href).searchParams.get("session_id")) || 0;
  } catch {
    return 0;
  }
}

function formatTime(iso) {
  if (!iso) return "";
  return String(iso).replace("T", " ").slice(0, 16);
}
function formatMin(m) {
  return formatTrainingMinutes(m);
}

function pickLabel(t) {
  const tag = t.same_district ? "【本区县】" : "";
  return `${tag}${t.title} · ${t.organization_name} · ${formatTime(t.start_at)}`;
}

async function loadActiveTrainings() {
  const { data } = await mpHttp.get("/api/mp/active-trainings");
  activeList.value = data || [];
  if (activeList.value.length === 1) {
    pickedSessionId.value = activeList.value[0].session_id;
  }
}

async function submitPickCheckin() {
  pickError.value = "";
  if (!pickedSessionId.value) return;
  picking.value = true;
  try {
    const { data } = await mpHttp.post("/api/mp/checkin", { session_id: pickedSessionId.value });
    result.value = data;
    state.value = "ok";
  } catch (e) {
    pickError.value = e?.response?.data?.detail || "签到失败";
  } finally {
    picking.value = false;
  }
}

async function init() {
  const sid = getSessionIdFromUrl();
  const profile = await ensureH5Login(sid);
  if (!profile) return;
  me.value = profile;

  if (!profile.name || !profile.phone || !profile.district_id || !profile.organization_id) {
    const q = sid ? `?session_id=${sid}` : "";
    window.location.replace(`/h5/bind${q}`);
    return;
  }

  if (!sid) {
    try {
      await loadActiveTrainings();
      state.value = "pick";
    } catch (e) {
      errorMsg.value = e?.response?.data?.detail || "加载场次失败";
      state.value = "error";
    }
    return;
  }

  try {
    const { data } = await mpHttp.post("/api/mp/checkin", { session_id: sid });
    result.value = data;
    state.value = "ok";
  } catch (e) {
    errorMsg.value = e?.response?.data?.detail || "签到失败，请稍后重试";
    state.value = "error";
  }
}

function retry() {
  state.value = "loading";
  errorMsg.value = "";
  init();
}

function goMe() {
  window.location.assign("/h5/me");
}

onMounted(init);
</script>

<style scoped>
.h5-loading {
  text-align: center;
  color: #888;
  padding: 60px 0;
}
.h5-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.h5-pick-title {
  margin: 0 0 8px;
  font-size: 17px;
  color: #1a237e;
}
.h5-pick-tip {
  margin: 0 0 16px;
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}
.h5-pick-select {
  width: 100%;
  margin-bottom: 14px;
}
.h5-btn-primary {
  width: 100%;
  height: 44px;
  background: #3949ab;
  color: #fff;
  border: 0;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 10px;
}
.h5-btn-primary[disabled] {
  opacity: 0.6;
}
.h5-err {
  color: #d32f2f;
  font-size: 13px;
  margin: 8px 0 0;
}
.h5-ok {
  text-align: center;
}
.h5-ok-icon {
  width: 64px;
  height: 64px;
  line-height: 64px;
  margin: 0 auto 10px;
  border-radius: 50%;
  background: #4caf50;
  color: #fff;
  font-size: 32px;
  font-weight: bold;
}
.h5-ok-text {
  font-size: 17px;
  font-weight: 600;
  color: #1a237e;
  margin-bottom: 12px;
}
.h5-ok-sub {
  background: #f5f7ff;
  border-radius: 8px;
  padding: 12px;
  font-size: 13px;
  color: #444;
  line-height: 1.8;
  text-align: left;
}
.h5-btn-secondary {
  width: 100%;
  height: 40px;
  margin-top: 16px;
  background: #e8eaf6;
  color: #1a237e;
  border: 0;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
}
.h5-err-card {
  text-align: center;
}
.h5-err-title {
  font-size: 16px;
  color: #d32f2f;
  font-weight: 600;
  margin-bottom: 10px;
}
.h5-err-body {
  color: #555;
  font-size: 13px;
}
</style>
