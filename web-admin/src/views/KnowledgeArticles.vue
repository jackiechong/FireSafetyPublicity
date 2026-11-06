<template>
  <div>
    <div class="page-head">
      <div class="page-head__main">
        <div class="eyebrow">宣传阵地</div>
        <h1 class="page-title">知识专栏</h1>
        <p class="page-desc">维护小程序首页的栏目、图文与视频内容，以及顶部宣传图</p>
      </div>
      <div class="page-actions">
        <button class="btn btn--ghost" @click="openNotice">
          <AppIcon name="bell" :size="15" />发布通知公告
        </button>
        <button class="btn btn--primary" @click="open()">
          <AppIcon name="plus" :size="15" />新增内容
        </button>
      </div>
    </div>

    <section class="card">
      <div class="card__head">
        <h3>首页顶部图片</h3>
        <span class="sub">展示在小程序首页顶部</span>
        <div class="grow"></div>
        <button class="btn btn--primary btn--sm" :disabled="savingHome" @click="saveHomeConfig">
          {{ savingHome ? "保存中…" : "保存设置" }}
        </button>
      </div>
      <div class="card__body banner-editor">
        <el-image
          v-if="homeConfig.banner_image_url"
          :src="assetUrl(homeConfig.banner_image_url)"
          fit="cover"
          class="banner-preview"
          :preview-src-list="[assetUrl(homeConfig.banner_image_url)]"
          preview-teleported
        />
        <div v-else class="banner-empty">
          <AppIcon name="image" :size="22" />
          <span>尚未设置顶部图片</span>
        </div>
        <div class="field">
          <label for="banner-url">图片地址</label>
          <div class="media-field">
            <input
              id="banner-url"
              v-model="homeConfig.banner_image_url"
              class="input"
              maxlength="512"
              placeholder="粘贴 https:// 图片链接，或上传后自动填入"
            />
            <el-upload :show-file-list="false" accept="image/*" :http-request="uploadHomeBanner">
              <button type="button" class="btn btn--ghost">
                <AppIcon name="upload" :size="14" />上传
              </button>
            </el-upload>
          </div>
          <div class="hint">建议 750 × 320 像素横图，保存后小程序端即时生效</div>
        </div>
      </div>
    </section>

    <section class="card">
      <div class="card__head">
        <h3>栏目管理</h3>
        <span class="sub">共 {{ categories.length }} 个栏目 · 修改后点“保存”生效</span>
      </div>
      <div class="card__body cat-add">
        <input
          v-model="newCategory.name"
          class="input"
          maxlength="64"
          placeholder="新增栏目名称，如：消防知识"
          style="width: 240px"
        />
        <el-input-number
          v-model="newCategory.sort_order"
          :min="0"
          :max="9999"
          size="small"
          controls-position="right"
          style="width: 108px"
        />
        <button class="btn btn--primary btn--sm" :disabled="saving" @click="addCategory">
          <AppIcon name="plus" :size="13" />新增栏目
        </button>
      </div>
      <div class="tablewrap">
        <table class="tb">
          <thead>
            <tr>
              <th>栏目名称</th>
              <th style="width: 168px">编码</th>
              <th style="width: 128px">排序</th>
              <th style="width: 96px">状态</th>
              <th class="col-actions" style="width: 132px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in categories" :key="c.id">
              <td>
                <el-input v-model="c.name" size="small" maxlength="64" />
              </td>
              <td><span class="code">{{ c.code }}</span></td>
              <td>
                <el-input-number
                  v-model="c.sort_order"
                  :min="0"
                  :max="9999"
                  size="small"
                  controls-position="right"
                  style="width: 108px"
                />
              </td>
              <td>
                <el-switch v-model="c.is_active" size="small" />
              </td>
              <td class="col-actions">
                <div class="rowact">
                  <button class="linkbtn" @click="saveCategory(c)">保存</button>
                  <el-dropdown trigger="click" @command="(cmd) => cmd === 'delete' && removeCategory(c)">
                    <button class="iconbtn" aria-label="更多操作"><AppIcon name="more" :size="16" /></button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="delete" class="is-danger">删除栏目</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </td>
            </tr>
            <tr v-if="!categories.length">
              <td colspan="5">
                <div class="empty">
                  <div class="empty__art"><AppIcon name="layers" :size="26" /></div>
                  <h4>还没有栏目</h4>
                  <p>先在上方输入栏目名称并新增，内容才能归类展示。</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card">
      <div class="card__head">
        <h3>专栏内容</h3>
        <span class="sub">共 {{ rows.length }} 条</span>
        <div class="grow"></div>
        <span class="badge badge--ok">启用 {{ rows.filter((r) => r.is_active).length }}</span>
      </div>
      <div v-loading="loading" class="tablewrap">
        <table class="tb">
          <thead>
            <tr>
              <th style="width: 132px">栏目</th>
              <th>标题</th>
              <th style="width: 84px">图片</th>
              <th style="width: 96px">视频</th>
              <th class="num" style="width: 72px">排序</th>
              <th style="width: 92px">状态</th>
              <th class="col-actions" style="width: 120px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td>{{ categoryName(row.category) }}</td>
              <td>
                <button class="cell-main linkbtn" style="padding: 0" @click="open(row)">{{ row.title }}</button>
              </td>
              <td>
                <el-image
                  v-if="row.image_url"
                  :src="assetUrl(row.image_url)"
                  fit="cover"
                  class="thumb"
                  :preview-src-list="[assetUrl(row.image_url)]"
                  preview-teleported
                />
                <span v-else class="muted">无</span>
              </td>
              <td>
                <span v-if="row.video_url" class="badge badge--ok">已上传</span>
                <span v-else class="badge badge--off">无</span>
              </td>
              <td class="num">{{ row.sort_order }}</td>
              <td>
                <span class="badge" :class="row.is_active ? 'badge--ok' : 'badge--off'">
                  {{ row.is_active ? "启用" : "停用" }}
                </span>
              </td>
              <td class="col-actions">
                <div class="rowact">
                  <button class="linkbtn" @click="open(row)">编辑</button>
                  <el-dropdown trigger="click" @command="(cmd) => cmd === 'delete' && remove(row)">
                    <button class="iconbtn" aria-label="更多操作"><AppIcon name="more" :size="16" /></button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="delete" class="is-danger">删除</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </td>
            </tr>
            <tr v-if="!rows.length && !loading">
              <td colspan="7">
                <div class="empty">
                  <div class="empty__art"><AppIcon name="book" :size="26" /></div>
                  <h4>还没有专栏内容</h4>
                  <p>新增图文或视频内容，也可以先发一条通知公告。</p>
                  <button class="btn btn--primary btn--sm" @click="open()">新增内容</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <el-drawer v-model="visible" size="520px" :with-header="false" destroy-on-close class="form-drawer">
      <div class="drawer-shell">
        <div class="drawer__head">
          <div class="grow">
            <h3>{{ editing ? "编辑内容" : "新增内容" }}</h3>
            <p>保存后可在小程序对应栏目中查看</p>
          </div>
          <button class="iconbtn" aria-label="关闭" @click="visible = false">
            <AppIcon name="x" :size="16" />
          </button>
        </div>
        <div class="drawer__body">
          <el-form :model="form" label-position="top">
            <div class="fieldset">
              <div class="fieldset__title">基本信息</div>
              <div class="formgrid">
                <div class="field">
                  <label>所属栏目<span class="req">*</span></label>
                  <el-select v-model="form.category" style="width: 100%">
                    <el-option v-for="c in categories" :key="c.code" :label="c.name" :value="c.code" />
                    <el-option v-if="!categories.some((c) => c.code === 'notice')" label="通知公告" value="notice" />
                  </el-select>
                </div>
                <div class="field">
                  <label>排序</label>
                  <el-input-number
                    v-model="form.sort_order"
                    :min="0"
                    :max="9999"
                    controls-position="right"
                    style="width: 100%"
                  />
                </div>
                <div class="field span-2">
                  <label>标题<span class="req">*</span></label>
                  <el-input v-model="form.title" maxlength="200" placeholder="如：关于开展消防宣传月活动的通知" />
                </div>
                <div class="field span-2">
                  <label>状态</label>
                  <div class="status-line">
                    <el-switch v-model="form.is_active" />
                    <span class="hint" style="margin: 0">
                      {{ form.is_active ? "启用后在小程序展示" : "停用后仅后台可见" }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div class="fieldset">
              <div class="fieldset__title">封面与视频</div>
              <div class="formgrid">
                <div class="field span-2">
                  <label>封面图片</label>
                  <div class="media-field">
                    <el-input v-model="form.image_url" maxlength="512" placeholder="https://…，用于栏目列表卡片" />
                    <el-upload :show-file-list="false" accept="image/*" :http-request="uploadArticleImage">
                      <button type="button" class="btn btn--ghost btn--sm">上传</button>
                    </el-upload>
                  </div>
                  <div class="hint">留空则不展示封面图</div>
                </div>
                <div class="field span-2">
                  <label>视频地址</label>
                  <div class="media-field">
                    <el-input v-model="form.video_url" maxlength="512" placeholder="宣传视频栏目可上传 mp4 / mov / webm" />
                    <el-upload :show-file-list="false" accept="video/*" :http-request="uploadArticleVideo">
                      <button type="button" class="btn btn--ghost btn--sm">上传</button>
                    </el-upload>
                  </div>
                  <div class="hint">仅“宣传视频”类栏目需要</div>
                </div>
              </div>
            </div>

            <div class="fieldset">
              <div class="fieldset__title">正文</div>
              <el-input
                v-model="form.content"
                type="textarea"
                :rows="10"
                maxlength="20000"
                show-word-limit
                placeholder="支持纯文本排版，换行会在小程序端保留"
              />
            </div>
          </el-form>
        </div>
        <div class="drawer__foot">
          <span class="hint" style="margin: 0">{{ editing ? "修改保存后立即生效" : "保存后可在小程序查看" }}</span>
          <div class="grow"></div>
          <button class="btn btn--ghost" @click="visible = false">取消</button>
          <button class="btn btn--primary" :disabled="saving" @click="submit">
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
  return categories.value.find((c) => c.code === value)?.name || (value === "notice" ? "通知公告" : value);
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

function open(row, defaultCategory = "knowledge") {
  editing.value = row || null;
  Object.assign(form, {
    category: row?.category || defaultCategory,
    title: row?.title || "",
    content: row?.content || "",
    image_url: row?.image_url || "",
    video_url: row?.video_url || "",
    sort_order: row?.sort_order ?? 100,
    is_active: row?.is_active ?? true,
  });
  visible.value = true;
}

function openNotice() {
  open(null, "notice");
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
.drawer-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
}
:deep(.form-drawer .el-drawer__body) {
  padding: 0;
  overflow: hidden;
}

.card + .card {
  margin-top: var(--s4);
}

.banner-editor {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: var(--s5);
  align-items: start;
}
.banner-preview {
  display: block;
  width: 100%;
  aspect-ratio: 750 / 320;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  overflow: hidden;
  background: var(--surface-3);
}
.banner-empty {
  display: grid;
  place-items: center;
  gap: 6px;
  aspect-ratio: 750 / 320;
  border: 1px dashed var(--line-strong);
  border-radius: var(--r-md);
  background: var(--surface-3);
  color: var(--ink-400);
  font-size: var(--fs-12);
}

.media-field {
  display: flex;
  align-items: center;
  gap: var(--s2);
}
.media-field .el-input {
  flex: 1;
  min-width: 0;
}

.cat-add {
  display: flex;
  align-items: center;
  gap: var(--s2);
  flex-wrap: wrap;
  padding-bottom: 0;
}
.cat-add .input {
  height: 32px;
}

.code {
  font-family: var(--font-num);
  font-size: var(--fs-12);
  color: var(--ink-500);
}
.thumb {
  display: block;
  width: 56px;
  height: 38px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  overflow: hidden;
  background: var(--surface-3);
}
.muted {
  font-size: var(--fs-12);
  color: var(--ink-400);
}
.rowact {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.status-line {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 34px;
}

@media (max-width: 980px) {
  .banner-editor {
    grid-template-columns: 1fr;
  }
}
</style>
