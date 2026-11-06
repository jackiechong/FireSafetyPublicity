<template>
  <div class="m-admin">
    <header class="m-page__head">
      <div class="eyebrow">现场管理</div>
      <h1 class="m-page__title">培训管理</h1>
      <p class="m-page__desc">{{ scopeText }} · 快速建场并生成签到二维码</p>
    </header>

    <section class="card m-panel">
      <div class="m-panel__head">
        <h2>新建培训</h2>
        <span class="sub">扫码签到</span>
      </div>
      <div class="m-panel__body">
        <p class="m-note">填写信息后生成二维码，受训人员用微信扫码即可签到。</p>

        <div class="m-field">
          <label class="m-field__label" for="m-title">培训标题<span class="req">*</span></label>
          <el-input id="m-title" v-model="form.title" placeholder="如：电气火灾防范培训" maxlength="100" />
        </div>

        <div class="m-field">
          <span class="m-field__label">所在区县</span>
          <el-select
            v-model="form.districtId"
            placeholder="选择区县"
            filterable
            class="m-w-full"
            @change="onDistrictChange"
          >
            <el-option v-for="d in districts" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </div>

        <div class="m-field">
          <span class="m-field__label">参训单位<span class="req">*</span></span>
          <el-select
            v-model="form.organizationId"
            placeholder="选择单位"
            filterable
            class="m-w-full"
            :disabled="!form.districtId"
          >
            <el-option
              v-for="o in orgsInDistrict"
              :key="o.id"
              :label="`${o.name}（${orgTypeName(o.org_type)}）`"
              :value="o.id"
            />
          </el-select>
        </div>

        <div class="m-field">
          <span class="m-field__label">时长（分钟）</span>
          <el-input-number
            v-model="form.durationMinutes"
            :min="15"
            :max="480"
            :step="15"
            controls-position="right"
            class="m-w-full"
          />
          <div class="m-hint">建议 30–180 分钟，按 15 分钟增减</div>
        </div>

        <div class="m-field">
          <label class="m-field__label" for="m-location">地点（选填）</label>
          <el-input id="m-location" v-model="form.location" placeholder="如：单位会议室" />
        </div>

        <button
          class="btn btn--primary btn--block m-submit"
          type="button"
          :disabled="creating"
          @click="createTraining"
        >
          <AppIcon :name="creating ? 'refresh' : 'plus'" :size="15" />
          {{ creating ? "创建中…" : "创建并生成二维码" }}
        </button>
      </div>
    </section>

    <section class="card m-panel">
      <div class="m-panel__head">
        <h2>我管理的培训</h2>
        <span class="sub">{{ trainings.length }} 场 · {{ scopeText }}</span>
      </div>
      <div class="m-panel__body">
        <p v-if="trainingLoading" class="m-note">正在加载培训列表…</p>

        <div v-else-if="!trainings.length" class="empty">
          <div class="empty__art"><AppIcon name="qr" :size="26" /></div>
          <h4>暂无培训</h4>
          <p>在上方填写信息创建第一场培训，即可生成签到二维码。</p>
        </div>

        <div v-else class="m-list">
          <button
            v-for="t in trainings"
            :key="t.id"
            class="m-cardrow"
            type="button"
            @click="openQrcode(t.id)"
          >
            <span class="m-cardrow__top">
              <span class="m-cardrow__title">{{ t.title }}</span>
              <span class="badge" :class="t.is_active === false ? 'badge--done' : 'badge--live'">
                {{ t.is_active === false ? "已结束" : "进行中" }}
              </span>
            </span>
            <span class="m-cardrow__sub">{{ orgName(t.organization_id) }} · {{ formatTime(t.start_at) }}</span>
            <span class="m-cardrow__foot">
              <span class="m-chip num">{{ formatTrainingMinutes(t.duration_minutes) }}</span>
              <span class="m-cardrow__loc">{{ t.location || "未填地点" }}</span>
              <span class="m-cardrow__go">查看二维码<AppIcon name="chevron" :size="13" /></span>
            </span>
          </button>
        </div>
      </div>
    </section>

    <el-dialog
      v-model="qrcodeOpen"
      :title="qrcodeData ? qrcodeData.title : '培训二维码'"
      width="92%"
      align-center
      destroy-on-close
      class="m-qr-dialog"
    >
      <div v-if="qrcodeData" class="m-qr">
        <div class="m-qr__frame">
          <canvas ref="qrCanvas" class="m-qr__canvas" />
        </div>

        <dl class="m-qr__meta">
          <div><dt>单位</dt><dd>{{ qrcodeData.organization_name }}</dd></div>
          <div><dt>大队</dt><dd>{{ qrcodeData.brigade_name }}</dd></div>
          <div><dt>开始</dt><dd>{{ formatTime(qrcodeData.start_at) }}</dd></div>
          <div><dt>时长</dt><dd>{{ formatTrainingMinutes(qrcodeData.duration_minutes) }}</dd></div>
          <div v-if="qrcodeData.location"><dt>地点</dt><dd>{{ qrcodeData.location }}</dd></div>
          <div><dt>已签到</dt><dd>{{ qrcodeData.attendance_count }} 人</dd></div>
        </dl>

        <div class="m-qr__url">
          <span class="m-qr__url-label">本场扫码地址</span>
          <span class="m-qr__url-text">{{ qrcodeUrl }}</span>
        </div>

        <div v-if="universalLoginDisplay" class="m-qr__url">
          <span class="m-qr__url-label">通用入口（登录后自选场次）</span>
          <span class="m-qr__url-text">{{ universalLoginDisplay }}</span>
        </div>

        <p class="m-qr__tip">
          本场培训：用微信扫上方码即进入本场签到。无固定场次时，可另做「通用入口」二维码，扫码登录后在列表里选择当前活动培训。
        </p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import QRCode from "qrcode";
import http from "../../api/http";
import AppIcon from "../../components/AppIcon.vue";
import { formatTrainingMinutes } from "../../utils/duration";

const districts = ref([]);
const orgs = ref([]); // 全量单位（用于显示已建培训对应的单位名）
const orgsInDistrict = ref([]);
const trainings = ref([]);
const trainingLoading = ref(false);
const creating = ref(false);

const me = ref(null);

const form = ref({
  title: "",
  districtId: undefined,
  organizationId: undefined,
  durationMinutes: 60,
  location: "",
});

const qrcodeOpen = ref(false);
const qrcodeData = ref(null);
const qrCanvas = ref(null);
const qrcodeUrl = ref("");
const orgTypes = ref([]);

function orgTypeName(value) {
  return orgTypes.value.find((t) => t.code === value)?.name || value || "其他部门";
}

const universalLoginDisplay = computed(() => {
  const raw = qrcodeData.value?.portal_login_url;
  if (raw && /^https?:\/\//i.test(String(raw))) return String(raw);
  const qs = new URLSearchParams({ next: "/h5/checkin" }).toString();
  return `${window.location.origin}/api/wxoa/login?${qs}`;
});

/** 把后端返回的 qr_payload 统一变成一段「能让微信扫码后直接打开」的完整 URL：
 *  - 后端配了 WECHAT_OA_REDIRECT_HOST 时直接返回完整 URL
 *  - 否则形如 "session_id=5"，由前端用当前 origin 拼成 /api/wxoa/login?session_id=5 */
function resolveQrUrl(payload) {
  if (!payload) return "";
  const s = String(payload);
  if (/^https?:\/\//i.test(s)) return s;
  if (s.startsWith("session_id=")) {
    return `${window.location.origin}/api/wxoa/login?${s}`;
  }
  return s;
}

const scopeText = computed(() => {
  if (!me.value) return "";
  return me.value.role === "detachment" ? "全市" : "本大队";
});

function formatTime(iso) {
  if (!iso) return "";
  return String(iso).replace("T", " ").slice(0, 16);
}

function orgName(id) {
  return orgs.value.find((o) => o.id === id)?.name || "—";
}

/** 取设计令牌里的颜色，供 canvas 绘制使用（与全局主题保持一致） */
function cssVar(name, fallback) {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

async function loadInitial() {
  try {
    const [meRes, distRes, orgRes, typeRes] = await Promise.all([
      http.get("/api/admin/me"),
      http.get("/api/admin/districts"),
      http.get("/api/admin/organizations"),
      http.get("/api/admin/org-types"),
    ]);
    me.value = meRes.data;
    districts.value = distRes.data;
    orgs.value = orgRes.data;
    orgTypes.value = typeRes.data || [];
  } catch (e) {
    console.error(e);
  }
  await loadTrainings();
}

async function onDistrictChange() {
  form.value.organizationId = undefined;
  if (!form.value.districtId) {
    orgsInDistrict.value = [];
    return;
  }
  try {
    const { data } = await http.get("/api/admin/organizations", {
      params: { district_id: Number(form.value.districtId) },
    });
    orgsInDistrict.value = data || [];
  } catch (e) {
    console.error(e);
    orgsInDistrict.value = [];
  }
}

async function loadTrainings() {
  trainingLoading.value = true;
  try {
    const { data } = await http.get("/api/admin/trainings");
    trainings.value = data || [];
  } catch (e) {
    console.error(e);
    trainings.value = [];
  } finally {
    trainingLoading.value = false;
  }
}

async function createTraining() {
  const f = form.value;
  if (!f.title.trim()) {
    ElMessage.warning("请输入培训标题");
    return;
  }
  if (!f.organizationId) {
    ElMessage.warning("请选择参训单位");
    return;
  }
  creating.value = true;
  try {
    const { data } = await http.post("/api/admin/trainings/quick", {
      title: f.title.trim(),
      organization_id: Number(f.organizationId),
      duration_minutes: Number(f.durationMinutes),
      location: f.location.trim() || undefined,
    });
    ElMessage.success("培训已创建");
    await loadTrainings();
    await showQrcode(data);
    form.value.title = "";
    form.value.location = "";
  } catch (e) {
    console.error(e);
    const msg = e?.response?.data?.detail || "创建失败";
    ElMessage.error(typeof msg === "string" ? msg : "创建失败");
  } finally {
    creating.value = false;
  }
}

async function openQrcode(sessionId) {
  try {
    const { data } = await http.get(`/api/admin/trainings/${sessionId}/qrcode-info`);
    await showQrcode(data);
  } catch (e) {
    console.error(e);
    ElMessage.error("二维码加载失败");
  }
}

async function showQrcode(info) {
  qrcodeData.value = info;
  qrcodeUrl.value = resolveQrUrl(info?.qr_payload);
  qrcodeOpen.value = true;
  await nextTick();
  if (qrCanvas.value && qrcodeUrl.value) {
    try {
      await QRCode.toCanvas(qrCanvas.value, qrcodeUrl.value, {
        margin: 1,
        scale: 6,
        color: { dark: cssVar("--surface-nav", "#0e2a47"), light: cssVar("--surface", "#ffffff") },
      });
    } catch (e) {
      console.error("qrcode render failed", e);
    }
  }
}

onMounted(loadInitial);
</script>

<style scoped>
.m-admin {
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

/* ---------- 表单 ---------- */
.m-note {
  margin: 0 0 12px;
  font-size: var(--fs-12);
  line-height: 1.6;
  color: var(--ink-500);
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
.m-field :deep(.el-input__wrapper),
.m-field :deep(.el-select__wrapper) {
  min-height: 44px;
}
.m-field :deep(.el-input-number) {
  width: 100%;
}
.m-field :deep(.el-input-number .el-input__wrapper) {
  min-height: 44px;
}
.m-hint {
  margin-top: 5px;
  font-size: var(--fs-11);
  color: var(--ink-400);
}
.m-w-full {
  width: 100%;
}
.m-submit {
  margin-top: 16px;
}
.m-submit svg {
  width: 15px;
  height: 15px;
}

/* ---------- 培训列表 ---------- */
.m-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.m-cardrow {
  display: block;
  width: 100%;
  padding: 12px;
  text-align: left;
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: var(--r-md);
  cursor: pointer;
  transition: border-color var(--t-fast), background var(--t-fast);
}
.m-cardrow:hover {
  border-color: var(--line-strong);
  background: var(--surface-2);
}
.m-cardrow:active {
  background: var(--surface-3);
}
.m-cardrow__top {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.m-cardrow__title {
  flex: 1;
  min-width: 0;
  font-size: var(--fs-14);
  font-weight: 600;
  line-height: 1.45;
  color: var(--ink-900);
  overflow-wrap: anywhere;
}
.m-cardrow__top .badge {
  flex: none;
}
.m-cardrow__sub {
  display: block;
  margin-top: 4px;
  font-size: var(--fs-12);
  color: var(--ink-500);
  overflow-wrap: anywhere;
}
.m-cardrow__foot {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  font-size: var(--fs-12);
  color: var(--ink-500);
}
.m-chip {
  padding: 2px 7px;
  font-size: var(--fs-11);
  color: var(--ink-600);
  background: var(--surface-3);
  border-radius: var(--r-sm);
  white-space: nowrap;
}
.m-cardrow__loc {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.m-cardrow__go {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: var(--fs-12);
  color: var(--brand-600);
  white-space: nowrap;
}
.m-cardrow__go svg {
  width: 13px;
  height: 13px;
}

/* ---------- 二维码弹层 ---------- */
.m-qr {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
.m-qr__frame {
  align-self: center;
  padding: 10px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
}
.m-qr__canvas {
  display: block;
  width: 220px;
  height: 220px;
  max-width: 100%;
}
.m-qr__meta {
  margin: 0;
  display: grid;
  gap: 6px;
  font-size: var(--fs-13);
}
.m-qr__meta > div {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.m-qr__meta dt {
  flex: none;
  width: 48px;
  font-size: var(--fs-12);
  color: var(--ink-500);
}
.m-qr__meta dd {
  flex: 1;
  min-width: 0;
  margin: 0;
  color: var(--ink-900);
  overflow-wrap: anywhere;
}
.m-qr__url {
  padding: 8px 10px;
  background: var(--surface-2);
  border: 1px solid var(--line-soft);
  border-radius: var(--r-sm);
  min-width: 0;
}
.m-qr__url-label {
  display: block;
  margin-bottom: 2px;
  font-size: var(--fs-11);
  color: var(--ink-500);
}
.m-qr__url-text {
  display: block;
  font-size: var(--fs-11);
  line-height: 1.5;
  color: var(--ink-600);
  word-break: break-all;
}
.m-qr__tip {
  margin: 0;
  font-size: var(--fs-11);
  line-height: 1.6;
  color: var(--ink-500);
}

:global(.m-qr-dialog) {
  border-radius: var(--r-lg);
}
:global(.m-qr-dialog .el-dialog__body) {
  padding: 16px;
}
</style>
