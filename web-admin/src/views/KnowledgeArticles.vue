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
        <h3>首页顶部图片</h3>
        <el-button type="primary" :loading="savingHome" @click="saveHomeConfig">保存设置</el-button>
      </div>
      <div class="banner-editor">
        <el-image
          v-if="homeConfig.banner_image_url"
          :src="assetUrl(homeConfig.banner_image_url)"
          fit="cover"
          class="banner-preview"
          :preview-src-list="[assetUrl(homeConfig.banner_image_url)]"
          preview-teleported
        />
        <div v-else class="banner-empty">未设置首页顶部图片</div>
        <div class="banner-actions">
          <el-input v-model="homeConfig.banner_image_url" maxlength="512" placeholder="可填写 https://... 或上传图片后自动生成" />
          <el-upload :show-file-list="false" accept="image/*" :http-request="uploadHomeBanner">
            <el-button>上传图片</el-button>
          </el-upload>
        </div>
      </div>
    </section>

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
            :src="assetUrl(row.image_url)"
            fit="cover"
            style="width: 52px; height: 36px; border-radius: 6px"
            :preview-src-list="[assetUrl(row.image_url)]"
            preview-teleported
          />
          <span v-else class="muted">无</span>
        </template>
      </el-table-column>
      <el-table-column label="视频" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.video_url" type="success">已上传</el-tag>
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
          <div class="media-field">
            <el-input v-model="form.image_url" maxlength="512" placeholder="https://...，用于小程序栏目列表和活动卡片展示" />
            <el-upload :show-file-list="false" accept="image/*" :http-request="uploadArticleImage">
              <el-button>上传图片</el-button>
            </el-upload>
          </div>
        </el-form-item>
        <el-form-item label="视频地址">
          <div class="media-field">
            <el-input v-model="form.video_url" maxlength="512" placeholder="宣传视频栏目可上传 mp4/mov/webm，供小程序端播放" />
            <el-upload :show-file-list="false" accept="video/*" :http-request="uploadArticleVideo">
              <el-button>上传视频</el-button>
            </el-upload>
          </div>
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
const savingHome = ref(false);
const homeConfig = reactive({ banner_image_url: "" });
const form = reactive({
  category: "knowledge",
  title: "",
  content: "",
  image_url: "",
  video_url: "",
  sort_order: 100,
  is_active: true,
});
const newCategory = reactive({ name: "", sort_order: 100 });

function categoryName(value) {
  return categories.value.find((c) => c.code === value)?.name || value;
}

function apiBase() {
  let raw = (import.meta.env.VITE_API_BASE || "").trim().replace(/\/+$/, "");
  if (raw.endsWith("/api")) raw = raw.slice(0, -4);
  return raw;
}

function assetUrl(value) {
  if (!value) return "";
  if (/^https?:\/\//i.test(value)) return value;
  return `${apiBase()}${value}`;
}

async function uploadMedia(file) {
  const data = new FormData();
  data.append("file", file);
  const res = await http.post("/api/admin/media/upload", data, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120000,
  });
  return res.data?.url || "";
}

async function load() {
  loading.value = true;
  try {
    const [catRes, articleRes, homeRes] = await Promise.all([
      http.get("/api/admin/knowledge-categories", { params: { include_inactive: true } }),
      http.get("/api/admin/knowledge-articles", { params: { include_inactive: true } }),
      http.get("/api/admin/home-config"),
    ]);
    categories.value = catRes.data || [];
    const active = categories.value.find((c) => c.is_active) || categories.value[0];
    if (active && !categories.value.some((c) => c.code === form.category)) form.category = active.code;
    rows.value = articleRes.data || [];
    homeConfig.banner_image_url = homeRes.data?.banner_image_url || "";
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
    video_url: row?.video_url || "",
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
    const data = {
      ...form,
      title: form.title.trim(),
      image_url: form.image_url.trim() || null,
      video_url: form.video_url.trim() || null,
    };
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

async function uploadHomeBanner({ file }) {
  try {
    homeConfig.banner_image_url = await uploadMedia(file);
    ElMessage.success("图片已上传，请保存设置");
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || "上传失败");
  }
}

async function uploadArticleImage({ file }) {
  try {
    form.image_url = await uploadMedia(file);
    ElMessage.success("图片已上传");
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || "上传失败");
  }
}

async function uploadArticleVideo({ file }) {
  try {
    form.video_url = await uploadMedia(file);
    ElMessage.success("视频已上传");
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || "上传失败");
  }
}

async function saveHomeConfig() {
  savingHome.value = true;
  try {
    const res = await http.patch("/api/admin/home-config", {
      banner_image_url: homeConfig.banner_image_url.trim() || null,
    });
    homeConfig.banner_image_url = res.data?.banner_image_url || "";
    ElMessage.success("首页顶部图片已保存");
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || "保存失败");
  } finally {
    savingHome.value = false;
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
.banner-editor {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 16px;
  align-items: center;
}
.banner-preview,
.banner-empty {
  width: 320px;
  height: 150px;
  border-radius: 8px;
  overflow: hidden;
  background: #eef3fb;
}
.banner-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8a94a6;
  border: 1px dashed #c7d2e4;
}
.banner-actions,
.media-field {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;
}
.media-field .el-input {
  flex: 1;
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
