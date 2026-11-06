<template>
  <div>
    <div class="page-head">
      <div class="page-head__main">
        <div class="eyebrow">培训业务</div>
        <h1 class="page-title">培训记录</h1>
        <p class="page-desc">登记、跟进与归档全市培训会议；进行中的场次可实时查看签到进度</p>
      </div>
      <div class="page-actions">
        <button class="btn btn--primary" @click="openCreate">
          <AppIcon name="plus" :size="15" />登记培训
        </button>
      </div>
    </div>

    <div class="filterbar">
      <div class="field" style="flex: 1; min-width: 240px">
        <label for="f-kw">关键词</label>
        <div class="search-inline">
          <AppIcon name="search" :size="15" />
          <input
            id="f-kw"
            v-model="searchQ"
            class="input"
            placeholder="培训主题 / 地点"
            @keyup.enter="load(true)"
          />
        </div>
      </div>
      <div style="display: flex; gap: 8px; margin-left: auto">
        <button class="btn btn--primary" @click="load(true)">查询</button>
        <button class="btn btn--ghost" @click="resetFilters">重置</button>
      </div>
    </div>

    <div v-if="searchQ" class="chips">
      <span class="chip">
        <b>关键词</b>{{ searchQ }}
        <button type="button" aria-label="移除关键词" @click="resetFilters"><AppIcon name="x" :size="11" /></button>
      </span>
      <button class="chips__reset" type="button" @click="resetFilters">清除全部</button>
    </div>

    <section class="card">
      <div class="card__head">
        <h3>培训清单</h3>
        <span class="sub">共 {{ total }} 条</span>
        <div class="grow"></div>
        <span class="badge badge--live">进行中 {{ activeCount }}</span>
      </div>

      <div v-loading="loading" class="tablewrap">
        <table class="tb">
          <thead>
            <tr>
              <th style="width: 64px">ID</th>
              <th>培训主题</th>
              <th style="width: 170px">主题分类</th>
              <th style="width: 96px">状态</th>
              <th style="width: 130px">主办单位</th>
              <th style="width: 150px">开始时间</th>
              <th class="num" style="width: 76px">时长</th>
              <th class="col-actions" style="width: 96px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td class="num" style="color: var(--ink-400)">{{ row.id }}</td>
              <td>
                <button class="cell-main linkbtn" style="padding: 0" @click="openAttendanceList(row)">
                  {{ row.title }}
                </button>
                <span v-if="row.location" class="cell-sub"><AppIcon name="pin" :size="12" />{{ row.location }}</span>
              </td>
              <td>{{ topicName(row.topic_id) }}</td>
              <td>
                <span class="badge" :class="row.is_active !== false ? 'badge--live' : 'badge--done'">
                  {{ row.is_active !== false ? "进行中" : "已结束" }}
                </span>
              </td>
              <td>{{ brigadeName(row.brigade_id) }}</td>
              <td class="num">{{ formatTime(row.start_at) }}</td>
              <td class="num">{{ row.duration_minutes }} 分</td>
              <td class="col-actions">
                <div class="rowact" style="display: inline-flex; align-items: center; gap: 2px">
                  <button class="linkbtn" @click="openAttendanceList(row)">查看</button>
                  <el-dropdown trigger="click" @command="(cmd) => onRowCommand(cmd, row)">
                    <button class="iconbtn" aria-label="更多操作"><AppIcon name="more" :size="16" /></button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="edit">编辑培训</el-dropdown-item>
                        <el-dropdown-item command="attendance">添加参训人员</el-dropdown-item>
                        <el-dropdown-item command="export">导出签到簿</el-dropdown-item>
                        <el-dropdown-item v-if="row.is_active !== false" command="end" divided>结束培训</el-dropdown-item>
                        <el-dropdown-item command="delete" divided class="is-danger">删除</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </td>
            </tr>
            <tr v-if="!rows.length && !loading">
              <td colspan="8">
                <div class="empty">
                  <div class="empty__art"><AppIcon name="calendar" :size="26" /></div>
                  <h4>没有找到培训记录</h4>
                  <p>{{ searchQ ? "换个关键词试试，或清除筛选条件。" : "还没有登记过培训，先登记第一场吧。" }}</p>
                  <button v-if="searchQ" class="btn btn--ghost btn--sm" @click="resetFilters">清除筛选</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pager">
        <span>共 {{ total }} 条 · 每页 {{ pageSize }} 条</span>
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

    <!-- 登记 / 编辑：右侧抽屉 -->
    <el-drawer v-model="createVisible" size="520px" :with-header="false" destroy-on-close class="form-drawer">
      <div class="drawer-shell">
        <div class="drawer__head">
          <div class="grow">
            <h3>登记培训</h3>
            <p>保存后自动生成签到二维码，可现场投屏或导出签到簿</p>
          </div>
          <button class="iconbtn" aria-label="关闭" @click="createVisible = false">
            <AppIcon name="x" :size="16" />
          </button>
        </div>
        <div class="drawer__body">
          <el-form :model="createForm" label-position="top">
            <div class="fieldset">
              <div class="fieldset__title">基本信息</div>
              <div class="formgrid">
                <div class="field span-2">
                  <label>培训主题<span class="req">*</span></label>
                  <el-input v-model="createForm.title" placeholder="如：建昌县消防救援大队开展消防宣传月活动" />
                </div>
                <div class="field">
                  <label>主题分类</label>
                  <el-select v-model="createForm.topic_id" clearable placeholder="未分类" style="width: 100%">
                    <el-option v-for="t in activeTopics" :key="t.id" :label="t.name" :value="t.id" />
                  </el-select>
                </div>
                <div class="field">
                  <label>主办单位<span class="req">*</span></label>
                  <el-select v-model="createForm.brigade_id" placeholder="请选择" style="width: 100%">
                    <el-option v-for="b in brigades" :key="b.id" :label="b.name" :value="b.id" />
                  </el-select>
                </div>
              </div>
            </div>

            <div class="fieldset">
              <div class="fieldset__title">时间与地点</div>
              <div class="formgrid">
                <div class="field">
                  <label>开始时间<span class="req">*</span></label>
                  <el-date-picker
                    v-model="createForm.start_at"
                    type="datetime"
                    value-format="YYYY-MM-DDTHH:mm:ss"
                    style="width: 100%"
                  />
                </div>
                <div class="field">
                  <label>时长（分钟）</label>
                  <el-input-number v-model="createForm.duration_minutes" :min="0" :step="30" style="width: 100%" />
                  <div class="hint">默认 60 分钟，按 30 分钟增减</div>
                </div>
                <div class="field span-2">
                  <label>培训地点</label>
                  <el-input v-model="createForm.location" placeholder="填写详细地址，便于参训人员导航到场" />
                </div>
                <div class="field span-2">
                  <label>备注</label>
                  <el-input v-model="createForm.remark" type="textarea" :rows="2" placeholder="选填：主讲人、课件、注意事项…" />
                </div>
              </div>
            </div>
          </el-form>
        </div>
        <div class="drawer__foot">
          <span class="hint" style="margin: 0">保存后状态为「进行中」，可随时结束或补录</span>
          <div class="grow"></div>
          <button class="btn btn--ghost" @click="createVisible = false">取消</button>
          <button class="btn btn--primary" :disabled="saving" @click="submitCreate">
            {{ saving ? "保存中…" : "保存并生成签到码" }}
          </button>
        </div>
      </div>
    </el-drawer>

    <el-drawer v-model="editVisible" size="520px" :with-header="false" destroy-on-close class="form-drawer">
      <div class="drawer-shell">
        <div class="drawer__head">
          <div class="grow">
            <h3>编辑培训</h3>
            <p>修改后立即生效，已生成的签到记录不受影响</p>
          </div>
          <button class="iconbtn" aria-label="关闭" @click="editVisible = false">
            <AppIcon name="x" :size="16" />
          </button>
        </div>
        <div class="drawer__body">
          <el-form label-position="top">
            <div class="fieldset">
              <div class="fieldset__title">基本信息</div>
              <div class="formgrid">
                <div class="field span-2">
                  <label>培训名称<span class="req">*</span></label>
                  <el-input v-model="editForm.title" />
                </div>
                <div class="field">
                  <label>主题分类</label>
                  <el-select v-model="editForm.topic_id" clearable placeholder="未分类" style="width: 100%">
                    <el-option v-for="t in editTopicOptions" :key="t.id" :label="t.name" :value="t.id" />
                  </el-select>
                </div>
                <div class="field">
                  <label>主办单位<span class="req">*</span></label>
                  <el-select v-model="editForm.brigade_id" style="width: 100%">
                    <el-option v-for="b in brigades" :key="b.id" :label="b.name" :value="b.id" />
                  </el-select>
                </div>
              </div>
            </div>
            <div class="fieldset">
              <div class="fieldset__title">时间与地点</div>
              <div class="formgrid">
                <div class="field">
                  <label>开始时间<span class="req">*</span></label>
                  <el-date-picker
                    v-model="editForm.start_at"
                    type="datetime"
                    value-format="YYYY-MM-DDTHH:mm:ss"
                    style="width: 100%"
                  />
                </div>
                <div class="field">
                  <label>时长（分钟）</label>
                  <el-input-number v-model="editForm.duration_minutes" :min="0" :step="30" style="width: 100%" />
                </div>
                <div class="field span-2">
                  <label>培训地点</label>
                  <el-input v-model="editForm.location" />
                </div>
                <div class="field span-2">
                  <label>备注</label>
                  <el-input v-model="editForm.remark" type="textarea" :rows="2" />
                </div>
              </div>
            </div>
          </el-form>
        </div>
        <div class="drawer__foot">
          <div class="grow"></div>
          <button class="btn btn--ghost" @click="editVisible = false">取消</button>
          <button class="btn btn--primary" :disabled="editSaving" @click="submitEdit">
            {{ editSaving ? "保存中…" : "保存修改" }}
          </button>
        </div>
      </div>
    </el-drawer>

    <!-- 添加参训人员 -->
    <el-dialog v-model="attVisible" title="添加参训人员" width="480px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="培训">
          <span>{{ currentSession?.title }}（#{{ currentSession?.id }}）</span>
        </el-form-item>
        <el-form-item label="手机号" required>
          <el-input v-model="attPhone" maxlength="11" placeholder="与小程序绑定一致" />
        </el-form-item>
        <template v-if="currentAdmin?.role === 'detachment'">
          <el-form-item label="姓名">
            <el-input v-model="attName" maxlength="64" placeholder="未注册人员必填" />
          </el-form-item>
          <el-form-item label="职务">
            <el-input v-model="attJobTitle" maxlength="64" placeholder="如：值班员" />
          </el-form-item>
          <el-form-item label="人员类别">
            <el-input v-model="attPersonCategory" maxlength="64" placeholder="如：消控室人员" />
          </el-form-item>
        </template>
        <el-form-item label="本次时长（分钟）">
          <el-input-number v-model="attDuration" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <button class="btn btn--ghost" @click="attVisible = false">取消</button>
        <button class="btn btn--primary" :disabled="attSaving" @click="submitAttendance">
          {{ attSaving ? "提交中…" : "确定添加" }}
        </button>
      </template>
    </el-dialog>

    <!-- 参训人员明细 -->
    <el-dialog v-model="attListVisible" :title="`${attListSession?.title || '培训'} · 参训人员`" width="820px" destroy-on-close>
      <div v-loading="attListLoading">
        <table class="tb">
          <thead>
            <tr>
              <th style="width: 64px">序号</th>
              <th>单位</th>
              <th style="width: 110px">姓名</th>
              <th style="width: 140px">职务</th>
              <th style="width: 130px">电话</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in attListRows" :key="row.index">
              <td class="num">{{ row.index }}</td>
              <td>{{ row.organization_name }}</td>
              <td>{{ row.name }}</td>
              <td>{{ row.job_title || "—" }}</td>
              <td class="num">{{ row.phone }}</td>
            </tr>
            <tr v-if="!attListRows.length">
              <td colspan="5">
                <div class="empty">
                  <div class="empty__art"><AppIcon name="users" :size="26" /></div>
                  <h4>还没有人签到</h4>
                  <p>把签到码投屏给参训人员，扫码后这里会实时更新。</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <template #footer>
        <button class="btn btn--ghost" @click="attListVisible = false">关闭</button>
        <button class="btn btn--primary" @click="exportAttendance(attListSession)">导出签到簿</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import http from "../api/http";
import AppIcon from "../components/AppIcon.vue";

const loading = ref(false);
const saving = ref(false);
const rows = ref([]);
const searchQ = ref("");
const brigades = ref([]);
const topics = ref([]);
const currentAdmin = ref(null);
const createVisible = ref(false);
const createForm = reactive({
  title: "",
  topic_id: null,
  brigade_id: null,
  start_at: "",
  duration_minutes: 60,
  location: "",
  remark: "",
  is_active: true,
});

const attVisible = ref(false);
const attSaving = ref(false);
const currentSession = ref(null);
const attPhone = ref("");
const attName = ref("");
const attJobTitle = ref("");
const attPersonCategory = ref("");
const attDuration = ref(0);
const editVisible = ref(false);
const editSaving = ref(false);
const editing = ref(null);
const editForm = reactive({
  title: "",
  topic_id: null,
  brigade_id: null,
  start_at: "",
  duration_minutes: 60,
  location: "",
  remark: "",
});
const attListVisible = ref(false);
const attListLoading = ref(false);
const attListRows = ref([]);
const attListSession = ref(null);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);

const activeTopics = computed(() => topics.value.filter((t) => t.is_active !== false));
const editTopicOptions = computed(
  () => topics.value.filter((t) => t.is_active !== false || t.id === editing.value?.topic_id)
);
const activeCount = computed(() => rows.value.filter((r) => r.is_active !== false).length);

function brigadeName(id) {
  return brigades.value.find((b) => b.id === id)?.name || id;
}

function topicName(id) {
  return topics.value.find((t) => t.id === id)?.name || "未分类";
}

function formatTime(iso) {
  if (!iso) return "";
  return iso.replace("T", " ").slice(0, 16);
}

async function load(resetPage = false) {
  if (resetPage) page.value = 1;
  loading.value = true;
  try {
    const params = {};
    if (searchQ.value.trim()) params.q = searchQ.value.trim();
    params.page = page.value;
    params.page_size = pageSize.value;
    const { data } = await http.get("/api/admin/trainings/page", { params });
    rows.value = data.items || [];
    total.value = data.total || 0;
  } finally {
    loading.value = false;
  }
}

function resetFilters() {
  searchQ.value = "";
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

function localNowIso() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function openCreate() {
  Object.assign(createForm, {
    title: "",
    topic_id: null,
    brigade_id: brigades.value[0]?.id ?? null,
    start_at: localNowIso(),
    duration_minutes: 60,
    location: "",
    remark: "",
    is_active: true,
  });
  createVisible.value = true;
}

async function submitCreate() {
  if (!createForm.title.trim() || !createForm.brigade_id) {
    ElMessage.warning("请填写主题并选择培训主办单位");
    return;
  }
  saving.value = true;
  try {
    await http.post("/api/admin/trainings", createForm);
    ElMessage.success("培训已登记，签到码已生成");
    createVisible.value = false;
    await load();
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || "登记失败");
  } finally {
    saving.value = false;
  }
}

function openEdit(row) {
  editing.value = row;
  Object.assign(editForm, {
    title: row.title || "",
    topic_id: row.topic_id || null,
    brigade_id: row.brigade_id || null,
    start_at: row.start_at ? row.start_at.slice(0, 19) : "",
    duration_minutes: row.duration_minutes || 0,
    location: row.location || "",
    remark: row.remark || "",
  });
  editVisible.value = true;
}

async function submitEdit() {
  if (!editing.value || !editForm.title.trim() || !editForm.brigade_id || !editForm.start_at) {
    ElMessage.warning("请填写培训名称、培训主办单位和开始时间");
    return;
  }
  editSaving.value = true;
  try {
    await http.patch(`/api/admin/trainings/${editing.value.id}`, {
      title: editForm.title.trim(),
      topic_id: editForm.topic_id || null,
      brigade_id: Number(editForm.brigade_id),
      start_at: editForm.start_at,
      duration_minutes: Number(editForm.duration_minutes || 0),
      location: editForm.location || null,
      remark: editForm.remark || null,
    });
    ElMessage.success("已保存");
    editVisible.value = false;
    await load();
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || "保存失败");
  } finally {
    editSaving.value = false;
  }
}

function onRowCommand(cmd, row) {
  if (cmd === "edit") openEdit(row);
  else if (cmd === "attendance") openAttendance(row);
  else if (cmd === "export") exportAttendance(row);
  else if (cmd === "end") endTraining(row);
  else if (cmd === "delete") deleteTraining(row);
}

function openAttendance(row) {
  currentSession.value = row;
  attPhone.value = "";
  attName.value = "";
  attJobTitle.value = "";
  attPersonCategory.value = "";
  attDuration.value = row.duration_minutes || 0;
  attVisible.value = true;
}

async function submitAttendance() {
  if (!attPhone.value || attPhone.value.length !== 11) {
    ElMessage.warning("请输入11位手机号");
    return;
  }
  attSaving.value = true;
  try {
    await http.post(`/api/admin/trainings/${currentSession.value.id}/attendance`, {
      phone: attPhone.value,
      name: attName.value.trim() || undefined,
      organization_id: currentSession.value.organization_id,
      job_title: attJobTitle.value.trim() || undefined,
      person_category: attPersonCategory.value.trim() || undefined,
      duration_minutes: attDuration.value,
    });
    ElMessage.success("已添加");
    attVisible.value = false;
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || "添加失败");
  } finally {
    attSaving.value = false;
  }
}

function saveBlob(data, name) {
  const url = URL.createObjectURL(new Blob([data]));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

async function openAttendanceList(row) {
  attListSession.value = row;
  attListVisible.value = true;
  attListLoading.value = true;
  try {
    const { data } = await http.get(`/api/admin/trainings/${row.id}/attendances`);
    attListRows.value = data || [];
  } finally {
    attListLoading.value = false;
  }
}

async function exportAttendance(row) {
  if (!row?.id) return;
  const { data } = await http.get(`/api/admin/exports/training-attendance/${row.id}.xlsx`, { responseType: "blob" });
  saveBlob(data, `${row.title || "培训"}-签到簿.xlsx`);
}

async function endTraining(row) {
  await ElMessageBox.confirm(`确定提前结束“${row.title}”吗？`, "提前结束", { type: "warning" });
  await http.post(`/api/admin/trainings/${row.id}/end`);
  ElMessage.success("已结束");
  await load();
}

async function deleteTraining(row) {
  await ElMessageBox.confirm(`确定删除“${row.title}”吗？删除后参训记录也会一并删除。`, "删除培训", {
    type: "warning",
    confirmButtonText: "删除",
    confirmButtonClass: "el-button--danger",
  });
  await http.delete(`/api/admin/trainings/${row.id}`);
  ElMessage.success("已删除");
  await load();
}

onMounted(async () => {
  const [me, b, t] = await Promise.all([
    http.get("/api/admin/me"),
    http.get("/api/admin/brigades"),
    http.get("/api/admin/training-topics", { params: { include_inactive: true } }),
  ]);
  currentAdmin.value = me.data;
  brigades.value = b.data;
  topics.value = t.data || [];
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
</style>
