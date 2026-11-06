<template>
  <div>
    <div class="page-head">
      <div class="page-head__main">
        <div class="eyebrow">数据查询</div>
        <h1 class="page-title">综合查询</h1>
        <p class="page-desc">按统计区间、培训主题、人员类别、开展大队与单位组合查询培训明细，并导出统计报表</p>
      </div>
      <div class="page-actions">
        <button class="btn btn--ghost" @click="downloadTemplate">
          <AppIcon name="download" :size="15" />下载模板
        </button>
        <el-upload :show-file-list="false" accept=".xlsx" :http-request="uploadPersons">
          <button class="btn btn--ghost"><AppIcon name="upload" :size="15" />导入人员</button>
        </el-upload>
        <button class="btn btn--ghost" @click="openScanTrainingImport">
          <AppIcon name="qr" :size="15" />导入扫码培训
        </button>
        <button class="btn btn--primary" @click="exportSummary">
          <AppIcon name="doc" :size="15" />导出统计
        </button>
      </div>
    </div>

    <div class="filterbar">
      <div class="field">
        <label for="f-range">统计区间</label>
        <el-date-picker
          id="f-range"
          v-model="range"
          type="datetimerange"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          value-format="YYYY-MM-DDTHH:mm:ss"
          style="width: 340px"
        />
      </div>
      <div class="field">
        <label for="f-topic">培训主题</label>
        <el-select id="f-topic" v-model="topicId" clearable placeholder="全部主题" style="width: 160px">
          <el-option v-for="t in topics" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
      </div>
      <div class="field">
        <label for="f-job">人员类别</label>
        <el-select id="f-job" v-model="jobTitle" clearable filterable placeholder="全部类别" style="width: 160px">
          <el-option v-for="j in jobTitles" :key="j.id" :label="j.name" :value="j.name" />
        </el-select>
      </div>
      <div class="field">
        <label for="f-brigade">开展大队</label>
        <el-select id="f-brigade" v-model="brigadeId" clearable placeholder="全部大队" style="width: 160px">
          <el-option v-for="brigade in brigades" :key="brigade.id" :label="brigade.name" :value="brigade.id" />
        </el-select>
      </div>
      <div class="field">
        <label for="f-org">单位</label>
        <el-select
          id="f-org"
          v-model="orgId"
          filterable
          remote
          clearable
          reserve-keyword
          placeholder="输入单位名称"
          :remote-method="remoteOrg"
          :loading="orgLoading"
          style="width: 220px"
          @change="onOrgPicked"
        >
          <el-option v-for="o in orgOptions" :key="o.id" :label="`${o.name}（${o.district_name}）`" :value="o.id" />
        </el-select>
      </div>
      <div style="display: flex; gap: 8px; margin-left: auto">
        <button class="btn btn--primary" @click="loadAll(true)">查询</button>
        <button class="btn btn--ghost" @click="resetFilters">重置</button>
      </div>
    </div>

    <div v-if="filterChips.length" class="chips">
      <span v-for="chip in filterChips" :key="chip.key" class="chip">
        <b>{{ chip.label }}</b>{{ chip.value }}
        <button type="button" :aria-label="`移除${chip.label}条件`" @click="clearChip(chip.key)">
          <AppIcon name="x" :size="11" />
        </button>
      </span>
      <button class="chips__reset" type="button" @click="resetFilters">清除全部</button>
    </div>

    <section class="card">
      <div class="card__head">
        <h3>培训清单</h3>
        <span class="sub">共 {{ summaryTotal }} 场</span>
        <div class="grow"></div>
        <span v-if="filterChips.length" class="badge badge--live">已选 {{ filterChips.length }} 项条件</span>
        <span v-else class="badge badge--done">全部数据</span>
      </div>

      <div v-loading="loading" class="tablewrap">
        <table class="tb">
          <thead>
            <tr>
              <th>培训名称</th>
              <th style="width: 150px">开展日期</th>
              <th class="num" style="width: 96px">培训人数</th>
              <th style="width: 140px">培训主题</th>
              <th style="width: 120px">开展大队</th>
              <th style="width: 200px">单位</th>
              <th v-if="canEditTraining" class="col-actions" style="width: 88px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in summary" :key="row.session_id">
              <td>
                <button class="cell-main linkbtn" style="padding: 0" @click="exportAttendance(row)">
                  {{ row.title }}
                </button>
              </td>
              <td class="num">{{ fmt(row.start_at) }}</td>
              <td class="num">{{ row.person_count }}</td>
              <td>{{ row.topic_name || "未分类" }}</td>
              <td>{{ row.brigade_name || "—" }}</td>
              <td>{{ row.organization_name || "—" }}</td>
              <td v-if="canEditTraining" class="col-actions">
                <button class="linkbtn" @click="openTrainingEdit(row)">编辑</button>
              </td>
            </tr>
            <tr v-if="!summary.length && !loading">
              <td :colspan="canEditTraining ? 7 : 6">
                <div class="empty">
                  <div class="empty__art"><AppIcon name="search" :size="26" /></div>
                  <h4>没有符合条件的培训</h4>
                  <p>{{ filterChips.length ? "换个条件组合试试，或清除筛选后重新查询。" : "当前统计区间内还没有培训记录。" }}</p>
                  <button v-if="filterChips.length" class="btn btn--ghost btn--sm" @click="resetFilters">清除筛选</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pager">
        <span>共 {{ summaryTotal }} 场 · 每页 {{ summaryPageSize }} 场</span>
        <el-pagination
          v-model:current-page="summaryPage"
          v-model:page-size="summaryPageSize"
          :total="summaryTotal"
          :page-sizes="[20, 50, 100]"
          layout="sizes, prev, pager, next, jumper"
          background
          @current-change="changeSummaryPage"
          @size-change="changeSummaryPageSize"
        />
      </div>
    </section>

    <div class="grid grid--2" style="margin-top: 20px">
      <section class="card">
        <div class="card__head">
          <h3>按人员类别</h3>
          <span class="sub">{{ jobTitle || "未选择类别" }}</span>
          <div class="grow"></div>
          <span class="badge badge--done">区县分布</span>
        </div>

        <template v-if="jobStats">
          <div class="card__body" style="padding-bottom: 4px">
            <div class="statline">
              <b class="num">{{ jobStats.total_person_count }}</b>
              <span>人 · 该类别累计培训人数</span>
            </div>
          </div>
          <div class="tablewrap">
            <table class="tb">
              <thead>
                <tr>
                  <th>区县</th>
                  <th class="num" style="width: 120px">培训人数</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in jobStats.district_counts" :key="item.district_name">
                  <td>{{ item.district_name }}</td>
                  <td class="num">{{ item.person_count }}</td>
                </tr>
                <tr v-if="!jobStats.district_counts?.length">
                  <td colspan="2">
                    <div class="empty" style="padding: 32px 20px">
                      <h4>暂无区县分布</h4>
                      <p>该人员类别在当前条件下还没有签到记录。</p>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <div v-else class="empty">
          <div class="empty__art"><AppIcon name="users" :size="26" /></div>
          <h4>先选择人员类别</h4>
          <p>在上方筛选栏选择人员类别后，这里会按区县汇总培训人数。</p>
        </div>
      </section>

      <section class="card">
        <div class="card__head">
          <h3>按培训主题</h3>
          <span class="sub">{{ topicStats.length }} 个主题</span>
          <div class="grow"></div>
          <span class="badge badge--done">培训人数</span>
        </div>
        <div class="tablewrap">
          <table class="tb">
            <thead>
              <tr>
                <th>主题</th>
                <th class="num" style="width: 96px">培训人数</th>
                <th style="width: 240px">开展大队</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in topicStats" :key="row.topic_name">
                <td class="cell-main">{{ row.topic_name || "未分类" }}</td>
                <td class="num">{{ row.person_count }}</td>
                <td class="cell-wrap" :title="(row.brigades || []).join('、')">
                  {{ (row.brigades || []).join("、") || "—" }}
                </td>
              </tr>
              <tr v-if="!topicStats.length">
                <td colspan="3">
                  <div class="empty" style="padding: 32px 20px">
                    <h4>暂无主题统计</h4>
                    <p>当前条件下还没有可汇总的培训记录。</p>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <section class="card" style="margin-top: 20px">
      <div class="card__head">
        <h3>单位完成情况</h3>
        <span class="sub">{{ selectedOrgName || "未选择单位" }}</span>
        <div class="grow"></div>
        <span class="badge badge--done">按人员类别</span>
      </div>

      <div v-if="!orgId" class="empty">
        <div class="empty__art"><AppIcon name="building" :size="26" /></div>
        <h4>先选择单位</h4>
        <p>在筛选栏选择单位后，这里按人员类别对比登记人数与已培训人数。</p>
      </div>

      <div v-else class="tablewrap">
        <table class="tb">
          <thead>
            <tr>
              <th>人员类别</th>
              <th class="num" style="width: 140px">本单位登记人数</th>
              <th class="num" style="width: 120px">已培训人数</th>
              <th style="width: 220px">完成进度</th>
              <th class="num" style="width: 90px">完成率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in completion" :key="row.job_title">
              <td class="cell-main">{{ row.job_title || "未填写类别" }}</td>
              <td class="num">{{ row.registered_count }}</td>
              <td class="num">{{ row.trained_count }}</td>
              <td>
                <div class="pbar" :aria-label="`完成率 ${row.completion_percent}%`">
                  <span :style="{ width: Math.min(100, Number(row.completion_percent) || 0) + '%' }"></span>
                </div>
              </td>
              <td class="num">{{ row.completion_percent }}%</td>
            </tr>
            <tr v-if="!completion.length">
              <td colspan="5">
                <div class="empty" style="padding: 32px 20px">
                  <h4>暂无完成情况</h4>
                  <p>该单位在当前条件下还没有登记人员或培训记录。</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <el-dialog v-model="trainingEditVisible" title="编辑培训" width="560px" destroy-on-close>
      <el-form :model="trainingEditForm" label-width="90px">
        <el-form-item label="培训名称" required>
          <el-input v-model="trainingEditForm.title" maxlength="256" />
        </el-form-item>
        <el-form-item label="培训主题">
          <el-select v-model="trainingEditForm.topic_id" clearable style="width: 100%">
            <el-option v-for="t in editTopicOptions" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="培训单位" required>
          <el-select
            v-model="trainingEditForm.organization_id"
            filterable
            remote
            reserve-keyword
            placeholder="输入单位名称搜索"
            :remote-method="remoteEditOrganization"
            :loading="editingOrganizationLoading"
            style="width: 100%"
          >
            <el-option
              v-for="o in trainingOrganizationOptions"
              :key="o.id"
              :label="o.district_name ? `${o.name}（${o.district_name}）` : o.name"
              :value="o.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间" required>
          <el-date-picker
            v-model="trainingEditForm.start_at"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="时长(分钟)">
          <el-input-number v-model="trainingEditForm.duration_minutes" :min="0" />
        </el-form-item>
        <el-form-item label="地点">
          <el-input v-model="trainingEditForm.location" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="trainingEditForm.remark" type="textarea" rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <button class="btn btn--ghost" @click="trainingEditVisible = false">取消</button>
        <button class="btn btn--primary" :disabled="trainingEditSaving" @click="saveTrainingEdit">
          {{ trainingEditSaving ? "保存中…" : "保存" }}
        </button>
      </template>
    </el-dialog>

    <el-dialog v-model="scanTrainingImportVisible" title="批量导入扫码培训" width="560px" destroy-on-close>
      <el-upload v-model:file-list="scanTrainingFiles" accept=".xlsx" multiple :auto-upload="false">
        <button class="btn btn--ghost">选择 Excel 文件</button>
      </el-upload>
      <p class="hint" style="margin-top: 10px">支持一次选择多个扫码导出文件，导入后自动归并为培训场次与签到记录。</p>
      <template #footer>
        <button class="btn btn--ghost" @click="scanTrainingImportVisible = false">取消</button>
        <button
          class="btn btn--primary"
          :disabled="!scanTrainingFiles.length || scanTrainingImporting"
          @click="submitScanTrainingImport"
        >
          {{ scanTrainingImporting ? "导入中…" : "开始导入" }}
        </button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import http from "../api/http";
import AppIcon from "../components/AppIcon.vue";

const loading = ref(false);
const range = ref([]);
const topics = ref([]);
const jobTitles = ref([]);
const topicId = ref();
const jobTitle = ref("");
const brigadeId = ref();
const brigades = ref([]);
const orgId = ref();
const orgOptions = ref([]);
const orgLoading = ref(false);
const summary = ref([]);
const summaryPage = ref(1);
const summaryPageSize = ref(20);
const summaryTotal = ref(0);
const jobStats = ref(null);
const topicStats = ref([]);
const completion = ref([]);
const currentAdmin = ref(null);
const trainingEditVisible = ref(false);
const trainingEditSaving = ref(false);
const editingTraining = ref(null);
const trainingOrganizationOptions = ref([]);
const editingOrganizationLoading = ref(false);
const scanTrainingImportVisible = ref(false);
const scanTrainingImporting = ref(false);
const scanTrainingFiles = ref([]);
const trainingEditForm = reactive({
  title: "",
  topic_id: null,
  organization_id: null,
  start_at: "",
  duration_minutes: 0,
  location: "",
  remark: "",
});
const canEditTraining = computed(() => currentAdmin.value?.role === "detachment");
const editTopicOptions = computed(() =>
  topics.value.filter((t) => t.is_active !== false || t.id === editingTraining.value?.topic_id)
);

/* ---- 展示辅助：已选条件回显 / 单个条件清除 ---- */
const selectedOrgName = ref("");
const filterChips = computed(() => {
  const chips = [];
  if (range.value?.[0]) {
    const end = range.value?.[1] ? ` 至 ${fmt(range.value[1])}` : " 起";
    chips.push({ key: "range", label: "区间", value: `${fmt(range.value[0])}${end}` });
  }
  if (topicId.value) {
    chips.push({ key: "topic", label: "主题", value: topics.value.find((t) => t.id === topicId.value)?.name || "已选" });
  }
  if (jobTitle.value) {
    chips.push({ key: "job", label: "类别", value: jobTitle.value });
  }
  if (brigadeId.value) {
    chips.push({
      key: "brigade",
      label: "大队",
      value: brigades.value.find((b) => Number(b.id) === Number(brigadeId.value))?.name || "已选",
    });
  }
  if (orgId.value) {
    chips.push({ key: "org", label: "单位", value: selectedOrgName.value || "已选" });
  }
  return chips;
});

function onOrgPicked(id) {
  if (!id) {
    selectedOrgName.value = "";
    return;
  }
  selectedOrgName.value = orgOptions.value.find((o) => Number(o.id) === Number(id))?.name || selectedOrgName.value;
}

function clearChip(key) {
  if (key === "range") range.value = [];
  else if (key === "topic") topicId.value = undefined;
  else if (key === "job") jobTitle.value = "";
  else if (key === "brigade") brigadeId.value = undefined;
  else if (key === "org") {
    orgId.value = undefined;
    selectedOrgName.value = "";
  }
  loadAll(true);
}

function resetFilters() {
  range.value = [];
  topicId.value = undefined;
  jobTitle.value = "";
  brigadeId.value = undefined;
  orgId.value = undefined;
  selectedOrgName.value = "";
  loadAll(true);
}

function params(extra = {}) {
  const p = { ...extra };
  if (range.value?.[0]) p.start = range.value[0];
  if (range.value?.[1]) p.end = range.value[1];
  if (topicId.value) p.topic_id = topicId.value;
  if (jobTitle.value) p.job_title = jobTitle.value;
  if (brigadeId.value) p.brigade_id = brigadeId.value;
  return p;
}

function fmt(v) {
  return v ? String(v).replace("T", " ").slice(0, 16) : "";
}

async function loadMeta() {
  const [topicRes, jobRes, brigadeRes] = await Promise.all([
    http.get("/api/admin/training-topics", { params: { include_inactive: true } }),
    http.get("/api/admin/job-titles"),
    http.get("/api/admin/brigades"),
  ]);
  topics.value = topicRes.data || [];
  jobTitles.value = jobRes.data || [];
  brigades.value = brigadeRes.data || [];
}

async function remoteOrg(q) {
  if (!q) {
    orgOptions.value = [];
    return;
  }
  orgLoading.value = true;
  try {
    const { data } = await http.get("/api/admin/organizations/suggest", { params: { q, limit: 30 } });
    orgOptions.value = data || [];
  } finally {
    orgLoading.value = false;
  }
}

function openTrainingEdit(row) {
  editingTraining.value = row;
  Object.assign(trainingEditForm, {
    title: row.title || "",
    topic_id: row.topic_id || null,
    organization_id: row.organization_id,
    start_at: row.start_at ? String(row.start_at).slice(0, 19) : "",
    duration_minutes: Number(row.duration_minutes || 0),
    location: row.location || "",
    remark: row.remark || "",
  });
  trainingOrganizationOptions.value = [
    {
      id: row.organization_id,
      name: row.organization_name,
      district_name: "",
    },
  ];
  trainingEditVisible.value = true;
}

async function remoteEditOrganization(q) {
  if (!q) return;
  editingOrganizationLoading.value = true;
  try {
    const { data } = await http.get("/api/admin/organizations/suggest", { params: { q, limit: 30 } });
    trainingOrganizationOptions.value = data || [];
  } finally {
    editingOrganizationLoading.value = false;
  }
}

async function saveTrainingEdit() {
  if (!editingTraining.value || !trainingEditForm.title.trim() || !trainingEditForm.start_at || !trainingEditForm.organization_id) {
    ElMessage.warning("请填写培训名称、开始时间并选择培训单位");
    return;
  }
  trainingEditSaving.value = true;
  try {
    await http.patch(`/api/admin/trainings/${editingTraining.value.session_id}`, {
      title: trainingEditForm.title.trim(),
      topic_id: trainingEditForm.topic_id || null,
      organization_id: trainingEditForm.organization_id,
      start_at: trainingEditForm.start_at,
      duration_minutes: Number(trainingEditForm.duration_minutes || 0),
      location: trainingEditForm.location.trim() || null,
      remark: trainingEditForm.remark.trim() || null,
    });
    ElMessage.success("培训数据已修改");
    trainingEditVisible.value = false;
    await loadAll();
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || "修改失败");
  } finally {
    trainingEditSaving.value = false;
  }
}

async function loadAll(resetPage = false) {
  if (resetPage) summaryPage.value = 1;
  loading.value = true;
  try {
    const calls = [
      http.get("/api/admin/stats/training-summary/page", {
        params: params({ page: summaryPage.value, page_size: summaryPageSize.value }),
      }),
      http.get("/api/admin/stats/by-topic", { params: params(topicId.value ? { topic_id: topicId.value } : {}) }),
    ];
    if (jobTitle.value) calls.push(http.get("/api/admin/stats/by-job-title", { params: params({ job_title: jobTitle.value }) }));
    else calls.push(Promise.resolve({ data: null }));
    if (orgId.value) calls.push(http.get("/api/admin/stats/org-completion", { params: params({ organization_id: orgId.value }) }));
    else calls.push(Promise.resolve({ data: [] }));
    const [s, t, j, c] = await Promise.all(calls);
    summary.value = s.data.items || [];
    summaryTotal.value = s.data.total || 0;
    topicStats.value = t.data || [];
    jobStats.value = j.data;
    completion.value = c.data || [];
  } finally {
    loading.value = false;
  }
}

function changeSummaryPage(nextPage) {
  summaryPage.value = nextPage;
  loadAll();
}

function changeSummaryPageSize(size) {
  summaryPageSize.value = size;
  loadAll(true);
}

async function downloadTemplate() {
  const { data } = await http.get("/api/admin/imports/person-template.xlsx", { responseType: "blob" });
  saveBlob(data, "person-import-template.xlsx");
}

async function exportSummary() {
  const { data } = await http.get("/api/admin/exports/training-summary.xlsx", {
    params: params(),
    responseType: "blob",
  });
  saveBlob(data, "training-summary.xlsx");
}

async function exportAttendance(row) {
  const { data } = await http.get(`/api/admin/exports/training-attendance/${row.session_id}.xlsx`, {
    responseType: "blob",
  });
  saveBlob(data, `${row.title || "培训"}-签到簿.xlsx`);
}

function saveBlob(data, name) {
  const url = URL.createObjectURL(new Blob([data]));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

async function uploadPersons({ file }) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await http.post("/api/admin/imports/persons", form);
  if (data.ok) {
    ElMessage.success(`导入完成，新增 ${data.imported} 人，更新 ${data.updated} 人`);
  } else {
    ElMessage.error((data.errors || []).slice(0, 5).join("；") || "导入失败");
  }
}

function openScanTrainingImport() {
  scanTrainingFiles.value = [];
  scanTrainingImportVisible.value = true;
}

async function submitScanTrainingImport() {
  if (!scanTrainingFiles.value.length) return;
  const form = new FormData();
  scanTrainingFiles.value.forEach((item) => form.append("files", item.raw));
  scanTrainingImporting.value = true;
  try {
    const { data } = await http.post("/api/admin/imports/scan-trainings", form);
    if (!data.ok) {
      ElMessage.error((data.errors || []).slice(0, 3).join("；") || "导入失败");
      return;
    }
    ElMessage.success(`已导入 ${data.files} 个文件：新增 ${data.sessions} 场培训、${data.imported} 条签到${data.skipped_duplicates ? `，已跳过 ${data.skipped_duplicates} 条重复记录` : ""}`);
    scanTrainingImportVisible.value = false;
    scanTrainingFiles.value = [];
    await loadAll();
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || "导入失败");
  } finally {
    scanTrainingImporting.value = false;
  }
}

onMounted(async () => {
  const [me] = await Promise.all([http.get("/api/admin/me"), loadMeta()]);
  currentAdmin.value = me.data;
  await loadAll();
});
</script>

<style scoped>
.statline {
  display: flex;
  align-items: baseline;
  gap: 8px;
  color: var(--ink-500);
  font-size: var(--fs-12);
}
.statline b {
  font-size: var(--fs-26);
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--ink-900);
}
.pbar {
  height: 5px;
  min-width: 120px;
  background: var(--surface-3);
  border-radius: 3px;
  overflow: hidden;
}
.pbar span {
  display: block;
  height: 100%;
  background: var(--brand-500);
  border-radius: 3px;
  transition: width var(--t-base);
}
.cell-wrap {
  font-size: var(--fs-12);
  line-height: 1.55;
  color: var(--ink-500);
}
</style>
