<template>
  <div class="h5-card" v-if="ready">
    <h3 class="h5-title">首次使用 · 完善实名信息</h3>
    <p class="h5-tip">姓名、单位等仅用于消防培训实名考核统计，不会对外公开。</p>

    <div class="h5-field">
      <label>所在区县</label>
      <select v-model="districtId" @change="onDistrictChange">
        <option :value="0">请选择区县</option>
        <option v-for="d in districts" :key="d.id" :value="d.id">{{ d.name }}</option>
      </select>
    </div>

    <div class="h5-field">
      <label>所在单位</label>
      <select v-model="orgChoice" :disabled="!districtId">
        <option value="">请选择单位</option>
        <option v-for="o in orgs" :key="o.id" :value="String(o.id)">
          {{ o.name }}（{{ orgTypeName(o.org_type) }}）
        </option>
        <option value="__OTHER__">其他单位（手动添加）</option>
      </select>
    </div>

    <div v-if="orgChoice === '__OTHER__'" class="h5-sub">
      <div class="h5-field">
        <label>新单位名称</label>
        <input v-model.trim="customOrgName" placeholder="如：XX 公司" maxlength="64" />
      </div>
      <div class="h5-field">
        <label>类型</label>
        <select v-model="customOrgType">
          <option v-for="t in orgTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
        </select>
      </div>
    </div>

    <div class="h5-field">
      <label>姓名</label>
      <input v-model.trim="name" maxlength="32" placeholder="请输入真实姓名" />
    </div>

    <div class="h5-field">
      <label>手机号</label>
      <input v-model.trim="phone" type="tel" maxlength="11" placeholder="11 位手机号" />
    </div>

    <div class="h5-field">
      <label>职务 / 岗位（选填）</label>
      <input v-model.trim="jobTitle" maxlength="40" placeholder="如：安全员" />
    </div>

    <button class="h5-btn-primary" :disabled="loading" @click="submit">
      {{ loading ? "提交中…" : "保存并继续" }}
    </button>
    <p v-if="errorMsg" class="h5-err">{{ errorMsg }}</p>
  </div>
  <div v-else class="h5-loading">加载中…</div>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import mpHttp from "../../api/mpHttp";
import { ensureH5Login } from "../../utils/h5Auth";

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
const orgTypes = [
  { value: "emergency", label: "应急" },
  { value: "education", label: "教育" },
  { value: "civil_affairs", label: "民政" },
  { value: "culture_tourism", label: "文旅" },
  { value: "health", label: "卫建" },
  { value: "commerce", label: "商务" },
  { value: "industry_agriculture", label: "工农业农村" },
  { value: "development_reform", label: "发改" },
  { value: "other_department", label: "其他部门" },
];

function orgTypeName(value) {
  return orgTypes.find((t) => t.value === value)?.label || "其他部门";
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
  await loadDistricts();
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
      job_title: jobTitle.value || undefined,
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
.h5-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.h5-title {
  margin: 0 0 6px;
  font-size: 16px;
  color: #1a237e;
}
.h5-tip {
  margin: 0 0 16px;
  font-size: 12px;
  color: #888;
  line-height: 1.5;
}
.h5-field {
  margin-bottom: 14px;
}
.h5-field label {
  display: block;
  font-size: 13px;
  color: #555;
  margin-bottom: 6px;
}
.h5-field input,
.h5-field select {
  width: 100%;
  height: 40px;
  font-size: 15px;
  padding: 0 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: #fafbff;
  box-sizing: border-box;
}
.h5-sub {
  background: #f5f7ff;
  border-radius: 8px;
  padding: 10px;
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
}
.h5-btn-primary[disabled] {
  opacity: 0.65;
}
.h5-err {
  margin-top: 10px;
  color: #d32f2f;
  font-size: 13px;
  text-align: center;
}
.h5-loading {
  text-align: center;
  color: #888;
  padding: 40px 0;
}
</style>
