<template>
  <div class="m-admin">
    <section class="m-block">
      <div class="m-block-title">新建培训</div>
      <p class="m-tip">填写信息后生成二维码，受训人员用微信扫码即可签到。</p>

      <div class="m-field">
        <div class="m-label">培训标题</div>
        <el-input v-model="form.title" placeholder="如：电气火灾防范培训" maxlength="100" />
      </div>

      <div class="m-field">
        <div class="m-label">所在区县</div>
        <el-select v-model="form.districtId" placeholder="选择区县" filterable class="m-w-full" @change="onDistrictChange">
          <el-option v-for="d in districts" :key="d.id" :label="d.name" :value="d.id" />
        </el-select>
      </div>

      <div class="m-field">
        <div class="m-label">参训单位</div>
        <el-select v-model="form.organizationId" placeholder="选择单位" filterable class="m-w-full" :disabled="!form.districtId">
          <el-option
            v-for="o in orgsInDistrict"
            :key="o.id"
            :label="`${o.name}（${orgTypeName(o.org_type)}）`"
            :value="o.id"
          />
        </el-select>
      </div>

      <div class="m-row">
        <div class="m-field m-flex1">
          <div class="m-label">时长</div>
          <el-input-number v-model="form.durationMinutes" :min="15" :max="480" :step="15" class="m-w-full" />
          <div class="m-hint">分钟（建议 30–180）</div>
        </div>
        <div class="m-field m-flex1">
          <div class="m-label">地点（选填）</div>
          <el-input v-model="form.location" placeholder="如：单位会议室" />
        </div>
      </div>

      <el-button type="primary" :loading="creating" class="m-submit" @click="createTraining">
        创建并生成二维码
      </el-button>
    </section>

    <section class="m-block">
      <div class="m-block-title">
        我管理的培训
        <span class="m-block-meta">{{ scopeText }}</span>
      </div>
      <el-empty v-if="!trainingLoading && !trainings.length" description="暂无培训" />
      <div v-else class="m-list">
        <div
          v-for="t in trainings"
          :key="t.id"
          class="m-row-card"
          @click="openQrcode(t.id)"
        >
          <div class="m-row-title">{{ t.title }}</div>
          <div class="m-row-sub">
            {{ orgName(t.organization_id) }} · {{ formatTime(t.start_at) }}
          </div>
          <div class="m-row-meta">
            <span>{{ formatTrainingMinutes(t.duration_minutes) }}</span>
            <span class="dot">·</span>
            <span>{{ t.location || "未填地点" }}</span>
            <span class="m-row-action">查看二维码 ›</span>
          </div>
        </div>
      </div>
    </section>

    <el-dialog
      v-model="qrcodeOpen"
      :title="qrcodeData ? qrcodeData.title : '培训二维码'"
      width="92%"
      align-center
      destroy-on-close
    >
      <div v-if="qrcodeData" class="m-qr-body">
        <canvas ref="qrCanvas" class="m-qr-canvas" />
        <div class="m-qr-info">
          <div><b>单位：</b>{{ qrcodeData.organization_name }}</div>
          <div><b>大队：</b>{{ qrcodeData.brigade_name }}</div>
          <div><b>开始：</b>{{ formatTime(qrcodeData.start_at) }}</div>
          <div><b>时长：</b>{{ formatTrainingMinutes(qrcodeData.duration_minutes) }}</div>
          <div v-if="qrcodeData.location"><b>地点：</b>{{ qrcodeData.location }}</div>
          <div><b>已签到：</b>{{ qrcodeData.attendance_count }} 人</div>
          <div class="m-qr-payload">本场扫码地址：{{ qrcodeUrl }}</div>
        <div v-if="universalLoginDisplay" class="m-qr-portal">
          <div><b>通用入口（登录后自选场次）：</b></div>
          <div class="m-qr-payload">{{ universalLoginDisplay }}</div>
        </div>
        </div>
        <p class="m-qr-tip">
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
const orgTypeLabels = {
  emergency: "应急",
  education: "教育",
  civil_affairs: "民政",
  culture_tourism: "文旅",
  health: "卫建",
  commerce: "商务",
  industry_agriculture: "农业农村",
  development_reform: "发改",
  other_department: "其他部门",
  department: "其他部门",
  enterprise: "其他部门",
};

function orgTypeName(value) {
  return orgTypeLabels[value] || "其他部门";
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

async function loadInitial() {
  try {
    const [meRes, distRes, orgRes] = await Promise.all([
      http.get("/api/admin/me"),
      http.get("/api/admin/districts"),
      http.get("/api/admin/organizations"),
    ]);
    me.value = meRes.data;
    districts.value = distRes.data;
    orgs.value = orgRes.data;
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
        color: { dark: "#1a237e", light: "#ffffff" },
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
  gap: 14px;
}
.m-block {
  background: #fff;
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.m-block-title {
  font-weight: 600;
  color: #333;
  font-size: 15px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.m-block-meta {
  font-size: 12px;
  color: #888;
  font-weight: normal;
}
.m-tip {
  margin: 0 0 12px;
  color: #888;
  font-size: 12px;
}
.m-field {
  margin-bottom: 12px;
}
.m-label {
  font-size: 13px;
  color: #555;
  margin-bottom: 4px;
}
.m-hint {
  margin-top: 4px;
  font-size: 11px;
  color: #999;
}
.m-row {
  display: flex;
  gap: 12px;
}
.m-flex1 {
  flex: 1;
  min-width: 0;
}
.m-w-full {
  width: 100%;
}
.m-submit {
  width: 100%;
}
.m-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.m-row-card {
  border: 1px solid #eef0f5;
  border-radius: 10px;
  padding: 12px;
  background: #fafbff;
}
.m-row-title {
  font-weight: 600;
  color: #1a237e;
  font-size: 14px;
}
.m-row-sub {
  margin-top: 4px;
  color: #555;
  font-size: 12px;
}
.m-row-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
  margin-top: 6px;
  color: #888;
  font-size: 12px;
}
.dot {
  margin: 0 4px;
}
.m-row-action {
  margin-left: auto;
  color: #3949ab;
}

.m-qr-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.m-qr-canvas {
  width: 240px;
  height: 240px;
}
.m-qr-info {
  width: 100%;
  font-size: 13px;
  color: #333;
  line-height: 1.8;
}
.m-qr-payload {
  color: #888;
  font-size: 12px;
  word-break: break-all;
}
.m-qr-portal {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #e0e4f0;
}
.m-qr-tip {
  margin: 4px 0 0;
  color: #888;
  font-size: 12px;
  text-align: center;
}
</style>
