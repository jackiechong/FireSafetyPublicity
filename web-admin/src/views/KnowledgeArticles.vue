<template>
  <div class="page">
    <div class="head">
      <div>
        <h2>知识专栏</h2>
        <p>维护小程序首页展示的消防知识、法律法规、制度、器材使用内容。</p>
      </div>
      <el-button type="primary" @click="open()">新增内容</el-button>
    </div>

    <el-table :data="rows" border stripe v-loading="loading" style="margin-top: 16px">
      <el-table-column label="栏目" width="120">
        <template #default="{ row }">{{ categoryName(row.category) }}</template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="180" />
      <el-table-column prop="sort_order" label="排序" width="90" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? "启用" : "停用" }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button link type="primary" @click="open(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="editing ? '编辑内容' : '新增内容'" width="640px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="栏目" required>
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="c in categories" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="200" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="8" maxlength="20000" show-word-limit />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import http from "../api/http";

const categories = [
  { value: "knowledge", label: "消防知识" },
  { value: "law", label: "法律法规" },
  { value: "system", label: "制度" },
  { value: "equipment", label: "器材使用" },
];

const loading = ref(false);
const saving = ref(false);
const visible = ref(false);
const editing = ref(null);
const rows = ref([]);
const form = reactive({
  category: "knowledge",
  title: "",
  content: "",
  sort_order: 100,
  is_active: true,
});

function categoryName(value) {
  return categories.find((c) => c.value === value)?.label || value;
}

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/api/admin/knowledge-articles", { params: { include_inactive: true } });
    rows.value = data || [];
  } finally {
    loading.value = false;
  }
}

function open(row) {
  editing.value = row || null;
  Object.assign(form, {
    category: row?.category || "knowledge",
    title: row?.title || "",
    content: row?.content || "",
    sort_order: row?.sort_order ?? 100,
    is_active: row?.is_active ?? true,
  });
  visible.value = true;
}

async function submit() {
  if (!form.title.trim()) {
    ElMessage.warning("请填写标题");
    return;
  }
  saving.value = true;
  try {
    const data = { ...form, title: form.title.trim() };
    if (editing.value) await http.patch(`/api/admin/knowledge-articles/${editing.value.id}`, data);
    else await http.post("/api/admin/knowledge-articles", data);
    ElMessage.success("已保存");
    visible.value = false;
    await load();
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」？`, "删除内容", { type: "warning" });
    await http.delete(`/api/admin/knowledge-articles/${row.id}`);
    ElMessage.success("已删除");
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
.head {
  align-items: center;
  display: flex;
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
</style>
