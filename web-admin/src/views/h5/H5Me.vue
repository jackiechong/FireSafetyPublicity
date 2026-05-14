<template>
  <div>
    <div v-if="me" class="h5-profile">
      <div class="h5-name">{{ me.name || "（未填姓名）" }}</div>
      <div class="h5-sub">
        {{ me.district_name || "—" }} · {{ me.organization_name || "—" }}
      </div>
      <div class="h5-sub h5-mini">
        <span v-if="me.job_title">{{ me.job_title }} · </span>{{ me.phone || "—" }}
      </div>
      <button class="h5-link" @click="editProfile">修改资料</button>
    </div>

    <div class="h5-card">
      <div class="h5-section-title">我的培训记录</div>
      <div v-if="loading" class="h5-loading-small">加载中…</div>
      <div v-else-if="!trainings.length" class="h5-empty">暂无培训记录</div>
      <div v-else class="h5-list">
        <div v-for="t in trainings" :key="t.session_id" class="h5-item">
          <div class="h5-item-title">{{ t.title }}</div>
          <div class="h5-item-sub">
            {{ t.district_name }} · {{ t.organization_name }}
          </div>
          <div class="h5-item-meta">
            <span>{{ formatTime(t.start_at) }}</span>
            <span class="dot">·</span>
            <span>{{ formatTrainingMinutes(t.duration_minutes) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import mpHttp from "../../api/mpHttp";
import { ensureH5Login } from "../../utils/h5Auth";
import { formatTrainingMinutes } from "../../utils/duration";

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
.h5-profile {
  background: linear-gradient(135deg, #3949ab 0%, #5c6bc0 100%);
  color: #fff;
  padding: 18px 16px;
  border-radius: 12px;
  margin-bottom: 14px;
}
.h5-name {
  font-size: 18px;
  font-weight: 600;
}
.h5-sub {
  font-size: 13px;
  opacity: 0.9;
  margin-top: 4px;
}
.h5-mini {
  font-size: 12px;
  opacity: 0.8;
}
.h5-link {
  margin-top: 10px;
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  border: 0;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 12px;
}
.h5-card {
  background: #fff;
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.h5-section-title {
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
}
.h5-loading-small,
.h5-empty {
  color: #888;
  padding: 18px 0;
  text-align: center;
  font-size: 13px;
}
.h5-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.h5-item {
  border: 1px solid #eef0f5;
  border-radius: 10px;
  padding: 10px 12px;
  background: #fafbff;
}
.h5-item-title {
  font-weight: 600;
  color: #1a237e;
  font-size: 14px;
}
.h5-item-sub {
  margin-top: 3px;
  color: #555;
  font-size: 12px;
}
.h5-item-meta {
  margin-top: 4px;
  color: #888;
  font-size: 12px;
}
.dot {
  margin: 0 4px;
}
</style>
