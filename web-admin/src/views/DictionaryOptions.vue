<template>
  <div>
    <div class="page-head">
      <div class="page-head__main">
        <div class="eyebrow">基础配置</div>
        <h1 class="page-title">字典配置</h1>
        <p class="page-desc">维护小程序注册与培训登记使用的单位类型、职务岗位和培训主题</p>
      </div>
    </div>

    <section class="card">
      <div class="card__head">
        <h3>单位类型</h3>
        <span class="sub">共 {{ orgTypes.length }} 项</span>
        <div class="grow"></div>
        <button class="btn btn--primary btn--sm" @click="openOrgType()">
          <AppIcon name="plus" :size="13" />新增类型
        </button>
      </div>
      <div v-loading="loading" class="tablewrap">
        <table class="tb">
          <thead>
            <tr>
              <th>名称</th>
              <th style="width: 180px">编码</th>
              <th class="num" style="width: 84px">排序</th>
              <th style="width: 92px">状态</th>
              <th class="col-actions" style="width: 120px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in orgTypes" :key="row.id">
              <td class="cell-main">{{ row.name }}</td>
              <td><span class="code">{{ row.code }}</span></td>
              <td class="num">{{ row.sort_order }}</td>
              <td>
                <span class="badge" :class="row.is_active ? 'badge--ok' : 'badge--off'">
                  {{ row.is_active ? "启用" : "停用" }}
                </span>
              </td>
              <td class="col-actions">
                <div class="rowact">
                  <button class="linkbtn" @click="openOrgType(row)">编辑</button>
                  <el-dropdown trigger="click" @command="(cmd) => cmd === 'delete' && removeOrgType(row)">
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
            <tr v-if="!orgTypes.length && !loading">
              <td colspan="5">
                <div class="empty">
                  <div class="empty__art"><AppIcon name="building" :size="26" /></div>
                  <h4>还没有单位类型</h4>
                  <p>新增后，小程序注册页的单位类型下拉即可选择。</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card">
      <div class="card__head">
        <h3>培训主题</h3>
        <span class="sub">共 {{ topics.length }} 项</span>
        <div class="grow"></div>
        <button class="btn btn--primary btn--sm" @click="openTopic()">
          <AppIcon name="plus" :size="13" />新增主题
        </button>
      </div>
      <div v-loading="loading" class="tablewrap">
        <table class="tb">
          <thead>
            <tr>
              <th>名称</th>
              <th class="num" style="width: 84px">排序</th>
              <th style="width: 92px">状态</th>
              <th class="col-actions" style="width: 120px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in topics" :key="row.id">
              <td class="cell-main">{{ row.name }}</td>
              <td class="num">{{ row.sort_order }}</td>
              <td>
                <span class="badge" :class="row.is_active ? 'badge--ok' : 'badge--off'">
                  {{ row.is_active ? "启用" : "停用" }}
                </span>
              </td>
              <td class="col-actions">
                <div class="rowact">
                  <button class="linkbtn" @click="openTopic(row)">编辑</button>
                  <el-dropdown trigger="click" @command="(cmd) => cmd === 'delete' && removeTopic(row)">
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
            <tr v-if="!topics.length && !loading">
              <td colspan="4">
                <div class="empty">
                  <div class="empty__art"><AppIcon name="list" :size="26" /></div>
                  <h4>还没有培训主题</h4>
                  <p>培训主题用于登记培训时归类，可先在后台补充常用主题。</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card">
      <div class="card__head">
        <h3>职务 / 岗位</h3>
        <span class="sub">共 {{ jobTitles.length }} 项</span>
        <div class="grow"></div>
        <button class="btn btn--primary btn--sm" @click="openJobTitle()">
          <AppIcon name="plus" :size="13" />新增职务
        </button>
      </div>
      <div v-loading="loading" class="tablewrap">
        <table class="tb">
          <thead>
            <tr>
              <th>名称</th>
              <th class="num" style="width: 84px">排序</th>
              <th style="width: 92px">状态</th>
              <th class="col-actions" style="width: 120px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in jobTitles" :key="row.id">
              <td class="cell-main">{{ row.name }}</td>
              <td class="num">{{ row.sort_order }}</td>
              <td>
                <span class="badge" :class="row.is_active ? 'badge--ok' : 'badge--off'">
                  {{ row.is_active ? "启用" : "停用" }}
                </span>
              </td>
              <td class="col-actions">
                <div class="rowact">
                  <button class="linkbtn" @click="openJobTitle(row)">编辑</button>
                  <el-dropdown trigger="click" @command="(cmd) => cmd === 'delete' && removeJobTitle(row)">
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
            <tr v-if="!jobTitles.length && !loading">
              <td colspan="4">
                <div class="empty">
                  <div class="empty__art"><AppIcon name="users" :size="26" /></div>
                  <h4>还没有职务 / 岗位</h4>
                  <p>新增后，小程序完善人员信息时可直接选择。</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <el-drawer v-model="dialogVisible" size="520px" :with-header="false" destroy-on-close class="form-drawer">
      <div class="drawer-shell">
        <div class="drawer__head">
          <div class="grow">
            <h3>{{ dialogTitle }}</h3>
            <p>
              {{
                kind === "org"
                  ? "单位类型决定小程序注册时可选的组织性质"
                  : kind === "topic"
                    ? "培训主题用于登记培训时分类归档"
                    : "职务 / 岗位用于完善人员信息"
              }}
            </p>
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
                  <label>名称<span class="req">*</span></label>
                  <el-input
                    v-model="form.name"
                    maxlength="64"
                    :placeholder="
                      kind === 'org' ? '如：应急管理部门' : kind === 'topic' ? '如：消防器材使用培训' : '如：消防安全管理人'
                    "
                  />
                </div>
                <div v-if="kind === 'org'" class="field span-2">
                  <label>编码</label>
                  <el-input v-model="form.code" maxlength="64" :disabled="!!editing" placeholder="新增时可不填，系统自动生成" />
                  <div class="hint">编码用于数据标识，保存后不可修改</div>
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
                <div class="field">
                  <label>状态</label>
                  <div class="status-line">
                    <el-switch v-model="form.is_active" />
                    <span class="hint" style="margin: 0">{{ form.is_active ? "启用" : "停用" }}</span>
                  </div>
                </div>
              </div>
            </div>
          </el-form>
        </div>
        <div class="drawer__foot">
          <span class="hint" style="margin: 0">删除已被引用的字典项时，系统会自动改为停用</span>
          <div class="grow"></div>
          <button class="btn btn--ghost" @click="dialogVisible = false">取消</button>
          <button class="btn btn--primary" :disabled="saving" @click="submit">
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

.code {
  font-family: var(--font-num);
  font-size: var(--fs-12);
  color: var(--ink-500);
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
</style>
