<template>
  <div class="page">
    <div class="head">
      <div>
        <h2>知识专栏</h2>
        <p>维护小程序首页展示的栏目名称和栏目内容。</p>
      </div>
      <el-button type="primary" @click="open()">新增内容</el-button>
    </div>

    <section class="panel">
      <div class="panel-head">
        <h3>栏目管理</h3>
        <div class="category-add">
          <el-input v-model="newCategory.name" maxlength="64" placeholder="新增栏目名称" style="width: 180px" />
          <el-input-number v-model="newCategory.sort_order" :min="0" :max="9999" size="small" />
          <el-button type="primary" :loading="saving" @click="addCategory">新增栏目</el-button>
        </div>
      </div>
      <el-table :data="categories" border stripe size="small">
        <el-table-column label="栏目名称">
          <template #default="{ row }">
            <el-input v-model="row.name" maxlength="64" size="small" />
          </template>
        </el-table-column>
        <el-table-column prop="code" label="编码" width="140" />
        <el-table-column label="排序" width="120">
          <template #default="{ row }">
            <el-input-number v-model="row.sort_order" :min="0" :max="9999" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="saveCategory(row)">保存</el-button>
            <el-button link type="danger" @click="removeCategory(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-table :data="rows" border stripe v-loading="loading" style="margin-top: 16px">
      <el-table-column label="栏目" width="120">
        <template #default="{ row }">{{ categoryName(row.category) }}</template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="180" />
      <el-table-column label="图片" width="90">
        <template #default="{ row }">
          <el-image
            v-if="row.image_url"
            :src="row.image_url"
            fit="cover"
            style="width: 52px; height: 36px; border-radius: 6px"
            :preview-src-list="[row.image_url]"
            preview-teleported
          />
          <span v-else class="muted">无</span>
        </template>
      </el-table-column>
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
            <el-option v-for="c in categories" :key="c.code" :label="c.name" :value="c.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="200" />
        </el-form-item>
        <el-form-item label="图片地址">
          <el-input v-model="form.image_url" maxlength="512" placeholder="https://...，用于小程序首页内容卡片展示" />
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

const loading = ref(false);
const saving = ref(false);
const visible = ref(false);
const editing = ref(null);
const rows = ref([]);
const categories = ref([]);
const form = reactive({
  category: "knowledge",
  title: "",
  content: "",
  image_url: "",
  sort_order: 100,
  is_active: true,
});
const newCategory = reactive({ name: "", sort_order: 100 });

function categoryName(value) {
  return categories.value.find((c) => c.code === value)?.name || value;
}

async function load() {
  loading.value = true;
  try {
    const [catRes, articleRes] = await Promise.all([
      http.get("/api/admin/knowledge-categories", { params: { include_inactive: true } }),
      http.get("/api/admin/knowledge-articles", { params: { include_inactive: true } }),
    ]);
    categories.value = catRes.data || [];
    const active = categories.value.find((c) => c.is_active) || categories.value[0];
    if (active && !categories.value.some((c) => c.code === form.category)) form.category = active.code;
    rows.value = articleRes.data || [];
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
    image_url: row?.image_url || "",
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
    const data = { ...form, title: form.title.trim(), image_url: form.image_url.trim() || null };
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

async function addCategory() {
  if (!newCategory.name.trim()) {
    ElMessage.warning("请填写栏目名称");
    return;
  }
  saving.value = true;
  try {
    await http.post("/api/admin/knowledge-categories", {
      name: newCategory.name.trim(),
      sort_order: Number(newCategory.sort_order || 100),
      is_active: true,
    });
    ElMessage.success("栏目已新增");
    newCategory.name = "";
    newCategory.sort_order = 100;
    await load();
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function saveCategory(row) {
  if (!row.name.trim()) {
    ElMessage.warning("请填写栏目名称");
    return;
  }
  saving.value = true;
  try {
    await http.patch(`/api/admin/knowledge-categories/${row.id}`, {
      name: row.name.trim(),
      sort_order: Number(row.sort_order || 100),
      is_active: !!row.is_active,
    });
    ElMessage.success("栏目已保存");
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

async function removeCategory(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.name}」？如已有内容引用，将自动停用。`, "删除栏目", { type: "warning" });
    await http.delete(`/api/admin/knowledge-categories/${row.id}`);
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
.panel {
  margin-top: 16px;
}
.panel-head {
  align-items: center;
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}
.category-add {
  align-items: center;
  display: flex;
  gap: 8px;
}
h3 {
  font-size: 1rem;
  margin: 0;
}
.muted {
  color: #999;
  font-size: 12px;
}
</style>
