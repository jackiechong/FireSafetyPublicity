<template>
  <div class="page">
    <div class="head">
      <div>
        <h2>综合查询</h2>
        <p>按时间区间、人员类别、培训主题、单位名称查询统计，并支持 Excel 导入导出。</p>
      </div>
      <div class="actions">
        <el-button @click="downloadTemplate">下载导入模板</el-button>
        <el-upload :show-file-list="false" accept=".xlsx" :http-request="uploadPersons">
          <el-button type="primary">批量导入人员</el-button>
        </el-upload>
        <el-button type="success" @click="exportSummary">导出统计 Excel</el-button>
      </div>
    </div>

    <section class="filters">
      <el-date-picker v-model="range" type="datetimerange" start-placeholder="开始时间" end-placeholder="结束时间" value-format="YYYY-MM-DDTHH:mm:ss" />
      <el-select v-model="topicId" clearable placeholder="培训主题" style="width: 180px">
        <el-option v-for="t in topics" :key="t.id" :label="t.name" :value="t.id" />
      </el-select>
      <el-select v-model="jobTitle" clearable filterable placeholder="人员类别/职务" style="width: 180px">
        <el-option v-for="j in jobTitles" :key="j.id" :label="j.name" :value="j.name" />
      </el-select>
      <el-select v-model="orgId" filterable remote clearable reserve-keyword placeholder="输入单位名称" :remote-method="remoteOrg" :loading="orgLoading" style="width: 260px">
        <el-option v-for="o in orgOptions" :key="o.id" :label="`${o.name}（${o.district_name}）`" :value="o.id" />
      </el-select>
      <el-button type="primary" @click="loadAll">查询</el-button>
    </section>

    <section class="panel">
      <h3>培训清单</h3>
      <el-table :data="summary" border stripe v-loading="loading">
        <el-table-column prop="title" label="培训名称" min-width="180" />
        <el-table-column label="开展日期" width="170">
          <template #default="{ row }">{{ fmt(row.start_at) }}</template>
        </el-table-column>
        <el-table-column prop="person_count" label="培训人数" width="100" />
        <el-table-column prop="topic_name" label="培训主题" min-width="140" />
        <el-table-column prop="brigade_name" label="开展大队" min-width="120" />
        <el-table-column prop="organization_name" label="单位" min-width="180" />
      </el-table>
    </section>

    <section class="grid">
      <div class="panel">
        <h3>按人员类别</h3>
        <el-empty v-if="!jobStats" description="请选择人员类别后查询" />
        <div v-else>
          <div class="metric">{{ jobStats.total_person_count }} 人</div>
          <el-table :data="jobStats.district_counts" border size="small">
            <el-table-column prop="district_name" label="区县" />
            <el-table-column prop="person_count" label="培训人数" width="100" />
          </el-table>
        </div>
      </div>

      <div class="panel">
        <h3>按培训主题</h3>
        <el-table :data="topicStats" border size="small">
          <el-table-column prop="topic_name" label="主题" />
          <el-table-column prop="person_count" label="培训人数" width="100" />
          <el-table-column label="开展大队">
            <template #default="{ row }">{{ (row.brigades || []).join("、") || "—" }}</template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <section class="panel">
      <h3>单位完成情况</h3>
      <el-empty v-if="!orgId" description="请选择单位后查询" />
      <el-table v-else :data="completion" border stripe>
        <el-table-column prop="job_title" label="人员类别" />
        <el-table-column prop="registered_count" label="本单位登记人数" width="140" />
        <el-table-column prop="trained_count" label="已培训人数" width="120" />
        <el-table-column label="完成百分比" width="180">
          <template #default="{ row }">
            <el-progress :percentage="row.completion_percent" />
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import http from "../api/http";

const loading = ref(false);
const range = ref([]);
const topics = ref([]);
const jobTitles = ref([]);
const topicId = ref();
const jobTitle = ref("");
const orgId = ref();
const orgOptions = ref([]);
const orgLoading = ref(false);
const summary = ref([]);
const jobStats = ref(null);
const topicStats = ref([]);
const completion = ref([]);

function params(extra = {}) {
  const p = { ...extra };
  if (range.value?.[0]) p.start = range.value[0];
  if (range.value?.[1]) p.end = range.value[1];
  if (topicId.value) p.topic_id = topicId.value;
  if (jobTitle.value) p.job_title = jobTitle.value;
  return p;
}

function fmt(v) {
  return v ? String(v).replace("T", " ").slice(0, 16) : "";
}

async function loadMeta() {
  const [topicRes, jobRes] = await Promise.all([
    http.get("/api/admin/training-topics"),
    http.get("/api/admin/job-titles"),
  ]);
  topics.value = topicRes.data || [];
  jobTitles.value = jobRes.data || [];
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

async function loadAll() {
  loading.value = true;
  try {
    const calls = [
      http.get("/api/admin/stats/training-summary", { params: params() }),
      http.get("/api/admin/stats/by-topic", { params: params(topicId.value ? { topic_id: topicId.value } : {}) }),
    ];
    if (jobTitle.value) calls.push(http.get("/api/admin/stats/by-job-title", { params: params({ job_title: jobTitle.value }) }));
    else calls.push(Promise.resolve({ data: null }));
    if (orgId.value) calls.push(http.get("/api/admin/stats/org-completion", { params: params({ organization_id: orgId.value }) }));
    else calls.push(Promise.resolve({ data: [] }));
    const [s, t, j, c] = await Promise.all(calls);
    summary.value = s.data || [];
    topicStats.value = t.data || [];
    jobStats.value = j.data;
    completion.value = c.data || [];
  } finally {
    loading.value = false;
  }
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

onMounted(async () => {
  await loadMeta();
  await loadAll();
});
</script>

<style scoped>
.page {
  background: #fff;
  border-radius: 8px;
  padding: 20px 24px;
}
.head,
.actions,
.filters {
  align-items: center;
  display: flex;
  gap: 12px;
}
.head {
  justify-content: space-between;
}
h2 {
  margin: 0 0 6px;
  font-size: 1.25rem;
}
p {
  color: #777;
  margin: 0;
}
.filters {
  flex-wrap: wrap;
  margin: 18px 0;
}
.panel {
  margin-top: 18px;
}
.grid {
  display: grid;
  gap: 18px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
h3 {
  font-size: 1rem;
  margin: 0 0 10px;
}
.metric {
  color: #1a237e;
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 10px;
}
</style>
