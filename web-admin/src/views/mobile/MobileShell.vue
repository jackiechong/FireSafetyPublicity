<template>
  <div class="m-shell">
    <header class="m-top">
      <div class="m-top__inner">
        <div class="m-brand">
          <span class="m-brand__mark"><AppIcon name="flame" :size="17" /></span>
          <span class="m-brand__text">
            <b>葫芦岛消防</b>
            <em>培训管理平台</em>
          </span>
        </div>
        <div class="m-top__actions">
          <button class="m-textbtn" type="button" @click="goDesktop">电脑版</button>
          <span class="m-top__sep" aria-hidden="true"></span>
          <button class="m-textbtn" type="button" @click="logout">退出</button>
        </div>
      </div>
    </header>

    <main class="m-main">
      <router-view />
    </main>

    <nav class="m-tabbar" aria-label="移动端导航">
      <div class="m-seg">
        <router-link to="/m" class="m-seg__item" exact-active-class="is-on">
          <AppIcon name="chart" :size="16" />
          <span>数据看板</span>
        </router-link>
        <router-link to="/m/admin" class="m-seg__item" exact-active-class="is-on">
          <AppIcon name="list" :size="16" />
          <span>培训管理</span>
        </router-link>
      </div>
    </nav>
  </div>
</template>

<script setup>
import { useRouter } from "vue-router";
import AppIcon from "../../components/AppIcon.vue";
import { clearToken } from "../../utils/auth";

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
  clearToken();
  router.push("/login");
}
</script>

<style scoped>
.m-shell {
  min-height: 100vh;
  background: var(--bg);
  color: var(--ink-900);
  padding-bottom: calc(88px + env(safe-area-inset-bottom, 0px));
}

/* ---------- 顶栏：品牌深海军蓝 ---------- */
.m-top {
  position: sticky;
  top: 0;
  z-index: 20;
  background: var(--surface-nav);
  color: #fff;
  padding-top: env(safe-area-inset-top, 0px);
  border-bottom: 1px solid var(--surface-nav-2);
  box-shadow: 0 8px 20px -16px rgba(11, 27, 43, 0.65);
}
.m-top__inner {
  max-width: 640px;
  margin: 0 auto;
  min-height: 52px;
  padding: 4px 10px 4px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.m-brand {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}
.m-brand__mark {
  flex: none;
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  color: var(--fire-100);
}
.m-brand__text {
  min-width: 0;
  line-height: 1.2;
}
.m-brand__text b {
  display: block;
  font-size: var(--fs-14);
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #fff;
  white-space: nowrap;
}
.m-brand__text em {
  display: block;
  margin-top: 2px;
  font-style: normal;
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--ink-300);
  white-space: nowrap;
}
.m-top__actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 2px;
  flex: none;
}
.m-top__sep {
  width: 1px;
  height: 14px;
  background: rgba(255, 255, 255, 0.18);
}
.m-textbtn {
  height: 44px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: var(--r-md);
  background: transparent;
  color: var(--line);
  font-size: var(--fs-13);
  cursor: pointer;
  transition: background var(--t-fast), color var(--t-fast);
}
.m-textbtn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}
.m-textbtn:active {
  background: rgba(255, 255, 255, 0.16);
}

/* ---------- 内容区 ---------- */
.m-main {
  max-width: 640px;
  margin: 0 auto;
  padding: 14px 14px 20px;
  min-width: 0;
}

/* ---------- 底部 segmented 标签 ---------- */
.m-tabbar {
  position: fixed;
  left: 50%;
  bottom: 0;
  transform: translateX(-50%);
  z-index: 20;
  width: 100%;
  max-width: 640px;
  padding: 8px 12px calc(8px + env(safe-area-inset-bottom, 0px));
  background: var(--surface);
  border-top: 1px solid var(--line);
  box-shadow: 0 -10px 26px -20px rgba(11, 27, 43, 0.55);
}
.m-seg {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3px;
  padding: 3px;
  background: var(--surface-3);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
}
.m-seg__item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  height: 44px;
  border-radius: var(--r-sm);
  color: var(--ink-500);
  font-size: var(--fs-13);
  font-weight: 500;
  text-decoration: none;
  transition: background var(--t-fast), color var(--t-fast), box-shadow var(--t-fast);
}
.m-seg__item svg {
  width: 16px;
  height: 16px;
}
.m-seg__item:hover {
  color: var(--ink-800);
}
.m-seg__item.is-on {
  background: var(--surface);
  color: var(--ink-900);
  font-weight: 600;
  box-shadow: inset 0 -3px 0 var(--fire-500), 0 1px 2px rgba(11, 27, 43, 0.1);
}
.m-seg__item.is-on svg {
  color: var(--fire-500);
}
</style>
