<template>
  <el-container class="layout">
    <el-aside width="220px">
      <div class="brand">消防培训管理</div>
      <el-menu :default-active="active" router background-color="#1a237e" text-color="#e8eaf6" active-text-color="#ffd54f">
        <el-menu-item index="/orgs">单位录入</el-menu-item>
        <el-menu-item index="/trainings">培训记录</el-menu-item>
        <el-menu-item index="/stats">统计数据</el-menu-item>
        <el-menu-item v-if="role === 'detachment'" index="/accounts">账号权限</el-menu-item>
        <el-menu-item index="/m">手机看板</el-menu-item>
      </el-menu>
      <div class="foot">
        <el-button link type="primary" size="small" style="width: 100%; margin-bottom: 8px" @click="goMobileBoard">
          手机数据看板
        </el-button>
        <el-button type="danger" plain size="small" @click="logout">退出登录</el-button>
      </div>
    </el-aside>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import http from "../api/http";

const route = useRoute();
const router = useRouter();
const active = computed(() => route.path);
const role = ref("");

onMounted(async () => {
  try {
    const { data } = await http.get("/api/admin/me");
    role.value = data.role;
  } catch {
    role.value = "";
  }
});

function goMobileBoard() {
  try {
    localStorage.removeItem("prefer_desktop");
  } catch {
    /* ignore */
  }
  router.push("/m");
}

function logout() {
  localStorage.removeItem("admin_token");
  router.push("/login");
}
</script>

<style scoped>
.layout {
  min-height: 100vh;
}
.brand {
  padding: 20px 16px;
  color: #fff;
  font-weight: 600;
  background: #0d1642;
  font-size: 15px;
}
.foot {
  padding: 16px;
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
}
.el-aside {
  position: relative;
  background: #1a237e;
  min-height: 100vh;
}
.el-main {
  background: #f5f7fa;
}
</style>
