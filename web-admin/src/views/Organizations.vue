<template>
  <div class="page">
    <h2>单位录入</h2>
    <el-form :inline="true" class="toolbar">
      <el-form-item label="关键词">
        <el-input v-model="keyword" placeholder="名称检索" clearable style="width: 200px" @keyup.enter="load" />
      </el-form-item>
      <el-form-item label="区县">
        <el-select v-model="filterDistrict" clearable placeholder="全部" style="width: 140px">
          <el-option v-for="d in districts" :key="d.id" :label="d.name" :value="d.id" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="load">查询</el-button>
        <el-button @click="openDialog()">新增单位</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="rows" border stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="名称" min-width="180" />
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          {{ orgTypeName(row.org_type) }}
        </template>
      </el-table-column>
      <el-table-column label="大队" width="120">
        <template #default="{ row }">{{ brigadeName(row.brigade_id) }}</template>
      </el-table-column>
      <el-table-column label="区县" width="100">
        <template #default="{ row }">{{ districtName(row.district_id) }}</template>
      </el-table-column>
      <el-table-column prop="contact_name" label="联系人" width="100" />
      <el-table-column prop="contact_phone" label="联系电话" width="120" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editing?.id ? '编辑单位' : '新增单位'" width="520px" destroy-on-close>
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="form.org_type" style="width: 100%">
            <el-option v-for="t in orgTypes" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属大队" required>
          <el-select v-model="form.brigade_id" style="width: 100%">
            <el-option v-for="b in brigades" :key="b.id" :label="b.name" :value="b.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="区县" required>
          <el-select v-model="form.district_id" style="width: 100%">
            <el-option v-for="d in districts" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="form.contact_name" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="form.contact_phone" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
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
const rows = ref([]);
const brigades = ref([]);
const districts = ref([]);
const keyword = ref("");
const filterDistrict = ref();
const dialogVisible = ref(false);
const editing = ref(null);
const orgTypes = [
  { value: "emergency", label: "应急" },
  { value: "education", label: "教育" },
  { value: "civil_affairs", label: "民政" },
  { value: "culture_tourism", label: "文旅" },
  { value: "health", label: "卫建" },
  { value: "commerce", label: "商务" },
  { value: "industry_agriculture", label: "工农业农村" },
  { value: "development_reform", label: "发改" },
  { value: "other_department", label: "其他部门" },
];

const form = reactive({
  name: "",
  org_type: "other_department",
  brigade_id: null,
  district_id: null,
  contact_name: "",
  contact_phone: "",
  remark: "",
});

function brigadeName(id) {
  return brigades.value.find((b) => b.id === id)?.name || id;
}
function districtName(id) {
  return districts.value.find((d) => d.id === id)?.name || id;
}
function orgTypeName(value) {
  return orgTypes.find((t) => t.value === value)?.label || "其他部门";
}

async function loadMeta() {
  const [b, d] = await Promise.all([http.get("/api/admin/brigades"), http.get("/api/admin/districts")]);
  brigades.value = b.data;
  districts.value = d.data;
}

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/api/admin/organizations", {
      params: {
        q: keyword.value || undefined,
        district_id: filterDistrict.value || undefined,
      },
    });
    rows.value = data;
  } finally {
    loading.value = false;
  }
}

function openDialog(row) {
  editing.value = row || null;
  if (row) {
    Object.assign(form, {
      name: row.name,
      org_type: row.org_type,
      brigade_id: row.brigade_id,
      district_id: row.district_id,
      contact_name: row.contact_name || "",
      contact_phone: row.contact_phone || "",
      remark: row.remark || "",
    });
  } else {
    Object.assign(form, {
      name: "",
      org_type: "other_department",
      brigade_id: brigades.value[0]?.id ?? null,
      district_id: districts.value[0]?.id ?? null,
      contact_name: "",
      contact_phone: "",
      remark: "",
    });
  }
  dialogVisible.value = true;
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning("请填写名称");
    return;
  }
  saving.value = true;
  try {
    if (editing.value?.id) {
      await http.patch(`/api/admin/organizations/${editing.value.id}`, form);
      ElMessage.success("已保存");
    } else {
      await http.post("/api/admin/organizations", form);
      ElMessage.success("已创建");
    }
    dialogVisible.value = false;
    await load();
  } catch (e) {
    console.error(e);
  } finally {
    saving.value = false;
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`确定删除「${row.name}」？`, "确认", { type: "warning" });
  await http.delete(`/api/admin/organizations/${row.id}`);
  ElMessage.success("已删除");
  await load();
}

onMounted(async () => {
  await loadMeta();
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
.toolbar {
  margin-bottom: 12px;
}
h2 {
  margin: 0 0 16px;
  font-size: 1.25rem;
}
</style>
