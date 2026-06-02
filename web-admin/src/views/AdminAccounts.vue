<template>
  <div class="page">
    <h2>管理员账号与权限</h2>
    <p class="tip">仅「支队」账号可管理；大队账号只能管理本单位数据，不能进入本页。</p>
    <el-button type="primary" @click="openCreate">新建管理员</el-button>

    <el-table :data="rows" border stripe v-loading="loading" style="margin-top: 16px">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column label="角色" width="120">
        <template #default="{ row }">
          {{ row.role === "detachment" ? "支队（全市）" : "大队" }}
        </template>
      </el-table-column>
      <el-table-column label="所属大队" min-width="120">
        <template #default="{ row }">{{ row.brigade_name || "—" }}</template>
      </el-table-column>
      <el-table-column label="小程序绑定" min-width="160">
        <template #default="{ row }">
          <el-tag v-if="row.wx_bound" type="success">已绑定 {{ row.wx_binding_count || 0 }} 个微信</el-tag>
          <el-tag v-else type="info">未绑定</el-tag>
          <div v-if="row.wx_bound && row.wx_bound_at" class="bind-time">
            首次：{{ formatTime(row.wx_bound_at) }}
          </div>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? "启用" : "停用" }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="320" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">权限</el-button>
          <el-button link type="warning" @click="openPwd(row)">改密</el-button>
          <el-button link type="success" :disabled="!row.is_active" @click="genBindCode(row)">
            生成绑定码
          </el-button>
          <el-button link type="info" :disabled="!row.wx_bound" @click="openBindings(row)">微信列表</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="createVisible" title="新建管理员" width="480px" destroy-on-close>
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="用户名" required>
          <el-input v-model="createForm.username" autocomplete="off" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="createForm.password" type="password" show-password autocomplete="new-password" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-radio-group v-model="createForm.role">
            <el-radio value="detachment">支队</el-radio>
            <el-radio value="brigade">大队</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="createForm.role === 'brigade'" label="所属大队" required>
          <el-select v-model="createForm.brigade_id" style="width: 100%" placeholder="请选择">
            <el-option v-for="b in allBrigades" :key="b.id" :label="b.name" :value="b.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="调整权限" width="480px" destroy-on-close>
      <el-form label-width="100px">
        <el-form-item label="用户名">
          <span>{{ editing?.username }}</span>
        </el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="editForm.role">
            <el-radio value="detachment">支队</el-radio>
            <el-radio value="brigade">大队</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="editForm.role === 'brigade'" label="所属大队">
          <el-select v-model="editForm.brigade_id" style="width: 100%">
            <el-option v-for="b in allBrigades" :key="b.id" :label="b.name" :value="b.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="editForm.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="pwdVisible" title="重置密码" width="400px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.new_password" type="password" show-password autocomplete="new-password" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitPwd">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="bindCodeVisible" title="小程序绑定码" width="420px" destroy-on-close>
      <p class="tip">请让管理员 <b>{{ bindCodeUser?.username }}</b> 在小程序「身份绑定」页输入下方 8 位数字。</p>
      <div v-if="bindCodeData" class="bind-code-box">
        <div class="bind-code">{{ bindCodeData.code }}</div>
        <p class="bind-expire">有效期 {{ bindCodeData.expires_in_minutes }} 分钟，至 {{ formatTime(bindCodeData.expires_at) }}</p>
      </div>
      <template #footer>
        <el-button type="primary" @click="bindCodeVisible = false">知道了</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="bindingsVisible" title="已绑定微信" width="620px" destroy-on-close>
      <p class="tip">
        管理员账号 <b>{{ bindingsUser?.username }}</b> 可同时绑定多个微信；同一个微信不能绑定到其他管理员账号。
      </p>
      <el-table :data="bindings" border stripe v-loading="bindingsLoading" size="small">
        <el-table-column label="人员" min-width="130">
          <template #default="{ row }">{{ row.person_name || "未登记" }}</template>
        </el-table-column>
        <el-table-column label="手机号" width="130">
          <template #default="{ row }">{{ row.person_phone || "—" }}</template>
        </el-table-column>
        <el-table-column label="绑定时间" width="150">
          <template #default="{ row }">{{ formatTime(row.bound_at) }}</template>
        </el-table-column>
        <el-table-column label="OpenID" min-width="160">
          <template #default="{ row }">
            <span class="openid">{{ row.wx_openid }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" @click="unbindWxBinding(row)">解绑</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="bindingsVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import http from "../api/http";

const router = useRouter();
const loading = ref(false);
const saving = ref(false);
const rows = ref([]);
const allBrigades = ref([]);

const createVisible = ref(false);
const createForm = reactive({
  username: "",
  password: "",
  role: "brigade",
  brigade_id: null,
});

const editVisible = ref(false);
const editing = ref(null);
const editForm = reactive({
  role: "brigade",
  brigade_id: null,
  is_active: true,
});

const pwdVisible = ref(false);
const pwdUserId = ref(null);
const pwdForm = reactive({ new_password: "" });

const bindCodeVisible = ref(false);
const bindCodeUser = ref(null);
const bindCodeData = ref(null);
const bindingsVisible = ref(false);
const bindingsUser = ref(null);
const bindings = ref([]);
const bindingsLoading = ref(false);

function formatTime(iso) {
  if (!iso) return "";
  return String(iso).replace("T", " ").slice(0, 16);
}

async function ensureDetachment() {
  const { data: me } = await http.get("/api/admin/me");
  if (me.role !== "detachment") {
    ElMessage.warning("仅支队管理员可管理账号权限");
    router.replace("/orgs");
    return false;
  }
  return true;
}

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/api/admin/accounts");
    rows.value = data;
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  Object.assign(createForm, {
    username: "",
    password: "",
    role: "brigade",
    brigade_id: allBrigades.value[0]?.id ?? null,
  });
  createVisible.value = true;
}

async function submitCreate() {
  if (!createForm.username.trim() || createForm.password.length < 6) {
    ElMessage.warning("用户名与密码（至少6位）必填");
    return;
  }
  if (createForm.role === "brigade" && !createForm.brigade_id) {
    ElMessage.warning("请选择所属大队");
    return;
  }
  saving.value = true;
  try {
    await http.post("/api/admin/accounts", {
      username: createForm.username.trim(),
      password: createForm.password,
      role: createForm.role,
      brigade_id: createForm.role === "brigade" ? createForm.brigade_id : null,
    });
    ElMessage.success("已创建");
    createVisible.value = false;
    await load();
  } catch (e) {
    console.error(e);
  } finally {
    saving.value = false;
  }
}

function openEdit(row) {
  editing.value = row;
  editForm.role = row.role;
  editForm.brigade_id = row.brigade_id || allBrigades.value[0]?.id;
  editForm.is_active = row.is_active;
  editVisible.value = true;
}

async function submitEdit() {
  if (editForm.role === "brigade" && !editForm.brigade_id) {
    ElMessage.warning("大队账号必须选择所属大队");
    return;
  }
  saving.value = true;
  try {
    await http.patch(`/api/admin/accounts/${editing.value.id}`, {
      role: editForm.role,
      brigade_id: editForm.role === "brigade" ? editForm.brigade_id : null,
      is_active: editForm.is_active,
    });
    ElMessage.success("已保存");
    editVisible.value = false;
    await load();
  } catch (e) {
    console.error(e);
  } finally {
    saving.value = false;
  }
}

function openPwd(row) {
  pwdUserId.value = row.id;
  pwdForm.new_password = "";
  pwdVisible.value = true;
}

async function submitPwd() {
  if (pwdForm.new_password.length < 6) {
    ElMessage.warning("新密码至少6位");
    return;
  }
  saving.value = true;
  try {
    await http.post(`/api/admin/accounts/${pwdUserId.value}/password`, {
      new_password: pwdForm.new_password,
    });
    ElMessage.success("密码已更新");
    pwdVisible.value = false;
  } catch (e) {
    console.error(e);
  } finally {
    saving.value = false;
  }
}

async function genBindCode(row) {
  try {
    const { data } = await http.post(`/api/admin/accounts/${row.id}/wx-bind-code`);
    bindCodeUser.value = row;
    bindCodeData.value = data;
    bindCodeVisible.value = true;
  } catch (e) {
    console.error(e);
  }
}

async function openBindings(row) {
  bindingsUser.value = row;
  bindingsVisible.value = true;
  await loadBindings();
}

async function loadBindings() {
  if (!bindingsUser.value) return;
  bindingsLoading.value = true;
  try {
    const { data } = await http.get(`/api/admin/accounts/${bindingsUser.value.id}/wx-bindings`);
    bindings.value = data || [];
  } catch (e) {
    console.error(e);
    bindings.value = [];
  } finally {
    bindingsLoading.value = false;
  }
}

async function unbindWxBinding(binding) {
  try {
    const label = binding.person_name || binding.person_phone || binding.wx_openid;
    await ElMessageBox.confirm(`确定解除「${label}」的小程序微信绑定？`, "解除绑定", {
      type: "warning",
    });
    await http.delete(`/api/admin/accounts/${bindingsUser.value.id}/wx-bindings/${binding.id}`);
    ElMessage.success("已解除绑定");
    await loadBindings();
    await load();
  } catch (e) {
    if (e !== "cancel") console.error(e);
  }
}

onMounted(async () => {
  if (!(await ensureDetachment())) return;
  const { data } = await http.get("/api/admin/brigades");
  allBrigades.value = data;
  await load();
});
</script>

<style scoped>
.page {
  background: #fff;
  padding: 20px 24px;
  border-radius: 8px;
  min-height: 400px;
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
.bind-time {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}
.bind-code-box {
  text-align: center;
  padding: 12px 0;
}
.bind-code {
  font-size: 36px;
  letter-spacing: 8px;
  font-weight: 700;
  color: #1a237e;
}
.bind-expire {
  margin-top: 12px;
  color: #666;
  font-size: 13px;
}
.openid {
  display: inline-block;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: bottom;
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  color: #666;
}
</style>
