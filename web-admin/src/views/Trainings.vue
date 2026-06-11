<template>
  <div class="page">
    <h2>培训记录</h2>
    <el-button type="primary" @click="openCreate">登记培训</el-button>

    <el-table :data="rows" border stripe v-loading="loading" style="margin-top: 16px">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" label="主题" min-width="160" />
      <el-table-column label="主题分类" min-width="120">
        <template #default="{ row }">{{ topicName(row.topic_id) }}</template>
      </el-table-column>
      <el-table-column label="扫码" width="88" align="center">
        <template #default="{ row }">
          <el-switch
            :model-value="row.is_active !== false"
            @change="(v) => patchTrainingActive(row, v)"
          />
        </template>
      </el-table-column>
      <el-table-column label="大队" width="110">
        <template #default="{ row }">{{ brigadeName(row.brigade_id) }}</template>
      </el-table-column>
      <el-table-column label="单位ID" width="80" prop="organization_id" />
      <el-table-column label="开始时间" width="170">
        <template #default="{ row }">{{ formatTime(row.start_at) }}</template>
      </el-table-column>
      <el-table-column prop="duration_minutes" label="时长(分)" width="100" />
      <el-table-column prop="location" label="地点" min-width="120" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="primary" @click="openAttendance(row)">添加参训人员</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="createVisible" title="登记培训" width="560px" destroy-on-close>
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="主题" required>
          <el-input v-model="createForm.title" />
        </el-form-item>
        <el-form-item label="主题分类">
          <el-select v-model="createForm.topic_id" clearable style="width: 100%">
            <el-option v-for="t in topics" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="大队" required>
          <el-select v-model="createForm.brigade_id" style="width: 100%">
            <el-option v-for="b in brigades" :key="b.id" :label="b.name" :value="b.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="单位" required>
          <el-select
            v-model="createForm.organization_id"
            filterable
            remote
            reserve-keyword
            placeholder="输入关键词联想"
            :remote-method="remoteOrg"
            :loading="orgLoading"
            style="width: 100%"
          >
            <el-option v-for="o in orgOptions" :key="o.id" :label="`${o.name}（${o.district_name}）`" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间" required>
          <el-date-picker v-model="createForm.start_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="时长(分钟)">
          <el-input-number v-model="createForm.duration_minutes" :min="0" />
        </el-form-item>
        <el-form-item label="地点">
          <el-input v-model="createForm.location" />
        </el-form-item>
        <el-form-item label="开放扫码">
          <el-switch v-model="createForm.is_active" active-text="活动场次" inactive-text="不开放" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="createForm.remark" type="textarea" rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="编辑培训" width="560px" destroy-on-close>
      <el-form label-width="100px">
        <el-form-item label="培训名称" required>
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-form-item label="主题分类">
          <el-select v-model="editForm.topic_id" clearable style="width: 100%">
            <el-option v-for="t in topics" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间" required>
          <el-date-picker v-model="editForm.start_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker v-model="editForm.end_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" clearable style="width: 100%" />
        </el-form-item>
        <el-form-item label="时长(分钟)">
          <el-input-number v-model="editForm.duration_minutes" :min="0" />
        </el-form-item>
        <el-form-item label="地点">
          <el-input v-model="editForm.location" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.remark" type="textarea" rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="attVisible" title="添加参训人员（手机号需已在小程序实名）" width="440px">
      <el-form label-width="100px">
        <el-form-item label="培训ID">
          <span>{{ currentSession?.id }}</span>
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="attPhone" maxlength="11" placeholder="与小程序绑定一致" />
        </el-form-item>
        <el-form-item label="本次时长(分)">
          <el-input-number v-model="attDuration" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="attVisible = false">取消</el-button>
        <el-button type="primary" :loading="attSaving" @click="submitAttendance">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import http from "../api/http";

const loading = ref(false);
const saving = ref(false);
const rows = ref([]);
const brigades = ref([]);
const topics = ref([]);
const createVisible = ref(false);
const createForm = reactive({
  title: "",
  topic_id: null,
  brigade_id: null,
  organization_id: null,
  start_at: "",
  duration_minutes: 60,
  location: "",
  remark: "",
  is_active: true,
});

const orgOptions = ref([]);
const orgLoading = ref(false);

const attVisible = ref(false);
const attSaving = ref(false);
const currentSession = ref(null);
const attPhone = ref("");
const attDuration = ref(0);
const editVisible = ref(false);
const editSaving = ref(false);
const editing = ref(null);
const editForm = reactive({
  title: "",
  topic_id: null,
  start_at: "",
  end_at: "",
  duration_minutes: 60,
  location: "",
  remark: "",
});

function brigadeName(id) {
  return brigades.value.find((b) => b.id === id)?.name || id;
}

function topicName(id) {
  return topics.value.find((t) => t.id === id)?.name || "未分类";
}

function formatTime(iso) {
  if (!iso) return "";
  return iso.replace("T", " ").slice(0, 19);
}

async function patchTrainingActive(row, val) {
  try {
    await http.patch(`/api/admin/trainings/${row.id}`, { is_active: val });
    row.is_active = val;
    ElMessage.success(val ? "已设为活动场次" : "已关闭扫码");
  } catch (e) {
    console.error(e);
    ElMessage.error(e?.response?.data?.detail || "更新失败");
    await load();
  }
}

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/api/admin/trainings");
    rows.value = data;
  } finally {
    loading.value = false;
  }
}

async function remoteOrg(q) {
  if (!q) {
    orgOptions.value = [];
    return;
  }
  orgLoading.value = true;
  try {
    const { data } = await http.get("/api/admin/organizations/suggest", { params: { q, limit: 30 } });
    orgOptions.value = data;
  } finally {
    orgLoading.value = false;
  }
}

function openCreate() {
  Object.assign(createForm, {
    title: "",
    topic_id: null,
    brigade_id: brigades.value[0]?.id ?? null,
    organization_id: null,
    start_at: new Date().toISOString().slice(0, 19),
    duration_minutes: 60,
    location: "",
    remark: "",
    is_active: true,
  });
  orgOptions.value = [];
  createVisible.value = true;
}

async function submitCreate() {
  if (!createForm.title.trim() || !createForm.organization_id) {
    ElMessage.warning("请填写主题并选择单位");
    return;
  }
  saving.value = true;
  try {
    await http.post("/api/admin/trainings", createForm);
    ElMessage.success("已登记");
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
  Object.assign(editForm, {
    title: row.title || "",
    topic_id: row.topic_id || null,
    start_at: row.start_at ? row.start_at.slice(0, 19) : "",
    end_at: row.end_at ? row.end_at.slice(0, 19) : "",
    duration_minutes: row.duration_minutes || 0,
    location: row.location || "",
    remark: row.remark || "",
  });
  editVisible.value = true;
}

async function submitEdit() {
  if (!editing.value || !editForm.title.trim() || !editForm.start_at) {
    ElMessage.warning("请填写培训名称和开始时间");
    return;
  }
  editSaving.value = true;
  try {
    await http.patch(`/api/admin/trainings/${editing.value.id}`, {
      title: editForm.title.trim(),
      topic_id: editForm.topic_id || null,
      start_at: editForm.start_at,
      end_at: editForm.end_at || null,
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

function openAttendance(row) {
  currentSession.value = row;
  attPhone.value = "";
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
      duration_minutes: attDuration.value,
    });
    ElMessage.success("已添加");
    attVisible.value = false;
  } catch (e) {
    console.error(e);
  } finally {
    attSaving.value = false;
  }
}

onMounted(async () => {
  const [b, t] = await Promise.all([
    http.get("/api/admin/brigades"),
    http.get("/api/admin/training-topics"),
  ]);
  brigades.value = b.data;
  topics.value = t.data || [];
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
  margin: 0 0 16px;
  font-size: 1.25rem;
}
</style>
