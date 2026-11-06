<template>
  <div v-if="ready" class="bind">
    <section class="card bind-head">
      <div class="bind-mark"><AppIcon name="shield" :size="24" /></div>
      <h1 class="bind-title">首次使用 · 完善实名信息</h1>
      <p class="bind-desc">姓名、单位等仅用于消防培训实名考核统计，不会对外公开。</p>
    </section>

    <section class="card bind-form">
      <div class="field">
        <label for="b-district">所在区县<span class="req">*</span></label>
        <div class="select">
          <select id="b-district" v-model="districtId" @change="onDistrictChange">
            <option :value="0">请选择区县</option>
            <option v-for="d in districts" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
        </div>
      </div>

      <div class="field">
        <label for="b-org">所在单位<span class="req">*</span></label>
        <div class="select">
          <select id="b-org" v-model="orgChoice" :disabled="!districtId">
            <option value="">请选择单位</option>
            <option v-for="o in orgs" :key="o.id" :value="String(o.id)">
              {{ o.name }}（{{ orgTypeName(o.org_type) }}）
            </option>
            <option value="__OTHER__">其他单位（手动添加）</option>
          </select>
        </div>
        <div v-if="!districtId" class="hint">先选择区县，再选择单位</div>
      </div>

      <div v-if="orgChoice === '__OTHER__'" class="bind-sub">
        <div class="field">
          <label for="b-neworg">新单位名称<span class="req">*</span></label>
          <input id="b-neworg" v-model.trim="customOrgName" class="input" placeholder="如：XX 公司" maxlength="64" />
        </div>
        <div class="field" style="margin-bottom: 0">
          <label for="b-newtype">单位类型</label>
          <div class="select">
            <select id="b-newtype" v-model="customOrgType">
              <option v-for="t in orgTypes" :key="t.code" :value="t.code">{{ t.name }}</option>
            </select>
          </div>
        </div>
      </div>

      <div class="field">
        <label for="b-name">姓名<span class="req">*</span></label>
        <input id="b-name" v-model.trim="name" class="input" maxlength="32" placeholder="请输入真实姓名" />
      </div>

      <div class="field">
        <label for="b-phone">手机号<span class="req">*</span></label>
        <input
          id="b-phone"
          v-model.trim="phone"
          class="input"
          type="tel"
          inputmode="numeric"
          maxlength="11"
          placeholder="11 位手机号"
        />
      </div>

      <div class="field" style="margin-bottom: 0">
        <label for="b-job">职务 / 岗位<span class="req">*</span></label>
        <div class="select">
          <select id="b-job" v-model="jobTitle">
            <option value="">请选择职务 / 岗位</option>
            <option v-for="t in jobTitles" :key="t.id" :value="t.name">{{ t.name }}</option>
          </select>
        </div>
      </div>

      <p v-if="errorMsg" class="bind-error">{{ errorMsg }}</p>
    </section>

    <div class="bind-fixed">
      <button class="btn btn--primary btn--block" :disabled="loading" @click="submit">
        {{ loading ? "提交中…" : "保存并继续" }}
      </button>
      <p class="bind-note">提交后信息将用于本次及后续培训的实名签到</p>
    </div>
  </div>

  <div v-else class="card bind-loading">
    <span class="bind-spinner" aria-hidden="true"></span>
    <p>加载中…</p>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import mpHttp from "../../api/mpHttp";
import { ensureH5Login } from "../../utils/h5Auth";
import AppIcon from "../../components/AppIcon.vue";

const ready = ref(false);
const loading = ref(false);
const errorMsg = ref("");

const me = ref(null);
const districts = ref([]);
const orgs = ref([]);

const districtId = ref(0);
const orgChoice = ref(""); // 单位 id 字符串 or "__OTHER__"
const customOrgName = ref("");
const customOrgType = ref("other_department");
const orgTypes = ref([]);
const jobTitles = ref([]);

function orgTypeName(value) {
  return orgTypes.value.find((t) => t.code === value)?.name || value || "其他部门";
}

const name = ref("");
const phone = ref("");
const jobTitle = ref("");

function getSessionIdFromUrl() {
  try {
    return Number(new URL(window.location.href).searchParams.get("session_id")) || 0;
  } catch {
    return 0;
  }
}

async function loadDistricts() {
  const { data } = await mpHttp.get("/api/mp/districts");
  districts.value = data || [];
}

async function loadDictionaries() {
  const [typesRes, jobsRes] = await Promise.all([
    mpHttp.get("/api/mp/org-types"),
    mpHttp.get("/api/mp/job-titles"),
  ]);
  orgTypes.value = typesRes.data || [];
  jobTitles.value = jobsRes.data || [];
  customOrgType.value = orgTypes.value[0]?.code || "other_department";
}

async function loadOrgs() {
  if (!districtId.value) {
    orgs.value = [];
    return;
  }
  const { data } = await mpHttp.get("/api/mp/organizations", {
    params: { district_id: districtId.value },
  });
  orgs.value = data || [];
}

function onDistrictChange() {
  orgChoice.value = "";
  customOrgName.value = "";
  loadOrgs();
}

watch(districtId, () => {
  /* nothing extra; onChange already handled */
});

async function init() {
  const profile = await ensureH5Login(getSessionIdFromUrl());
  if (!profile) return; // 已跳走
  me.value = profile;
  await Promise.all([loadDistricts(), loadDictionaries()]);
  if (profile.district_id) {
    districtId.value = profile.district_id;
    await loadOrgs();
    if (profile.organization_id) orgChoice.value = String(profile.organization_id);
  }
  if (profile.name) name.value = profile.name;
  if (profile.phone) phone.value = profile.phone;
  if (profile.job_title) jobTitle.value = profile.job_title;
  ready.value = true;
}

async function submit() {
  errorMsg.value = "";
  if (!districtId.value) {
    errorMsg.value = "请选择区县";
    return;
  }
  if (!orgChoice.value) {
    errorMsg.value = "请选择单位";
    return;
  }
  if (!name.value || phone.value.length !== 11) {
    errorMsg.value = "请填写姓名与 11 位手机号";
    return;
  }
  if (orgChoice.value === "__OTHER__" && !customOrgName.value) {
    errorMsg.value = "请输入新单位名称";
    return;
  }
  if (!jobTitle.value) {
    errorMsg.value = "请选择职务 / 岗位";
    return;
  }
  loading.value = true;
  try {
    let organization_id = Number(orgChoice.value);
    if (orgChoice.value === "__OTHER__") {
      const { data: created } = await mpHttp.post("/api/mp/organizations", {
        district_id: districtId.value,
        name: customOrgName.value,
        org_type: customOrgType.value,
      });
      organization_id = created.id;
    }
    await mpHttp.post("/api/mp/profile", {
      name: name.value,
      phone: phone.value,
      district_id: districtId.value,
      organization_id,
      job_title: jobTitle.value,
    });
    const sid = getSessionIdFromUrl();
    if (sid) {
      window.location.replace(`/h5/checkin?session_id=${sid}`);
    } else {
      window.location.replace("/h5/me");
    }
  } catch (e) {
    errorMsg.value = e?.response?.data?.detail || "保存失败，请稍后再试";
  } finally {
    loading.value = false;
  }
}

onMounted(init);
</script>

<style scoped>
.bind-head {
  padding: 20px 18px 18px;
  margin-bottom: 12px;
}
.bind-mark {
  width: 44px;
  height: 44px;
  margin-bottom: 12px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--brand-50);
  border: 1px solid #cfe0ee;
  color: var(--brand-700);
}
.bind-title {
  font-size: var(--fs-16);
  font-weight: 600;
  color: var(--ink-900);
}
.bind-desc {
  margin-top: 6px;
  font-size: var(--fs-12);
  line-height: 1.65;
  color: var(--ink-500);
}

.bind-form {
  padding: 16px;
}
.bind-form .field {
  margin-bottom: 14px;
}
.bind-form .input,
.bind-form .select select {
  height: 44px;
  font-size: var(--fs-14);
}
.bind-sub {
  margin-bottom: 14px;
  padding: 12px;
  background: var(--surface-2);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
}
.bind-error {
  margin-top: 4px;
  font-size: var(--fs-12);
  color: var(--fire-500);
}

.bind-fixed {
  position: sticky;
  bottom: 0;
  margin-top: 14px;
  padding: 12px 0 calc(12px + env(safe-area-inset-bottom, 0px));
  background: linear-gradient(180deg, rgba(238, 242, 246, 0) 0%, var(--bg) 34%);
}
.bind-fixed .btn {
  height: 46px;
  font-size: var(--fs-14);
}
.bind-note {
  margin-top: 8px;
  font-size: var(--fs-11);
  color: var(--ink-400);
  text-align: center;
}

.bind-loading {
  display: grid;
  place-items: center;
  gap: 12px;
  padding: 48px 20px;
  color: var(--ink-500);
  font-size: var(--fs-13);
}
.bind-spinner {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 2px solid var(--line);
  border-top-color: var(--brand-600);
  animation: bind-spin 720ms linear infinite;
}
@keyframes bind-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
