<template>
  <div>
    <div class="page-head">
      <div class="page-head__main">
        <div class="eyebrow">内容与系统</div>
        <h1 class="page-title">账号权限</h1>
        <p class="page-desc">维护支队与大队管理员的登录账号、数据权限与小程序微信绑定；仅支队账号可进入本页</p>
      </div>
      <div class="page-actions">
        <button class="btn btn--primary" @click="openCreate">
          <AppIcon name="plus" :size="15" />新建管理员
        </button>
      </div>
    </div>

    <div class="filterbar">
      <div class="field" style="flex: 1; min-width: 220px">
        <label for="f-kw">用户名</label>
        <div class="search-inline">
          <AppIcon name="search" :size="15" />
          <input
            id="f-kw"
            v-model="searchQ"
            class="input"
            placeholder="按用户名筛选"
            @keyup.enter="applyFilters"
          />
        </div>
      </div>
      <div class="field" style="width: 150px">
        <label for="f-role">角色</label>
        <div class="select">
          <select id="f-role" v-model="roleFilter">
            <option value="">全部角色</option>
            <option value="detachment">支队</option>
            <option value="brigade">大队</option>
          </select>
        </div>
      </div>
      <div class="field" style="width: 150px">
        <label for="f-state">状态</label>
        <div class="select">
          <select id="f-state" v-model="stateFilter">
            <option value="">全部状态</option>
            <option value="active">启用</option>
            <option value="inactive">停用</option>
          </select>
        </div>
      </div>
      <div style="display: flex; gap: 8px; margin-left: auto">
        <button class="btn btn--primary" @click="applyFilters">查询</button>
        <button class="btn btn--ghost" @click="resetFilters">重置</button>
      </div>
    </div>

    <div v-if="hasFilters" class="chips">
      <span v-if="appliedQ" class="chip">
        <b>用户名</b>{{ appliedQ }}
        <button type="button" aria-label="移除用户名筛选" @click="clearKeyword">
          <AppIcon name="x" :size="11" />
        </button>
      </span>
      <span v-if="appliedRole" class="chip">
        <b>角色</b>{{ roleLabel(appliedRole) }}
        <button type="button" aria-label="移除角色筛选" @click="clearRole">
          <AppIcon name="x" :size="11" />
        </button>
      </span>
      <span v-if="appliedState" class="chip">
        <b>状态</b>{{ stateLabel(appliedState) }}
        <button type="button" aria-label="移除状态筛选" @click="clearState">
          <AppIcon name="x" :size="11" />
        </button>
      </span>
      <button class="chips__reset" type="button" @click="resetFilters">清除全部</button>
    </div>

    <section class="card">
      <div class="card__head">
        <h3>管理员清单</h3>
        <span class="sub">共 {{ filteredRows.length }} 个账号</span>
        <div class="grow"></div>
        <span class="badge badge--ok">启用 {{ activeCount }}</span>
        <span class="badge badge--off">停用 {{ inactiveCount }}</span>
      </div>

      <div v-loading="loading" class="tablewrap">
        <table class="tb">
          <thead>
            <tr>
              <th style="width: 64px">ID</th>
              <th>用户名</th>
              <th style="width: 130px">角色</th>
              <th style="width: 150px">所属大队</th>
              <th style="width: 210px">小程序绑定</th>
              <th style="width: 96px">状态</th>
              <th class="col-actions" style="width: 110px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in pagedRows" :key="row.id">
              <td class="num" style="color: var(--ink-400)">{{ row.id }}</td>
              <td>
                <button class="cell-main linkbtn" style="padding: 0" @click="openView(row)">
                  {{ row.username }}
                </button>
              </td>
              <td>{{ roleLabel(row.role) }}</td>
              <td>{{ row.brigade_name || "—" }}</td>
              <td>
                <span class="badge" :class="row.wx_bound ? 'badge--ok' : 'badge--off'">
                  {{ row.wx_bound ? "已绑定 " + (row.wx_binding_count || 0) + " 个微信" : "未绑定" }}
                </span>
                <span v-if="row.wx_bound && row.wx_bound_at" class="cell-sub">
                  首次 {{ formatTime(row.wx_bound_at) }}
                </span>
              </td>
              <td>
                <span class="badge" :class="row.is_active ? 'badge--ok' : 'badge--off'">
                  {{ row.is_active ? "启用" : "停用" }}
                </span>
              </td>
              <td class="col-actions">
                <div class="rowact" style="display: inline-flex; align-items: center; gap: 2px">
                  <button class="linkbtn" @click="openView(row)">查看</button>
                  <el-dropdown trigger="click" @command="(cmd) => onRowCommand(cmd, row)">
                    <button class="iconbtn" aria-label="更多操作"><AppIcon name="more" :size="16" /></button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="edit">调整权限</el-dropdown-item>
                        <el-dropdown-item command="pwd">重置密码</el-dropdown-item>
                        <el-dropdown-item command="bindcode" :disabled="!row.is_active">
                          生成绑定码
                        </el-dropdown-item>
                        <el-dropdown-item v-if="row.wx_bound" command="unbind" divided class="is-danger">
                          解绑微信
                        </el-dropdown-item>
                        <el-dropdown-item command="status" divided>
                          {{ row.is_active ? "停用账号" : "启用账号" }}
                        </el-dropdown-item>
                        <el-dropdown-item
                          v-if="row.username !== 'admin'"
                          command="delete"
                          divided
                          class="is-danger"
                        >
                          删除账号
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </td>
            </tr>
            <tr v-if="!filteredRows.length && !loading">
              <td colspan="7">
                <div class="empty">
                  <div class="empty__art"><AppIcon name="users" :size="26" /></div>
                  <h4>{{ hasFilters ? "没有匹配的管理员账号" : "还没有管理员账号" }}</h4>
                  <p>
                    {{
                      hasFilters
                        ? "换个用户名或角色试试，或清除筛选条件。"
                        : "创建第一个管理员账号，开始分配数据权限。"
                    }}
                  </p>
                  <button v-if="hasFilters" class="btn btn--ghost btn--sm" @click="resetFilters">
                    清除筛选
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pager">
        <span>共 {{ filteredRows.length }} 条 · 每页 {{ pageSize }} 条</span>
        <el-pagination
          :current-page="safePage"
          v-model:page-size="pageSize"
          :total="filteredRows.length"
          :page-sizes="[20, 50, 100]"
          layout="sizes, prev, pager, next, jumper"
          background
          @current-change="changePage"
          @size-change="changePageSize"
        />
      </div>
    </section>

    <!-- 账号详情 -->
    <el-drawer v-model="viewVisible" size="520px" :with-header="false" destroy-on-close class="form-drawer">
      <div class="drawer-shell">
        <div class="drawer__head">
          <div class="grow">
            <h3>账号详情</h3>
            <p>{{ viewUser?.username }}</p>
          </div>
          <button class="iconbtn" aria-label="关闭" @click="viewVisible = false">
            <AppIcon name="x" :size="16" />
          </button>
        </div>
        <div class="drawer__body">
          <div class="fieldset">
            <div class="fieldset__title">账号信息</div>
            <div class="formgrid">
              <div class="field">
                <label>用户名</label>
                <div class="ro">{{ viewUser?.username }}</div>
              </div>
              <div class="field">
                <label>账号 ID</label>
                <div class="ro num">#{{ viewUser?.id }}</div>
              </div>
              <div class="field">
                <label>角色</label>
                <div class="ro">{{ roleLabel(viewUser?.role) }}</div>
              </div>
              <div class="field">
                <label>所属大队</label>
                <div class="ro">{{ viewUser?.brigade_name || "—" }}</div>
              </div>
            </div>
          </div>
          <div class="fieldset">
            <div class="fieldset__title">状态与绑定</div>
            <div class="formgrid">
              <div class="field">
                <label>账号状态</label>
                <div class="ro">
                  <span class="badge" :class="viewUser?.is_active ? 'badge--ok' : 'badge--off'">
                    {{ viewUser?.is_active ? "启用" : "停用" }}
                  </span>
                </div>
              </div>
              <div class="field">
                <label>小程序绑定</label>
                <div class="ro">
                  <span class="badge" :class="viewUser?.wx_bound ? 'badge--ok' : 'badge--off'">
                    {{
                      viewUser?.wx_bound
                        ? "已绑定 " + (viewUser?.wx_binding_count || 0) + " 个微信"
                        : "未绑定"
                    }}
                  </span>
                </div>
              </div>
              <div class="field span-2">
                <label>首次绑定时间</label>
                <div class="ro">{{ viewUser?.wx_bound_at ? formatTime(viewUser.wx_bound_at) : "—" }}</div>
              </div>
            </div>
          </div>
        </div>
        <div class="drawer__foot">
          <div class="grow"></div>
          <button class="btn btn--ghost" @click="viewVisible = false">关闭</button>
        </div>
      </div>
    </el-drawer>

    <!-- 新建管理员 -->
    <el-drawer v-model="createVisible" size="520px" :with-header="false" destroy-on-close class="form-drawer">
      <div class="drawer-shell">
        <div class="drawer__head">
          <div class="grow">
            <h3>新建管理员</h3>
            <p>账号创建后即可登录后台，权限范围按角色生效</p>
          </div>
          <button class="iconbtn" aria-label="关闭" @click="createVisible = false">
            <AppIcon name="x" :size="16" />
          </button>
        </div>
        <div class="drawer__body">
          <el-form :model="createForm" label-position="top">
            <div class="fieldset">
              <div class="fieldset__title">登录账号</div>
              <div class="formgrid">
                <div class="field">
                  <label>用户名<span class="req">*</span></label>
                  <el-input v-model="createForm.username" autocomplete="off" placeholder="如：lianshan02" />
                </div>
                <div class="field">
                  <label>初始密码<span class="req">*</span></label>
                  <el-input
                    v-model="createForm.password"
                    type="password"
                    show-password
                    autocomplete="new-password"
                    placeholder="至少 6 位"
                  />
                </div>
              </div>
            </div>

            <div class="fieldset">
              <div class="fieldset__title">权限范围</div>
              <div class="formgrid">
                <div class="field span-2">
                  <label>角色<span class="req">*</span></label>
                  <el-radio-group v-model="createForm.role">
                    <el-radio value="detachment">支队（全市）</el-radio>
                    <el-radio value="brigade">大队</el-radio>
                  </el-radio-group>
                  <div class="hint">支队账号可管理全市数据与账号；大队账号仅能管理本单位数据。</div>
                </div>
                <div v-if="createForm.role === 'brigade'" class="field span-2">
                  <label>所属大队<span class="req">*</span></label>
                  <el-select v-model="createForm.brigade_id" placeholder="请选择大队" style="width: 100%">
                    <el-option v-for="b in allBrigades" :key="b.id" :label="b.name" :value="b.id" />
                  </el-select>
                </div>
              </div>
            </div>
          </el-form>
        </div>
        <div class="drawer__foot">
          <span class="hint" style="margin: 0">账号与密码由管理员线下交接</span>
          <div class="grow"></div>
          <button class="btn btn--ghost" @click="createVisible = false">取消</button>
          <button class="btn btn--primary" :disabled="saving" @click="submitCreate">
            {{ saving ? "创建中…" : "创建账号" }}
          </button>
        </div>
      </div>
    </el-drawer>

    <!-- 调整权限 -->
    <el-drawer v-model="editVisible" size="520px" :with-header="false" destroy-on-close class="form-drawer">
      <div class="drawer-shell">
        <div class="drawer__head">
          <div class="grow">
            <h3>调整权限</h3>
            <p>保存后立即生效，已登录的会话按新权限重新校验</p>
          </div>
          <button class="iconbtn" aria-label="关闭" @click="editVisible = false">
            <AppIcon name="x" :size="16" />
          </button>
        </div>
        <div class="drawer__body">
          <el-form label-position="top">
            <div class="fieldset">
              <div class="fieldset__title">账号信息</div>
              <div class="formgrid">
                <div class="field span-2">
                  <label>用户名</label>
                  <div class="ro">{{ editing?.username }}</div>
                </div>
              </div>
            </div>
            <div class="fieldset">
              <div class="fieldset__title">权限与状态</div>
              <div class="formgrid">
                <div class="field span-2">
                  <label>角色</label>
                  <el-radio-group v-model="editForm.role">
                    <el-radio value="detachment">支队（全市）</el-radio>
                    <el-radio value="brigade">大队</el-radio>
                  </el-radio-group>
                </div>
                <div v-if="editForm.role === 'brigade'" class="field span-2">
                  <label>所属大队</label>
                  <el-select v-model="editForm.brigade_id" placeholder="请选择大队" style="width: 100%">
                    <el-option v-for="b in allBrigades" :key="b.id" :label="b.name" :value="b.id" />
                  </el-select>
                </div>
                <div class="field span-2">
                  <label>账号状态</label>
                  <el-switch v-model="editForm.is_active" active-text="启用" inactive-text="停用" />
                  <div class="hint">停用后该账号无法登录后台，历史数据与其他账号不受影响。</div>
                </div>
              </div>
            </div>
          </el-form>
        </div>
        <div class="drawer__foot">
          <div class="grow"></div>
          <button class="btn btn--ghost" @click="editVisible = false">取消</button>
          <button class="btn btn--primary" :disabled="saving" @click="submitEdit">
            {{ saving ? "保存中…" : "保存修改" }}
          </button>
        </div>
      </div>
    </el-drawer>

    <!-- 重置密码 -->
    <el-drawer v-model="pwdVisible" size="520px" :with-header="false" destroy-on-close class="form-drawer">
      <div class="drawer-shell">
        <div class="drawer__head">
          <div class="grow">
            <h3>重置密码</h3>
            <p>为该管理员设置新的登录密码</p>
          </div>
          <button class="iconbtn" aria-label="关闭" @click="pwdVisible = false">
            <AppIcon name="x" :size="16" />
          </button>
        </div>
        <div class="drawer__body">
          <el-form label-position="top">
            <div class="fieldset">
              <div class="fieldset__title">账号</div>
              <div class="formgrid">
                <div class="field span-2">
                  <label>管理员账号</label>
                  <div class="ro">{{ pwdTarget?.username || "—" }}</div>
                </div>
              </div>
            </div>
            <div class="fieldset">
              <div class="fieldset__title">新密码</div>
              <div class="formgrid">
                <div class="field span-2">
                  <label>新密码<span class="req">*</span></label>
                  <el-input
                    v-model="pwdForm.new_password"
                    type="password"
                    show-password
                    autocomplete="new-password"
                    placeholder="至少 6 位"
                  />
                  <div class="hint">保存后旧密码立即失效，请把新密码告知该管理员。</div>
                </div>
              </div>
            </div>
          </el-form>
        </div>
        <div class="drawer__foot">
          <div class="grow"></div>
          <button class="btn btn--ghost" @click="pwdVisible = false">取消</button>
          <button class="btn btn--primary" :disabled="saving" @click="submitPwd">
            {{ saving ? "保存中…" : "保存新密码" }}
          </button>
        </div>
      </div>
    </el-drawer>

    <!-- 小程序绑定码 -->
    <el-drawer
      v-model="bindCodeVisible"
      size="520px"
      :with-header="false"
      destroy-on-close
      class="form-drawer"
    >
      <div class="drawer-shell">
        <div class="drawer__head">
          <div class="grow">
            <h3>小程序绑定码</h3>
            <p>一次性使用，过期后重新生成</p>
          </div>
          <button class="iconbtn" aria-label="关闭" @click="bindCodeVisible = false">
            <AppIcon name="x" :size="16" />
          </button>
        </div>
        <div class="drawer__body">
          <div class="notice">
            <AppIcon name="qr" :size="17" />
            <div>
              <b>在小程序中完成绑定</b>
              <span>
                让管理员 {{ bindCodeUser?.username }} 打开小程序「身份绑定」页，输入下面的 8 位数字。
              </span>
            </div>
          </div>
          <div v-if="bindCodeData" class="codebox">
            <div class="codebox__value">{{ bindCodeData.code }}</div>
            <p class="codebox__hint">
              有效期 {{ bindCodeData.expires_in_minutes }} 分钟，至 {{ formatTime(bindCodeData.expires_at) }}
            </p>
          </div>
        </div>
        <div class="drawer__foot">
          <span class="hint" style="margin: 0">绑定码仅可使用一次</span>
          <div class="grow"></div>
          <button class="btn btn--primary" @click="bindCodeVisible = false">知道了</button>
        </div>
      </div>
    </el-drawer>

    <!-- 已绑定微信 -->
    <el-drawer
      v-model="bindingsVisible"
      size="560px"
      :with-header="false"
      destroy-on-close
      class="form-drawer"
    >
      <div class="drawer-shell">
        <div class="drawer__head">
          <div class="grow">
            <h3>微信绑定</h3>
            <p>{{ bindingsUser?.username }} · 共 {{ bindings.length }} 个微信</p>
          </div>
          <button class="iconbtn" aria-label="关闭" @click="bindingsVisible = false">
            <AppIcon name="x" :size="16" />
          </button>
        </div>
        <div class="drawer__body">
          <p class="hint" style="margin: 0 0 14px">
            管理员账号可同时绑定多个微信；同一个微信不能绑定到其他管理员账号。
          </p>
          <div v-loading="bindingsLoading" class="tablewrap">
            <table class="tb">
              <thead>
                <tr>
                  <th>人员</th>
                  <th style="width: 120px">绑定时间</th>
                  <th style="width: 170px">OpenID</th>
                  <th class="col-actions" style="width: 70px">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="binding in bindings" :key="binding.id">
                  <td>
                    <span class="cell-main">{{ binding.person_name || "未登记" }}</span>
                    <span class="cell-sub">{{ binding.person_phone || "—" }}</span>
                  </td>
                  <td class="num">{{ formatTime(binding.bound_at) }}</td>
                  <td>
                    <span class="openid" :title="binding.wx_openid">{{ binding.wx_openid }}</span>
                  </td>
                  <td class="col-actions">
                    <button class="linkbtn is-danger" @click="unbindWxBinding(binding)">解绑</button>
                  </td>
                </tr>
                <tr v-if="!bindings.length && !bindingsLoading">
                  <td colspan="4">
                    <div class="empty">
                      <div class="empty__art"><AppIcon name="phone" :size="26" /></div>
                      <h4>还没有绑定微信</h4>
                      <p>生成绑定码后，让管理员在小程序「身份绑定」页输入即可。</p>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="drawer__foot">
          <div class="grow"></div>
          <button class="btn btn--ghost" @click="bindingsVisible = false">关闭</button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import http from "../api/http";
import AppIcon from "../components/AppIcon.vue";

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

// —— 展示层：筛选、分页与只读详情，不涉及任何接口调用 ——
const searchQ = ref("");
const roleFilter = ref("");
const stateFilter = ref("");
const appliedQ = ref("");
const appliedRole = ref("");
const appliedState = ref("");
const page = ref(1);
const pageSize = ref(20);
const viewVisible = ref(false);
const viewUser = ref(null);

const filteredRows = computed(() => {
  const kw = appliedQ.value.trim().toLowerCase();
  return rows.value.filter((row) => {
    if (kw && !String(row.username || "").toLowerCase().includes(kw)) return false;
    if (appliedRole.value && row.role !== appliedRole.value) return false;
    if (appliedState.value === "active" && !row.is_active) return false;
    if (appliedState.value === "inactive" && row.is_active) return false;
    return true;
  });
});

const totalPages = computed(() => Math.max(1, Math.ceil(filteredRows.value.length / pageSize.value)));
const safePage = computed(() => Math.min(page.value, totalPages.value));
const pagedRows = computed(() => {
  const start = (safePage.value - 1) * pageSize.value;
  return filteredRows.value.slice(start, start + pageSize.value);
});

const activeCount = computed(() => rows.value.filter((row) => row.is_active).length);
const inactiveCount = computed(() => rows.value.filter((row) => !row.is_active).length);
const hasFilters = computed(() => Boolean(appliedQ.value || appliedRole.value || appliedState.value));
const pwdTarget = computed(() => rows.value.find((row) => row.id === pwdUserId.value) || null);

function roleLabel(role) {
  if (!role) return "—";
  return role === "detachment" ? "支队（全市）" : "大队";
}

function stateLabel(value) {
  return value === "active" ? "启用" : "停用";
}

function applyFilters() {
  appliedQ.value = searchQ.value;
  appliedRole.value = roleFilter.value;
  appliedState.value = stateFilter.value;
  page.value = 1;
}

function clearKeyword() {
  searchQ.value = "";
  appliedQ.value = "";
  page.value = 1;
}

function clearRole() {
  roleFilter.value = "";
  appliedRole.value = "";
  page.value = 1;
}

function clearState() {
  stateFilter.value = "";
  appliedState.value = "";
  page.value = 1;
}

function resetFilters() {
  searchQ.value = "";
  roleFilter.value = "";
  stateFilter.value = "";
  appliedQ.value = "";
  appliedRole.value = "";
  appliedState.value = "";
  page.value = 1;
}

function changePage(nextPage) {
  page.value = nextPage;
}

function changePageSize(size) {
  pageSize.value = size;
  page.value = 1;
}

function openView(row) {
  viewUser.value = row;
  viewVisible.value = true;
}

function onRowCommand(cmd, row) {
  if (cmd === "edit" || cmd === "status") openEdit(row);
  else if (cmd === "pwd") openPwd(row);
  else if (cmd === "bindcode") genBindCode(row);
  else if (cmd === "unbind") openBindings(row);
  else if (cmd === "delete") removeAccount(row);
}

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

async function removeAccount(row) {
  if (row.username === "admin") return;
  try {
    await ElMessageBox.confirm(
      `确定删除管理员账号“${row.username}”吗？该账号的小程序微信绑定也将一并解除。`,
      "删除管理员",
      { type: "warning", confirmButtonText: "删除", cancelButtonText: "取消" }
    );
    await http.delete(`/api/admin/accounts/${row.id}`);
    ElMessage.success("账号已删除");
    await load();
  } catch (e) {
    if (e !== "cancel") ElMessage.error(e?.response?.data?.detail || "删除失败");
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
.drawer-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
}
:deep(.form-drawer .el-drawer__body) {
  padding: 0;
  overflow: hidden;
}
.ro {
  font-size: var(--fs-13);
  color: var(--ink-900);
  padding-top: 8px;
  min-height: 22px;
}
.codebox {
  margin-top: var(--s5);
  padding: 26px 16px;
  text-align: center;
  background: var(--surface-2);
  border: 1px dashed var(--line-strong);
  border-radius: var(--r-lg);
}
.codebox__value {
  font-family: var(--font-num);
  font-variant-numeric: tabular-nums;
  font-size: 34px;
  font-weight: 600;
  letter-spacing: 0.18em;
  color: var(--brand-800);
}
.codebox__hint {
  margin-top: 10px;
  font-size: var(--fs-12);
  color: var(--ink-500);
}
.openid {
  display: inline-block;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
  font-family: var(--font-num);
  font-size: var(--fs-12);
  color: var(--ink-500);
}
</style>
