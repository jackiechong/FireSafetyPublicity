<template>
  <div class="page">
    <div class="head">
      <div>
        <h2>人员管理</h2>
        <p class="tip">管理已通过微信登录并完成注册的人员，可调整手机号、所属单位和管理员身份。</p>
      </div>
      <el-button type="primary" :loading="loading" @click="load">刷新</el-button>
    </div>

    <div class="filters">
      <el-input
        v-model="keyword"
        clearable
        placeholder="搜索姓名、手机号、单位"
        class="search"
        @keyup.enter="load"
        @clear="load"
      />
      <el-select v-model="filterDistrictId" clearable placeholder="区县" class="filter" @change="onFilterDistrictChange">
        <el-option v-for="d in districtFilterOptions" :key="d.id" :label="d.name" :value="d.id" />
      </el-select>
      <el-select
        v-model="filterOrganizationId"
        clearable
        filterable
        placeholder="单位"
        class="filter-org"
        :disabled="!filterDistrictId"
        @change="load"
      >
        <el-option v-for="o in filterOrgs" :key="o.id" :label="o.name" :value="o.id" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
    </div>

    <el-table :data="rows" border stripe v-loading="loading" style="width: 100%">
      <el-table-column label="姓名" width="120">
        <template #default="{ row }">
          <el-button link type="primary" @click="openPersonTrainings(row)">{{ row.name || "—" }}</el-button>
        </template>
      </el-table-column>
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column prop="district_name" label="区县" width="130" />
      <el-table-column prop="organization_name" label="所属单位" min-width="220" />
      <el-table-column prop="job_title" label="身份/岗位" min-width="130">
        <template #default="{ row }">{{ row.job_title || "—" }}</template>
      </el-table-column>
      <el-table-column label="管理员" width="160">
        <template #default="{ row }">
          <el-tag v-if="row.is_admin" type="success">
            {{ row.admin_role === "detachment" ? "支队管理员" : "大队管理员" }}
          </el-tag>
          <el-tag v-else type="info">普通人员</el-tag>
          <div v-if="row.admin_brigade_name" class="sub">{{ row.admin_brigade_name }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="150">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="170" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="!canEdit" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" :disabled="currentAdmin?.role !== 'detachment'" @click="unbindPerson(row)">解除绑定</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="editVisible" title="编辑人员信息" width="560px" destroy-on-close>
      <el-form :model="form" label-width="96px">
        <el-form-item label="姓名" required>
          <el-input v-model="form.name" maxlength="64" />
        </el-form-item>
        <el-form-item label="手机号" required>
          <el-input v-model="form.phone" maxlength="11" />
        </el-form-item>
        <el-form-item label="区县" required>
          <el-select v-model="form.district_id" style="width: 100%" @change="onEditDistrictChange">
            <el-option v-for="d in districts" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属单位" required>
          <el-select v-model="form.organization_id" filterable style="width: 100%" :disabled="!form.district_id">
            <el-option v-for="o in editOrgs" :key="o.id" :label="o.name" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="身份/岗位">
          <el-select v-model="form.job_title" clearable filterable placeholder="请选择身份/岗位" style="width: 100%">
            <el-option v-for="item in jobTitleSelectOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="currentAdmin?.role === 'detachment'" label="管理员">
          <el-switch
            v-model="form.is_admin"
            active-text="设为管理员"
            inactive-text="普通人员"
          />
          <div class="form-tip">设为管理员后，默认按所属单位的大队赋予小程序管理权限。</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="trainingVisible" :title="`${trainingPersonName}的培训记录`" width="760px" destroy-on-close>
      <el-table :data="trainingRows" border stripe v-loading="trainingLoading" size="small">
        <el-table-column prop="title" label="培训名称" min-width="180" />
        <el-table-column label="培训时间" width="160">
          <template #default="{ row }">{{ formatTime(row.start_at) }}</template>
        </el-table-column>
        <el-table-column prop="organization_name" label="参训单位" min-width="180" />
        <el-table-column prop="district_name" label="区县" width="120" />
        <el-table-column prop="duration_minutes" label="时长(分)" width="100" />
        <el-table-column prop="location" label="地点" min-width="120" />
      </el-table>
      <template #footer>
        <el-button @click="trainingVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import http from "../api/http";

const rows = ref([]);
const districts = ref([]);
const filterOrgs = ref([]);
const editOrgs = ref([]);
const jobTitleOptions = ref([]);
const keyword = ref("");
const filterDistrictId = ref();
const filterOrganizationId = ref();
const loading = ref(false);
const saving = ref(false);
const currentAdmin = ref(null);
const editVisible = ref(false);
const editingId = ref(null);
const trainingVisible = ref(false);
const trainingLoading = ref(false);
const trainingRows = ref([]);
const trainingPersonName = ref("");

const form = reactive({
  name: "",
  phone: "",
  district_id: undefined,
  organization_id: undefined,
  job_title: "",
  is_admin: false,
});

const canEdit = computed(() => !!currentAdmin.value);
const districtFilterOptions = computed(() => [{ id: 0, name: "葫芦岛支队" }, ...districts.value]);
const jobTitleSelectOptions = computed(() => {
  const current = form.job_title ? [form.job_title] : [];
  return [...new Set([...jobTitleOptions.value, ...current].filter(Boolean))];
});

function formatTime(iso) {
  if (!iso) return "—";
  return String(iso).replace("T", " ").slice(0, 16);
}

function errorMessage(e, fallback) {
  return e?.response?.data?.detail || fallback;
}

async function loadOrgs(districtId) {
  if (!districtId || Number(districtId) === 0) return [];
  const { data } = await http.get("/api/admin/organizations", {
    params: { district_id: Number(districtId) },
  });
  return data || [];
}

async function onFilterDistrictChange() {
  filterOrganizationId.value = undefined;
  filterOrgs.value = filterDistrictId.value ? await loadOrgs(filterDistrictId.value) : [];
  await load();
}

async function onEditDistrictChange() {
  form.organization_id = undefined;
  editOrgs.value = form.district_id ? await loadOrgs(form.district_id) : [];
}

async function load() {
  loading.value = true;
  try {
    const params = {};
    if (keyword.value.trim()) params.q = keyword.value.trim();
    if (filterDistrictId.value && Number(filterDistrictId.value) > 0) params.district_id = Number(filterDistrictId.value);
    if (filterOrganizationId.value) params.organization_id = Number(filterOrganizationId.value);
    const { data } = await http.get("/api/admin/persons", { params });
    rows.value = data || [];
  } catch (e) {
    ElMessage.error(errorMessage(e, "人员列表加载失败"));
  } finally {
    loading.value = false;
  }
}

async function openEdit(row) {
  editingId.value = row.person_id;
  Object.assign(form, {
    name: row.name || "",
    phone: row.phone || "",
    district_id: row.district_id,
    organization_id: row.organization_id,
    job_title: row.job_title || "",
    is_admin: !!row.is_admin,
  });
  editOrgs.value = row.district_id ? await loadOrgs(row.district_id) : [];
  editVisible.value = true;
}

async function submitEdit() {
  const cleanPhone = String(form.phone || "").trim();
  if (!form.name.trim()) {
    ElMessage.warning("请填写姓名");
    return;
  }
  if (!/^1\d{10}$/.test(cleanPhone)) {
    ElMessage.warning("输入号码有误，请重新输入");
    return;
  }
  if (!form.district_id || !form.organization_id) {
    ElMessage.warning("请选择区县和所属单位");
    return;
  }
  saving.value = true;
  try {
    await http.patch(`/api/admin/persons/${editingId.value}`, {
      name: form.name.trim(),
      phone: cleanPhone,
      district_id: Number(form.district_id),
      organization_id: Number(form.organization_id),
      job_title: form.job_title.trim() || null,
      is_admin: !!form.is_admin,
    });
    ElMessage.success("人员信息已保存");
    editVisible.value = false;
    await load();
  } catch (e) {
    ElMessage.error(errorMessage(e, "保存失败"));
  } finally {
    saving.value = false;
  }
}

async function openPersonTrainings(row) {
  trainingPersonName.value = row.name || "人员";
  trainingRows.value = [];
  trainingVisible.value = true;
  trainingLoading.value = true;
  try {
    const { data } = await http.get(`/api/admin/persons/${row.person_id}/trainings`);
    trainingRows.value = data || [];
  } finally {
    trainingLoading.value = false;
  }
}

async function unbindPerson(row) {
  try {
    await ElMessageBox.confirm(
      `确定解除「${row.name || row.phone || "该人员"}」的微信身份绑定吗？解除后该微信下次进入小程序需要重新填写身份信息。`,
      "解除身份绑定",
      { type: "warning" }
    );
    await http.patch(`/api/admin/persons/${row.person_id}/unbind`);
    ElMessage.success("已解除身份绑定");
    await load();
  } catch (e) {
    if (e !== "cancel") ElMessage.error(errorMessage(e, "解除失败"));
  }
}

onMounted(async () => {
  const [me, dist, jobs] = await Promise.all([
    http.get("/api/admin/me"),
    http.get("/api/admin/districts"),
    http.get("/api/admin/job-titles"),
  ]);
  currentAdmin.value = me.data;
  districts.value = dist.data || [];
  jobTitleOptions.value = (jobs.data || []).map((x) => x.name).filter(Boolean);
  await load();
});
</script>

<style scoped>
.page {
  background: #fff;
  padding: 20px 24px;
  border-radius: 8px;
  min-height: 400px;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}
h2 {
  margin: 0 0 8px;
  font-size: 1.25rem;
}
.tip {
  color: #888;
  font-size: 13px;
  margin: 0 0 16px;
}
.filters {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}
.search {
  width: 260px;
}
.filter {
  width: 150px;
}
.filter-org {
  width: 260px;
}
.sub {
  margin-top: 4px;
  font-size: 12px;
  color: #888;
}
.form-tip {
  margin-top: 6px;
  color: #888;
  font-size: 12px;
  line-height: 1.5;
}
</style>
