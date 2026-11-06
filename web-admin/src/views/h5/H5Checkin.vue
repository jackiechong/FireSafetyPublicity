<template>
  <div v-if="state === 'loading'" class="card h5-loading">
    <span class="h5-spinner" aria-hidden="true"></span>
    <p>正在加载培训信息…</p>
  </div>

  <div v-else-if="state === 'pick'" class="h5-pick">
    <section class="card h5-card">
      <div class="h5-card__head">
        <h3>选择培训场次</h3>
        <span class="badge badge--live">进行中 {{ activeList.length }}</span>
      </div>
      <p class="h5-tip">已按您所在区县优先排列当前开放扫码的活动场次。</p>

      <div v-if="!activeList.length" class="h5-empty">
        <div class="empty__art"><AppIcon name="calendar" :size="26" /></div>
        <h4>暂无可签到的活动培训</h4>
        <p>请确认现场已开始培训且未到结束时间，或稍后再试。</p>
      </div>

      <template v-else>
        <div class="session-list">
          <button
            v-for="t in activeList"
            :key="t.session_id"
            type="button"
            class="session"
            :class="{ 'is-on': pickedSessionId === t.session_id }"
            :aria-pressed="pickedSessionId === t.session_id"
            @click="pickedSessionId = t.session_id"
          >
            <span class="session__radio" aria-hidden="true"></span>
            <span class="session__body">
              <span class="session__title">{{ t.title }}</span>
              <span class="session__meta">
                <AppIcon name="building" :size="12" />{{ t.organization_name }}
              </span>
              <span class="session__meta">
                <AppIcon name="clock" :size="12" />{{ formatTime(t.start_at) }}
                <span v-if="t.same_district" class="badge badge--ok" style="margin-left: 6px">本区县</span>
              </span>
            </span>
          </button>
        </div>

        <p v-if="pickError" class="h5-error">{{ pickError }}</p>
      </template>
    </section>

    <div class="h5-fixed">
      <button
        v-if="activeList.length"
        class="btn btn--primary btn--block"
        :disabled="!pickedSessionId || picking"
        @click="submitPickCheckin"
      >
        {{ picking ? "提交中…" : "确认签到" }}
      </button>
      <button class="btn btn--ghost btn--block" @click="goMe">我的培训记录</button>
    </div>
  </div>

  <div v-else-if="state === 'ok'" class="h5-result">
    <section class="card h5-result__card">
      <div class="result-icon result-icon--ok"><AppIcon name="check" :size="30" /></div>
      <h2 class="result-title">{{ result.already_checked ? "您之前已签到" : "签到成功" }}</h2>
      <p class="result-sub">{{ result.already_checked ? "本次培训已记录在您的档案中" : "本次培训已计入个人培训档案" }}</p>

      <dl class="result-list">
        <div><dt>培训</dt><dd>{{ result.title }}</dd></div>
        <div><dt>主办单位</dt><dd>{{ result.organization_name }}</dd></div>
        <div v-if="result.location"><dt>地点</dt><dd>{{ result.location }}</dd></div>
        <div><dt>开始时间</dt><dd class="num">{{ formatTime(result.start_at) }}</dd></div>
        <div><dt>课时</dt><dd class="num">{{ formatMin(result.duration_minutes) }}</dd></div>
        <div v-if="me"><dt>本人</dt><dd>{{ me.name || "（未填）" }} · {{ me.organization_name || "" }}</dd></div>
      </dl>
    </section>

    <div class="h5-fixed">
      <button class="btn btn--primary btn--block" @click="goMe">查看我的培训记录</button>
    </div>
  </div>

  <div v-else class="h5-result">
    <section class="card h5-result__card">
      <div class="result-icon result-icon--warn"><AppIcon name="alert" :size="28" /></div>
      <h2 class="result-title">无法签到</h2>
      <p class="result-error">{{ errorMsg }}</p>
      <p class="h5-tip" style="text-align: center">
        若签到码已过期，请联系现场组织人员重新生成；如信息有误，可先完善实名信息。
      </p>
    </section>

    <div class="h5-fixed">
      <button class="btn btn--primary btn--block" @click="retry">重试</button>
      <button class="btn btn--ghost btn--block" @click="goMe">我的培训记录</button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import mpHttp from "../../api/mpHttp";
import { ensureH5Login } from "../../utils/h5Auth";
import { formatTrainingMinutes } from "../../utils/duration";
import AppIcon from "../../components/AppIcon.vue";

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
  display: grid;
  place-items: center;
  gap: 12px;
  padding: 48px 20px;
  color: var(--ink-500);
  font-size: var(--fs-13);
}
.h5-spinner {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 2px solid var(--line);
  border-top-color: var(--brand-600);
  animation: spin 720ms linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.h5-card {
  padding: 18px 16px;
}
.h5-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.h5-card__head h3 {
  font-size: var(--fs-16);
  font-weight: 600;
  color: var(--ink-900);
}
.h5-tip {
  margin-top: 6px;
  font-size: var(--fs-12);
  line-height: 1.6;
  color: var(--ink-500);
}

.session-list {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}
.session {
  display: flex;
  gap: 11px;
  width: 100%;
  padding: 13px 13px;
  text-align: left;
  background: var(--surface);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-md);
  cursor: pointer;
  transition: border-color var(--t-fast), background var(--t-fast);
}
.session:active {
  background: var(--surface-2);
}
.session.is-on {
  border-color: var(--brand-500);
  background: var(--brand-50);
  box-shadow: 0 0 0 3px rgba(27, 109, 163, 0.12);
}
.session__radio {
  width: 16px;
  height: 16px;
  flex: none;
  margin-top: 2px;
  border-radius: 50%;
  border: 1.5px solid var(--line-strong);
  background: #fff;
}
.session.is-on .session__radio {
  border-color: var(--brand-600);
  border-width: 5px;
}
.session__body {
  min-width: 0;
  display: grid;
  gap: 4px;
}
.session__title {
  font-size: var(--fs-13);
  font-weight: 600;
  line-height: 1.45;
  color: var(--ink-900);
}
.session__meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-12);
  color: var(--ink-500);
}

.h5-error {
  margin-top: 12px;
  font-size: var(--fs-12);
  color: var(--fire-500);
  text-align: center;
}

.h5-fixed {
  position: sticky;
  bottom: 0;
  display: grid;
  gap: 8px;
  margin-top: 16px;
  padding: 12px 0 calc(12px + env(safe-area-inset-bottom, 0px));
  background: linear-gradient(180deg, rgba(238, 242, 246, 0) 0%, var(--bg) 34%);
}
.h5-fixed .btn {
  height: 46px;
  font-size: var(--fs-14);
}

.h5-result__card {
  padding: 26px 18px 20px;
  text-align: center;
}
.result-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto 14px;
  display: grid;
  place-items: center;
  border-radius: 50%;
}
.result-icon--ok {
  background: var(--ok-100);
  color: var(--ok-500);
}
.result-icon--warn {
  background: var(--warn-100);
  color: var(--warn-500);
}
.result-title {
  font-size: var(--fs-20);
  font-weight: 600;
  color: var(--ink-900);
}
.result-sub {
  margin-top: 5px;
  font-size: var(--fs-12);
  color: var(--ink-500);
}
.result-error {
  margin-top: 10px;
  font-size: var(--fs-13);
  line-height: 1.6;
  color: var(--fire-500);
}

.result-list {
  margin: 18px 0 0;
  padding: 14px;
  text-align: left;
  background: var(--surface-2);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
}
.result-list > div {
  display: flex;
  gap: 10px;
  padding: 5px 0;
  font-size: var(--fs-13);
}
.result-list dt {
  flex: none;
  width: 64px;
  color: var(--ink-500);
}
.result-list dd {
  margin: 0;
  color: var(--ink-900);
  line-height: 1.5;
}
</style>
