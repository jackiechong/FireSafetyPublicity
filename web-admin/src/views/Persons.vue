<template>
  <div>
    <div class="page-head">
      <div class="page-head__main">
        <div class="eyebrow">人员档案</div>
        <h1 class="page-title">注册人员</h1>
        <p class="page-desc">管理已通过微信登录并完成注册的人员，可调整手机号、所属单位与管理员身份</p>
      </div>
      <div class="page-actions">
        <button class="btn btn--ghost" :disabled="loading" @click="load(true)">
          <AppIcon name="refresh" :size="15" />{{ loading ? "刷新中…" : "刷新" }}
        </button>
      </div>
    </div>

    <div class="filterbar">
      <div class="field" style="flex: 1; min-width: 240px">
        <label for="f-person-kw">关键词</label>
        <div class="search-inline">
          <AppIcon name="search" :size="15" />
          <input
            id="f-person-kw"
            v-model="keyword"
            class="input"
            placeholder="姓名 / 手机号 / 单位"
            @keyup.enter="load(true)"
          />
        </div>
      </div>
      <div class="field" style="width: 170px">
        <label for="f-person-district">区县</label>
        <el-select
          id="f-person-district"
          v-model="filterDistrictId"
          clearable
          placeholder="全部区县"
          style="width: 100%"
          @change="onFilterDistrictChange"
        >
          <el-option v-for="d in districtFilterOptions" :key="d.id" :label="d.name" :value="d.id" />
        </el-select>
      </div>
      <div class="field" style="width: 220px">
        <label for="f-person-org">所属单位</label>
        <el-select
          id="f-person-org"
          v-model="filterOrganizationId"
          clearable
          filterable
          placeholder="全部单位"
          style="width: 100%"
          :disabled="!filterDistrictId"
          @change="load(true)"
        >
          <el-option v-for="o in filterOrgs" :key="o.id" :label="o.name" :value="o.id" />
        </el-select>
      </div>
      <div style="display: flex; gap: 8px; margin-left: auto">
        <button class="btn btn--primary" @click="load(true)">查询</button>
        <button class="btn btn--ghost" @click="resetFilters">重置</button>
      </div>
    </div>

    <div v-if="hasValue(keyword) || hasValue(filterDistrictId) || hasValue(filterOrganizationId)" class="chips">
      <span v-if="hasValue(keyword)" class="chip">
        <b>关键词</b>{{ keyword }}
        <button type="button" aria-label="移除关键词" @click="clearKeyword"><AppIcon name="x" :size="11" /></button>
      </span>
      <span v-if="hasValue(filterDistrictId)" class="chip">
        <b>区县</b>{{ districtName(filterDistrictId) }}
        <button type="button" aria-label="移除区县筛选" @click="clearDistrict"><AppIcon name="x" :size="11" /></button>
      </span>
      <span v-if="hasValue(filterOrganizationId)" class="chip">
        <b>单位</b>{{ organizationName(filterOrganizationId) }}
        <button type="button" aria-label="移除单位筛选" @click="clearOrganization"><AppIcon name="x" :size="11" /></button>
      </span>
      <button class="chips__reset" type="button" @click="resetFilters">清除全部</button>
    </div>

    <section class="card">
      <div class="card__head">
        <h3>人员清单</h3>
        <span class="sub">共 {{ total }} 人</span>
        <div class="grow"></div>
        <span class="badge badge--ok">实名注册</span>
      </div>

      <div v-loading="loading" class="tablewrap">
        <table class="tb">
          <thead>
            <tr>
              <th style="width: 110px">姓名</th>
              <th style="width: 130px">手机号</th>
              <th style="width: 120px">区县</th>
              <th>所属单位</th>
              <th style="width: 120px">职务岗位</th>
              <th style="width: 100px">微信绑定</th>
              <th style="width: 150px">管理员</th>
              <th style="width: 140px">注册时间</th>
              <th class="col-actions" style="width: 150px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.person_id">
              <td>
                <button class="cell-main linkbtn" style="padding: 0" @click="openPersonTrainings(row)">
                  {{ row.name || "—" }}
                </button>
              </td>
              <td class="num">{{ row.phone || "—" }}</td>
              <td>{{ row.district_name || "—" }}</td>
              <td>{{ row.organization_name || "—" }}</td>
              <td>{{ row.job_title || "—" }}</td>
              <td>
                <span class="badge" :class="row.wechat_bound ? 'badge--ok' : 'badge--off'">
                  {{ row.wechat_bound ? "已绑定" : "未绑定" }}
                </span>
              </td>
              <td>
                <span v-if="row.is_admin" class="badge" :class="row.admin_role === 'detachment' ? 'badge--live' : 'badge--ok'">
                  {{ row.admin_role === "detachment" ? "支队管理员" : "大队管理员" }}
                </span>
                <span v-else class="badge badge--off">普通人员</span>
                <span v-if="row.admin_brigade_name" class="cell-sub">{{ row.admin_brigade_name }}</span>
              </td>
              <td class="num">{{ formatTime(row.created_at) }}</td>
              <td class="col-actions">
                <div class="rowact" style="display: inline-flex; align-items: center; gap: 2px">
                  <button class="linkbtn" @click="openPersonTrainings(row)">查看</button>
                  <button class="linkbtn" :disabled="!canEdit" @click="openEdit(row)">编辑</button>
                  <el-dropdown trigger="click" @command="(cmd) => onRowCommand(cmd, row)">
                    <button class="iconbtn" aria-label="更多操作"><AppIcon name="more" :size="16" /></button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item
                          v-if="currentAdmin?.role === 'detachment'"
                          command="unbind"
                          :disabled="!row.wechat_bound"
                        >
                          解除微信绑定
                        </el-dropdown-item>
                        <el-dropdown-item command="delete" :disabled="!canEdit" divided class="is-danger">
                          删除人员
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </td>
            </tr>
            <tr v-if="!rows.length && !loading">
              <td colspan="9">
                <div class="empty">
                  <div class="empty__art"><AppIcon name="users" :size="26" /></div>
                  <h4>没有找到注册人员</h4>
                  <p>
                    {{
                      hasValue(keyword) || hasValue(filterDistrictId) || hasValue(filterOrganizationId)
                        ? "换个关键词、区县或单位试试，也可以清除筛选查看全部。"
                        : "还没有人员通过小程序完成注册，分享小程序入口后这里会自动出现。"
                    }}
                  </p>
                  <button
                    v-if="hasValue(keyword) || hasValue(filterDistrictId) || hasValue(filterOrganizationId)"
                    class="btn btn--ghost btn--sm"
                    @click="resetFilters"
                  >
                    清除筛选
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pager">
        <span>共 {{ total }} 人 · 每页 {{ pageSize }} 条</span>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="sizes, prev, pager, next, jumper"
          background
          @current-change="changePage"
          @size-change="changePageSize"
        />
      </div>
    </section>

    <!-- 查看培训记录 -->
    <el-drawer v-model="trainingVisible" size="640px" :with-header="false" destroy-on-close class="form-drawer">
      <div class="drawer-shell">
        <div class="drawer__head">
          <div class="grow">
            <h3>{{ trainingPersonName }}的培训记录</h3>
            <p>含该人员在各单位的参训明细，按时间倒序</p>
          </div>
          <button class="iconbtn" aria-label="关闭" @click="trainingVisible = false">
            <AppIcon name="x" :size="16" />
          </button>
        </div>
        <div class="drawer__body" style="padding: 0">
          <div v-loading="trainingLoading" class="tablewrap">
            <table class="tb">
              <thead>
                <tr>
                  <th>培训名称</th>
                  <th style="width: 130px">培训时间</th>
                  <th style="width: 150px">参训单位</th>
                  <th style="width: 90px">区县</th>
                  <th class="num" style="width: 80px">时长</th>
                  <th style="width: 110px">地点</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, idx) in trainingRows" :key="idx">
                  <td>{{ item.title }}</td>
                  <td class="num">{{ formatTime(item.start_at) }}</td>
                  <td>{{ item.organization_name || "—" }}</td>
                  <td>{{ item.district_name || "—" }}</td>
                  <td class="num">{{ item.duration_minutes }} 分</td>
                  <td>{{ item.location || "—" }}</td>
                </tr>
                <tr v-if="!trainingRows.length && !trainingLoading">
                  <td colspan="6">
                    <div class="empty">
                      <div class="empty__art"><AppIcon name="calendar" :size="26" /></div>
                      <h4>还没有培训记录</h4>
                      <p>该人员尚未参加过培训，登记并签到后这里会显示明细。</p>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="drawer__foot">
          <div class="grow"></div>
          <button class="btn btn--ghost" @click="trainingVisible = false">关闭</button>
        </div>
      </div>
    </el-drawer>

    <!-- 编辑人员 -->
    <el-drawer v-model="editVisible" size="520px" :with-header="false" destroy-on-close class="form-drawer">
      <div class="drawer-shell">
        <div class="drawer__head">
          <div class="grow">
            <h3>编辑人员信息</h3>
            <p>保存后立即生效，该人员的签到与培训记录保持关联</p>
          </div>
          <button class="iconbtn" aria-label="关闭" @click="editVisible = false">
            <AppIcon name="x" :size="16" />
          </button>
        </div>
        <div class="drawer__body">
          <el-form :model="form" label-position="top">
            <div class="fieldset">
              <div class="fieldset__title">身份信息</div>
              <div class="formgrid">
                <div class="field">
                  <label>姓名<span class="req">*</span></label>
                  <el-input v-model="form.name" maxlength="64" />
                </div>
                <div class="field">
                  <label>手机号<span class="req">*</span></label>
                  <el-input v-model="form.phone" maxlength="11" />
                </div>
              </div>
            </div>

            <div class="fieldset">
              <div class="fieldset__title">归属信息</div>
              <div class="formgrid">
                <div class="field">
                  <label>区县<span class="req">*</span></label>
                  <el-select v-model="form.district_id" style="width: 100%" @change="onEditDistrictChange">
                    <el-option v-for="d in districts" :key="d.id" :label="d.name" :value="d.id" />
                  </el-select>
                </div>
                <div class="field">
                  <label>所属单位<span class="req">*</span></label>
                  <el-select
                    v-model="form.organization_id"
                    filterable
                    style="width: 100%"
                    :disabled="!form.district_id"
                    placeholder="请先选择区县"
                  >
                    <el-option v-for="o in editOrgs" :key="o.id" :label="o.name" :value="o.id" />
                  </el-select>
                </div>
                <div class="field span-2">
                  <label>职务岗位</label>
                  <el-select v-model="form.job_title" clearable filterable placeholder="请选择职务岗位" style="width: 100%">
                    <el-option v-for="item in jobTitleSelectOptions" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>
              </div>
            </div>

            <div v-if="currentAdmin?.role === 'detachment'" class="fieldset">
              <div class="fieldset__title">权限设置</div>
              <div class="field">
                <label>管理员身份</label>
                <el-switch v-model="form.is_admin" active-text="设为管理员" inactive-text="普通人员" />
                <div class="hint">设为管理员后，默认按所属单位的大队赋予小程序管理权限。</div>
              </div>
            </div>
          </el-form>
        </div>
        <div class="drawer__foot">
          <span class="hint" style="margin: 0">带 * 为必填项</span>
          <div class="grow"></div>
          <button class="btn btn--ghost" @click="editVisible = false">取消</button>
          <button class="btn btn--primary" :disabled="saving" @click="submitEdit">
            {{ saving ? "保存中…" : "保存" }}
          </button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import http from "../api/http";
import AppIcon from "../components/AppIcon.vue";

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
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);

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

function hasValue(value) {
  return value !== undefined && value !== null && value !== "";
}

function districtName(id) {
  return districtFilterOptions.value.find((d) => d.id === Number(id))?.name || "—";
}

function organizationName(id) {
  return filterOrgs.value.find((o) => o.id === Number(id))?.name || "—";
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
  await load(true);
}

async function onEditDistrictChange() {
  form.organization_id = undefined;
  editOrgs.value = form.district_id ? await loadOrgs(form.district_id) : [];
}

async function load(resetPage = false) {
  if (resetPage) page.value = 1;
  loading.value = true;
  try {
    const params = {};
    if (keyword.value.trim()) params.q = keyword.value.trim();
    if (filterDistrictId.value && Number(filterDistrictId.value) > 0) params.district_id = Number(filterDistrictId.value);
    if (filterOrganizationId.value) params.organization_id = Number(filterOrganizationId.value);
    params.page = page.value;
    params.page_size = pageSize.value;
    const { data } = await http.get("/api/admin/persons/page", { params });
    rows.value = data.items || [];
    total.value = data.total || 0;
  } catch (e) {
    ElMessage.error(errorMessage(e, "人员列表加载失败"));
  } finally {
    loading.value = false;
  }
}

function clearKeyword() {
  keyword.value = "";
  load(true);
}

function clearDistrict() {
  filterDistrictId.value = undefined;
  filterOrganizationId.value = undefined;
  filterOrgs.value = [];
  load(true);
}

function clearOrganization() {
  filterOrganizationId.value = undefined;
  load(true);
}

function resetFilters() {
  keyword.value = "";
  filterDistrictId.value = undefined;
  filterOrganizationId.value = undefined;
  filterOrgs.value = [];
  load(true);
}

function changePageSize(size) {
  pageSize.value = size;
  load(true);
}

function changePage(nextPage) {
  page.value = nextPage;
  load();
}

function onRowCommand(cmd, row) {
  if (cmd === "unbind") unbindPerson(row);
  else if (cmd === "delete") removePerson(row);
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

async function removePerson(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${row.name || row.phone || "该人员"}」吗？删除后该人员的培训签到记录也会一并删除，此操作不可恢复。`,
      "删除人员",
      { type: "warning", confirmButtonText: "确认删除", cancelButtonText: "取消" }
    );
    await http.delete(`/api/admin/persons/${row.person_id}`);
    ElMessage.success("人员已删除");
    await load();
  } catch (e) {
    if (e !== "cancel") ElMessage.error(errorMessage(e, "删除失败"));
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
.drawer-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
}
:deep(.form-drawer .el-drawer__body) {
  padding: 0;
  overflow: hidden;
}
:deep(.filterbar .el-select__wrapper) {
  min-height: 36px;
}
.linkbtn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
