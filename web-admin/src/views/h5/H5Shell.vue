<template>
  <div class="h5-shell">
    <header class="h5-header">
      <div class="h5-header__emblem"><AppIcon name="flame" :size="16" /></div>
      <div class="h5-header__text">
        <b>葫芦岛消防 · 培训签到</b>
        <span>TRAINING CHECK-IN</span>
      </div>
    </header>

    <main class="h5-main">
      <router-view />
    </main>

    <footer class="h5-footer">若长时间无响应，请退出微信浏览器重新扫码</footer>
  </div>
</template>

<script setup>
import AppIcon from "../../components/AppIcon.vue";
/* 仅做布局，不读 admin_token；H5 内的鉴权由各页面内部 ensureH5Login 触发。 */
</script>

<style scoped>
.h5-shell {
  min-height: 100vh;
  background: var(--bg);
  padding-bottom: calc(16px + env(safe-area-inset-bottom, 0px));
}
.h5-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 12px 16px;
  padding-top: calc(12px + env(safe-area-inset-top, 0px));
  background: var(--surface-nav);
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.h5-header__emblem {
  width: 28px;
  height: 28px;
  flex: none;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  color: #ffd9d5;
}
.h5-header__text {
  line-height: 1.25;
}
.h5-header__text b {
  display: block;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.04em;
}
.h5-header__text span {
  display: block;
  font-size: 9px;
  letter-spacing: 0.16em;
  color: #7f9cb5;
}
.h5-main {
  padding: 16px;
  max-width: 560px;
  margin: 0 auto;
}
.h5-footer {
  text-align: center;
  font-size: 11px;
  color: var(--ink-400);
  padding: 18px 16px 8px;
}
</style>
