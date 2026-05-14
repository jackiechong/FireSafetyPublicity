<template>
  <div class="h5-shell">
    <header class="h5-header">
      <div class="h5-brand">葫芦岛消防 · 培训签到</div>
    </header>
    <main class="h5-main">
      <router-view />
    </main>
    <footer class="h5-footer">
      若长时间无响应，请退出微信浏览器重新扫码
    </footer>
  </div>
</template>

<script setup>
/* 仅做布局，不读 admin_token；H5 内的鉴权由各页面内部 ensureH5Login 触发。 */
</script>

<style scoped>
.h5-shell {
  min-height: 100vh;
  background: #f4f6fb;
  padding-bottom: env(safe-area-inset-bottom, 12px);
}
.h5-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: linear-gradient(135deg, #1a237e 0%, #3949ab 100%);
  color: #fff;
  padding: 14px 16px;
  padding-top: calc(14px + env(safe-area-inset-top, 0px));
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}
.h5-main {
  padding: 14px;
  max-width: 640px;
  margin: 0 auto;
}
.h5-footer {
  text-align: center;
  font-size: 11px;
  color: #aaa;
  padding: 16px 0 10px;
}
</style>
