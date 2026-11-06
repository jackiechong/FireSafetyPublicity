<template>
  <div class="me">
    <section v-if="me" class="me-profile">
      <div class="me-profile__top">
        <span class="me-avatar">{{ (me.name || "学").slice(0, 1) }}</span>
        <div class="me-identity">
          <h1>{{ me.name || "（未填姓名）" }}</h1>
          <p>{{ me.district_name || "—" }} · {{ me.organization_name || "—" }}</p>
        </div>
        <button class="btn btn--ghost btn--sm me-edit" @click="editProfile">修改资料</button>
      </div>
      <div class="me-profile__meta">
        <span v-if="me.job_title"><AppIcon name="users" :size="13" />{{ me.job_title }}</span>
        <span><AppIcon name="phone" :size="13" />{{ me.phone || "—" }}</span>
      </div>
    </section>

    <section class="card me-list">
      <div class="card__head">
        <h3>我的培训记录</h3>
        <div class="grow"></div>
        <span class="me-count num">{{ trainings.length }} 场</span>
      </div>

      <div v-if="loading" class="me-loading">
        <span class="me-spinner" aria-hidden="true"></span>
        <span>加载中…</span>
      </div>

      <div v-else-if="!trainings.length" class="empty">
        <div class="empty__art"><AppIcon name="calendar" :size="26" /></div>
        <h4>暂无培训记录</h4>
        <p>参加培训并完成扫码签到后，记录会显示在这里。</p>
      </div>

      <ul v-else class="me-items">
        <li v-for="t in trainings" :key="t.session_id" class="me-item">
          <div class="me-item__title">{{ t.title }}</div>
          <div class="me-item__sub">{{ t.district_name }} · {{ t.organization_name }}</div>
          <div class="me-item__meta">
            <span><AppIcon name="clock" :size="12" />{{ formatTime(t.start_at) }}</span>
            <span class="me-dot"></span>
            <span class="num">{{ formatTrainingMinutes(t.duration_minutes) }}</span>
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import mpHttp from "../../api/mpHttp";
import { ensureH5Login } from "../../utils/h5Auth";
import { formatTrainingMinutes } from "../../utils/duration";
import AppIcon from "../../components/AppIcon.vue";

const me = ref(null);
const trainings = ref([]);
const loading = ref(true);

function formatTime(iso) {
  if (!iso) return "";
  return String(iso).replace("T", " ").slice(0, 16);
}

async function init() {
  const profile = await ensureH5Login();
  if (!profile) return;
  me.value = profile;
  try {
    const { data } = await mpHttp.get("/api/mp/trainings");
    trainings.value = data || [];
  } catch {
    trainings.value = [];
  } finally {
    loading.value = false;
  }
}

function editProfile() {
  window.location.assign("/h5/bind");
}

onMounted(init);
</script>

<style scoped>
.me-profile {
  padding: 18px;
  margin-bottom: 12px;
  color: #fff;
  background: linear-gradient(168deg, #0f2e4d 0%, #0a2038 100%);
  border: 1px solid #123c5f;
}
.me-profile__top {
  display: flex;
  align-items: center;
  gap: 12px;
}
.me-avatar {
  width: 44px;
  height: 44px;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.24);
  font-size: var(--fs-16);
  font-weight: 600;
}
.me-identity {
  min-width: 0;
  flex: 1;
}
.me-identity h1 {
  font-size: var(--fs-16);
  font-weight: 600;
  letter-spacing: 0.01em;
}
.me-identity p {
  margin-top: 3px;
  font-size: var(--fs-12);
  color: #a9c4d9;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.me-edit {
  flex: none;
  height: 28px;
  color: #dbe8f3;
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.24);
}
.me-edit:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.16);
  border-color: rgba(255, 255, 255, 0.36);
}
.me-profile__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.14);
  font-size: var(--fs-12);
  color: #a9c4d9;
}
.me-profile__meta span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.me-list {
  overflow: hidden;
}
.me-count {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  font-size: var(--fs-12);
  color: var(--ink-600);
  background: var(--surface-3);
  border-radius: var(--r-sm);
}
.me-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 32px 16px;
  color: var(--ink-500);
  font-size: var(--fs-13);
}
.me-spinner {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid var(--line);
  border-top-color: var(--brand-600);
  animation: me-spin 720ms linear infinite;
}
@keyframes me-spin {
  to {
    transform: rotate(360deg);
  }
}

.me-items {
  list-style: none;
  margin: 0;
  padding: 4px 0;
}
.me-item {
  padding: 13px 18px;
  border-bottom: 1px solid var(--line-soft);
}
.me-item:last-child {
  border-bottom: 0;
}
.me-item__title {
  font-size: var(--fs-13);
  font-weight: 600;
  line-height: 1.5;
  color: var(--ink-900);
}
.me-item__sub {
  margin-top: 3px;
  font-size: var(--fs-12);
  color: var(--ink-500);
}
.me-item__meta {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 6px;
  font-size: var(--fs-12);
  color: var(--ink-500);
}
.me-item__meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.me-dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--ink-300);
}
</style>
