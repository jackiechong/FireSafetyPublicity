<template>
  <div>
    <div class="page-head">
      <div class="page-head__main">
        <div class="eyebrow">基础档案</div>
        <h1 class="page-title">单位台账</h1>
        <p class="page-desc">维护全市消防培训责任单位，按区县与大队归类；支持模板批量导入与逐条修正</p>
      </div>
      <div class="page-actions">
        <button class="btn btn--ghost" @click="downloadTemplate">
          <AppIcon name="download" :size="15" />下载模板
        </button>
        <el-upload :show-file-list="false" accept=".xlsx" :http-request="uploadOrganizations">
          <button class="btn btn--ghost"><AppIcon name="upload" :size="15" />批量导入</button>
        </el-upload>
        <button class="btn btn--primary" @click="openDialog()">
          <AppIcon name="plus" :size="15" />新增单位
        </button>
      </div>
    </div>

    <div class="filterbar">
      <div class="field" style="flex: 1; min-width: 240px">
        <label for="f-org-kw">关键词</label>
        <div class="search-inline">
          <AppIcon name="search" :size="15" />
          <input
            id="f-org-kw"
            v-model="keyword"
            class="input"
            placeholder="单位名称"
            @keyup.enter="load(true)"
          />
        </div>
      </div>
      <div class="field" style="width: 200px">
        <label for="f-org-district">区县</label>
        <el-select
          id="f-org-district"
          v-model="filterDistrict"
          clearable
          placeholder="全部区县"
          style="width: 100%"
          @change="load(true)"
        >
          <el-option v-for="d in districts" :key="d.id" :label="d.name" :value="d.id" />
        </el-select>
      </div>
      <div style="display: flex; gap: 8px; margin-left: auto">
        <button class="btn btn--primary" @click="load(true)">查询</button>
        <button class="btn btn--ghost" @click="resetFilters">重置</button>
      </div>
    </div>

    <div v-if="keyword || filterDistrict" class="chips">
      <span v-if="keyword" class="chip">
        <b>关键词</b>{{ keyword }}
        <button type="button" aria-label="移除关键词" @click="removeKeyword"><AppIcon name="x" :size="11" /></button>
      </span>
      <span v-if="filterDistrict" class="chip">
        <b>区县</b>{{ districtName(filterDistrict) }}
        <button type="button" aria-label="移除区县筛选" @click="removeDistrict"><AppIcon name="x" :size="11" /></button>
      </span>
      <button class="chips__reset" type="button" @click="resetFilters">清除全部</button>
    </div>

    <section class="card">
      <div class="card__head">
        <h3>单位清单</h3>
        <span class="sub">共 {{ total }} 家</span>
        <div class="grow"></div>
        <span class="badge badge--ok">台账已登记</span>
      </div>

      <div v-loading="loading" class="tablewrap">
        <table class="tb">
          <thead>
            <tr>
              <th class="num" style="width: 64px">ID</th>
              <th>单位名称</th>
              <th style="width: 120px">单位类型</th>
              <th style="width: 110px">区县</th>
              <th style="width: 120px">所属大队</th>
              <th style="width: 110px">联系人</th>
              <th style="width: 130px">联系电话</th>
              <th class="col-actions" style="width: 150px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td class="num" style="color: var(--ink-400)">{{ row.id }}</td>
              <td>
                <button class="cell-main linkbtn" style="padding: 0" @click="openDetail(row)">{{ row.name }}</button>
              </td>
              <td>{{ orgTypeName(row.org_type) }}</td>
              <td>{{ districtName(row.district_id) }}</td>
              <td>{{ brigadeName(row.brigade_id) }}</td>
              <td>{{ row.contact_name || "—" }}</td>
              <td class="num">{{ row.contact_phone || "—" }}</td>
              <td class="col-actions">
                <div class="rowact" style="display: inline-flex; align-items: center; gap: 2px">
                  <button class="linkbtn" @click="openDetail(row)">查看</button>
                  <button class="linkbtn" @click="openDialog(row)">编辑</button>
                  <el-dropdown
                    v-if="currentAdmin?.role === 'detachment'"
                    trigger="click"
                    @command="(cmd) => onRowCommand(cmd, row)"
                  >
                    <button class="iconbtn" aria-label="更多操作"><AppIcon name="more" :size="16" /></button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="delete" class="is-danger">删除单位</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </td>
            </tr>
            <tr v-if="!rows.length && !loading">
              <td colspan="8">
                <div class="empty">
                  <div class="empty__art"><AppIcon name="building" :size="26" /></div>
                  <h4>没有找到单位</h4>
                  <p>{{ keyword || filterDistrict ? "换个关键词或区县试试，也可以清除筛选查看全部。" : "台账里还没有单位，先新增第一家，或用模板批量导入。" }}</p>
                  <button v-if="keyword || filterDistrict" class="btn btn--ghost btn--sm" @click="resetFilters">清除筛选</button>
                  <button v-else class="btn btn--primary btn--sm" @click="openDialog()">新增单位</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pager">
        <span>共 {{ total }} 家 · 每页 {{ pageSize }} 条</span>
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

    <!-- 查看单位 -->
    <el-drawer v-model="detailVisible" size="520px" :with-header="false" destroy-on-close class="form-drawer">
      <div class="drawer-shell">
        <div class="drawer__head">
          <div class="grow">
            <h3>{{ detail?.name || "单位详情" }}</h3>
            <p>单位 #{{ detail?.id }} · {{ orgTypeName(detail?.org_type) }}</p>
          </div>
          <button class="iconbtn" aria-label="关闭" @click="detailVisible = false">
            <AppIcon name="x" :size="16" />
          </button>
        </div>
        <div class="drawer__body">
          <div class="fieldset">
            <div class="fieldset__title">归属信息</div>
            <div class="formgrid">
              <div class="field">
                <label>所属大队</label>
                <b>{{ brigadeName(detail?.brigade_id) }}</b>
              </div>
              <div class="field">
                <label>区县</label>
                <b>{{ districtName(detail?.district_id) }}</b>
              </div>
            </div>
          </div>
          <div class="fieldset">
            <div class="fieldset__title">联系信息</div>
            <div class="formgrid">
              <div class="field">
                <label>联系人</label>
                <b>{{ detail?.contact_name || "—" }}</b>
              </div>
              <div class="field">
                <label>联系电话</label>
                <b class="num">{{ detail?.contact_phone || "—" }}</b>
              </div>
              <div class="field span-2">
                <label>备注</label>
                <b>{{ detail?.remark || "—" }}</b>
              </div>
            </div>
          </div>
        </div>
        <div class="drawer__foot">
          <div class="grow"></div>
          <button class="btn btn--ghost" @click="detailVisible = false">关闭</button>
          <button class="btn btn--primary" @click="editFromDetail">编辑</button>
        </div>
      </div>
    </el-drawer>

    <!-- 新增 / 编辑单位 -->
    <el-drawer v-model="dialogVisible" size="520px" :with-header="false" destroy-on-close class="form-drawer">
      <div class="drawer-shell">
        <div class="drawer__head">
          <div class="grow">
            <h3>{{ editing?.id ? "编辑单位" : "新增单位" }}</h3>
            <p>{{ editing?.id ? "修改后立即生效，已有培训与人员归属不受影响" : "登记后即可在培训与人员中选择该单位" }}</p>
          </div>
          <button class="iconbtn" aria-label="关闭" @click="dialogVisible = false">
            <AppIcon name="x" :size="16" />
          </button>
        </div>
        <div class="drawer__body">
          <el-form :model="form" label-position="top">
            <div class="fieldset">
              <div class="fieldset__title">基本信息</div>
              <div class="formgrid">
                <div class="field span-2">
                  <label>单位名称<span class="req">*</span></label>
                  <el-input v-model="form.name" placeholder="填写单位全称，如：连山区某商业综合体" />
                </div>
                <div class="field">
                  <label>单位类型<span class="req">*</span></label>
                  <el-select v-model="form.org_type" style="width: 100%">
                    <el-option v-for="t in orgTypes" :key="t.code" :label="t.name" :value="t.code" />
                  </el-select>
                </div>
                <div class="field">
                  <label>所属大队<span class="req">*</span></label>
                  <el-select v-model="form.brigade_id" style="width: 100%">
                    <el-option v-for="b in brigades" :key="b.id" :label="b.name" :value="b.id" />
                  </el-select>
                </div>
                <div class="field span-2">
                  <label>区县<span class="req">*</span></label>
                  <el-select v-model="form.district_id" style="width: 100%">
                    <el-option v-for="d in districts" :key="d.id" :label="d.name" :value="d.id" />
                  </el-select>
                </div>
              </div>
            </div>

            <div class="fieldset">
              <div class="fieldset__title">联系信息</div>
              <div class="formgrid">
                <div class="field">
                  <label>联系人</label>
                  <el-input v-model="form.contact_name" placeholder="选填" />
                </div>
                <div class="field">
                  <label>联系电话</label>
                  <el-input v-model="form.contact_phone" placeholder="选填" />
                </div>
                <div class="field span-2">
                  <label>备注</label>
                  <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="选填：单位地址、行业特征等" />
                </div>
              </div>
            </div>
          </el-form>
        </div>
        <div class="drawer__foot">
          <span class="hint" style="margin: 0">带 * 为必填项</span>
          <div class="grow"></div>
          <button class="btn btn--ghost" @click="dialogVisible = false">取消</button>
          <button class="btn btn--primary" :disabled="saving" @click="save">
            {{ saving ? "保存中…" : "保存" }}
          </button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import http from "../api/http";
import AppIcon from "../components/AppIcon.vue";

const loading = ref(false);
const saving = ref(false);
const rows = ref([]);
const brigades = ref([]);
const districts = ref([]);
const keyword = ref("");
const filterDistrict = ref();
const dialogVisible = ref(false);
const editing = ref(null);
const orgTypes = ref([]);
const currentAdmin = ref(null);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);

const detailVisible = ref(false);
const detail = ref(null);

const form = reactive({
  name: "",
  org_type: "other_department",
  brigade_id: null,
  district_id: null,
  contact_name: "",
  contact_phone: "",
  remark: "",
});

function brigadeName(id) {
  return brigades.value.find((b) => b.id === id)?.name || id;
}
function districtName(id) {
  return districts.value.find((d) => d.id === id)?.name || id;
}
function orgTypeName(value) {
  return orgTypes.value.find((t) => t.code === value)?.name || value || "其他部门";
}

async function loadMeta() {
  const [me, b, d, t] = await Promise.all([
    http.get("/api/admin/me"),
    http.get("/api/admin/brigades"),
    http.get("/api/admin/districts"),
    http.get("/api/admin/org-types"),
  ]);
  currentAdmin.value = me.data;
  brigades.value = b.data;
  districts.value = d.data;
  orgTypes.value = t.data || [];
}

function saveBlob(data, name) {
  const url = URL.createObjectURL(new Blob([data]));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

async function downloadTemplate() {
  const { data } = await http.get("/api/admin/imports/organization-template.xlsx", { responseType: "blob" });
  saveBlob(data, "organization-import-template.xlsx");
}

async function uploadOrganizations({ file }) {
  const data = new FormData();
  data.append("file", file);
  const res = await http.post("/api/admin/imports/organizations", data);
  if (res.data.ok) {
    ElMessage.success(`导入完成，新增 ${res.data.imported} 个，更新 ${res.data.updated} 个`);
    await load();
  } else {
    ElMessage.error((res.data.errors || []).slice(0, 5).join("；") || "导入失败");
  }
}

async function load(resetPage = false) {
  if (resetPage) page.value = 1;
  loading.value = true;
  try {
    const { data } = await http.get("/api/admin/organizations/page", {
      params: {
        q: keyword.value || undefined,
        district_id: filterDistrict.value || undefined,
        page: page.value,
        page_size: pageSize.value,
      },
    });
    rows.value = data.items || [];
    total.value = data.total || 0;
  } finally {
    loading.value = false;
  }
}

function resetFilters() {
  keyword.value = "";
  filterDistrict.value = undefined;
  load(true);
}

function removeKeyword() {
  keyword.value = "";
  load(true);
}

function removeDistrict() {
  filterDistrict.value = undefined;
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

function openDetail(row) {
  detail.value = row;
  detailVisible.value = true;
}

function editFromDetail() {
  openDialog(detail.value);
  detailVisible.value = false;
}

function onRowCommand(cmd, row) {
  if (cmd === "delete") remove(row);
}

function openDialog(row) {
  editing.value = row || null;
  if (row) {
    Object.assign(form, {
      name: row.name,
      org_type: row.org_type,
      brigade_id: row.brigade_id,
      district_id: row.district_id,
      contact_name: row.contact_name || "",
      contact_phone: row.contact_phone || "",
      remark: row.remark || "",
    });
  } else {
    Object.assign(form, {
      name: "",
      org_type: orgTypes.value[0]?.code || "other_department",
      brigade_id: brigades.value[0]?.id ?? null,
      district_id: districts.value[0]?.id ?? null,
      contact_name: "",
      contact_phone: "",
      remark: "",
    });
  }
  dialogVisible.value = true;
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning("请填写名称");
    return;
  }
  saving.value = true;
  try {
    if (editing.value?.id) {
      await http.patch(`/api/admin/organizations/${editing.value.id}`, form);
      ElMessage.success("已保存");
    } else {
      await http.post("/api/admin/organizations", form);
      ElMessage.success("已创建");
    }
    dialogVisible.value = false;
    await load();
  } catch (e) {
    console.error(e);
  } finally {
    saving.value = false;
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`确定删除「${row.name}」？`, "确认", { type: "warning" });
  await http.delete(`/api/admin/organizations/${row.id}`);
  ElMessage.success("已删除");
  await load();
}

onMounted(async () => {
  await loadMeta();
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
</style>
