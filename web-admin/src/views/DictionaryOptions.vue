<template>
  <div class="page">
    <h2>字典配置</h2>
    <p class="tip">支队管理员可维护小程序注册时使用的单位类型、职务/岗位，以及培训前选择的主题分类。</p>

    <section class="panel">
      <div class="panel-head">
        <h3>单位类型</h3>
        <el-button type="primary" @click="openOrgType()">新增类型</el-button>
      </div>
      <el-table :data="orgTypes" border stripe v-loading="loading">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="code" label="编码" />
        <el-table-column prop="sort_order" label="排序" width="90" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? "启用" : "停用" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="openOrgType(row)">编辑</el-button>
            <el-button link type="danger" @click="removeOrgType(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3>培训主题</h3>
        <el-button type="primary" @click="openTopic()">新增主题</el-button>
      </div>
      <el-table :data="topics" border stripe v-loading="loading">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="sort_order" label="排序" width="90" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? "启用" : "停用" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="openTopic(row)">编辑</el-button>
            <el-button link type="danger" @click="removeTopic(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3>职务/岗位</h3>
        <el-button type="primary" @click="openJobTitle()">新增职务</el-button>
      </div>
      <el-table :data="jobTitles" border stripe v-loading="loading">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="sort_order" label="排序" width="90" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? "启用" : "停用" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="openJobTitle(row)">编辑</el-button>
            <el-button link type="danger" @click="removeJobTitle(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="420px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" maxlength="64" />
        </el-form-item>
        <el-form-item v-if="kind === 'org'" label="编码">
          <el-input v-model="form.code" maxlength="64" :disabled="!!editing" placeholder="新增时可不填，系统自动生成" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import http from "../api/http";

const loading = ref(false);
const saving = ref(false);
const orgTypes = ref([]);
const jobTitles = ref([]);
const topics = ref([]);
const dialogVisible = ref(false);
const kind = ref("org");
const editing = ref(null);
const form = reactive({ name: "", code: "", sort_order: 100, is_active: true });

const dialogTitle = computed(() => {
  const base = kind.value === "org" ? "单位类型" : "职务/岗位";
  if (kind.value === "topic") return `${editing.value ? "编辑" : "新增"}培训主题`;
  return `${editing.value ? "编辑" : "新增"}${base}`;
});

async function load() {
  loading.value = true;
  try {
    const [types, titles, topicRows] = await Promise.all([
      http.get("/api/admin/org-types", { params: { include_inactive: true } }),
      http.get("/api/admin/job-titles", { params: { include_inactive: true } }),
      http.get("/api/admin/training-topics", { params: { include_inactive: true } }),
    ]);
    orgTypes.value = types.data || [];
    jobTitles.value = titles.data || [];
    topics.value = topicRows.data || [];
  } finally {
    loading.value = false;
  }
}

function openOrgType(row) {
  kind.value = "org";
  open(row);
}

function openJobTitle(row) {
  kind.value = "job";
  open(row);
}

function openTopic(row) {
  kind.value = "topic";
  open(row);
}

function open(row) {
  editing.value = row || null;
  Object.assign(form, {
    name: row?.name || "",
    code: row?.code || "",
    sort_order: row?.sort_order ?? 100,
    is_active: row?.is_active ?? true,
  });
  dialogVisible.value = true;
}

async function submit() {
  if (!form.name.trim()) {
    ElMessage.warning("请填写名称");
    return;
  }
  saving.value = true;
  try {
    const url = kind.value === "org"
      ? "/api/admin/org-types"
      : kind.value === "topic"
        ? "/api/admin/training-topics"
        : "/api/admin/job-titles";
    const data = {
      name: form.name.trim(),
      sort_order: Number(form.sort_order || 100),
      is_active: !!form.is_active,
    };
    if (kind.value === "org" && !editing.value && form.code.trim()) data.code = form.code.trim();
    if (editing.value) await http.patch(`${url}/${editing.value.id}`, data);
    else await http.post(url, data);
    ElMessage.success("已保存");
    dialogVisible.value = false;
    await load();
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function removeOrgType(row) {
  await remove("/api/admin/org-types", row, "单位类型");
}

async function removeJobTitle(row) {
  await remove("/api/admin/job-titles", row, "职务");
}

async function removeTopic(row) {
  await remove("/api/admin/training-topics", row, "培训主题");
}

async function remove(url, row, label) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.name}」？如已有数据引用，将自动停用。`, `删除${label}`, {
      type: "warning",
    });
    await http.delete(`${url}/${row.id}`);
    ElMessage.success("已处理");
    await load();
  } catch (e) {
    if (e !== "cancel") ElMessage.error(e?.response?.data?.detail || "删除失败");
  }
}

onMounted(load);
</script>

<style scoped>
.page {
  background: #fff;
  border-radius: 8px;
  padding: 20px 24px;
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
.panel {
  margin-top: 18px;
}
.panel-head {
  align-items: center;
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}
h3 {
  margin: 0;
  font-size: 1rem;
}
</style>
