<template>
  <div class="m-shell">
    <header class="m-header">
      <div class="m-brand">葫芦岛消防</div>
      <div class="m-actions">
        <el-button link @click="goDesktop">电脑版</el-button>
        <el-button link @click="logout">退出</el-button>
      </div>
    </header>
    <nav class="m-tabs">
      <router-link to="/m" class="m-tab" exact-active-class="m-tab-active">
        数据看板
      </router-link>
      <router-link to="/m/admin" class="m-tab" exact-active-class="m-tab-active">
        培训管理
      </router-link>
    </nav>
    <main class="m-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useRouter } from "vue-router";

const router = useRouter();

function goDesktop() {
  try {
    localStorage.setItem("prefer_desktop", "1");
  } catch {
    /* ignore */
  }
  router.push("/orgs");
}

function logout() {
  localStorage.removeItem("admin_token");
  router.push("/login");
}
</script>

<style scoped>
.m-shell {
  min-height: 100vh;
  background: #f0f2f5;
  padding-bottom: env(safe-area-inset-bottom, 12px);
}
.m-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  padding-top: calc(12px + env(safe-area-inset-top, 0px));
  background: linear-gradient(135deg, #1a237e 0%, #3949ab 100%);
  color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}
.m-brand {
  font-weight: 600;
  font-size: 1.05rem;
}
.m-actions {
  display: flex;
  gap: 4px;
}
.m-actions :deep(.el-button) {
  color: #e8eaf6 !important;
}

.m-tabs {
  position: sticky;
  top: 56px;
  z-index: 9;
  display: flex;
  background: #fff;
  border-bottom: 1px solid #eef0f5;
}
.m-tab {
  flex: 1;
  text-align: center;
  padding: 12px 0;
  text-decoration: none;
  color: #555;
  font-size: 14px;
  border-bottom: 2px solid transparent;
}
.m-tab-active {
  color: #1a237e;
  font-weight: 600;
  border-bottom-color: #3949ab;
}

.m-main {
  padding: 12px;
  max-width: 640px;
  margin: 0 auto;
}
</style>
