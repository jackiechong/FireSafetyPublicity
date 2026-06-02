<template>
  <div class="h5-entry">
    <h2 class="h5-entry-title">学员培训签到</h2>
    <p class="h5-entry-desc">
      请使用微信打开本页。首次使用需登记姓名、单位与手机号；之后再次扫码将自动识别您的微信身份。
    </p>
    <button class="h5-btn-primary" @click="goWxLogin">微信登录 · 选择培训签到</button>
    <button class="h5-btn-secondary" @click="goWxMe">微信登录 · 我的培训记录</button>
    <p class="h5-entry-note">
      若您扫描的是现场培训二维码，也可直接扫二维码进入，无需从此页进入。
    </p>
  </div>
</template>

<script setup>
function goWxLogin() {
  const params = new URLSearchParams({ next: "/h5/checkin" });
  window.location.href = `/api/wxoa/login?${params.toString()}`;
}

function goWxMe() {
  const params = new URLSearchParams({ next: "/h5/me" });
  window.location.href = `/api/wxoa/login?${params.toString()}`;
}
</script>

<style scoped>
.h5-entry {
  background: #fff;
  border-radius: 12px;
  padding: 24px 18px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  text-align: center;
}
.h5-entry-title {
  margin: 0 0 10px;
  font-size: 18px;
  color: #1a237e;
}
.h5-entry-desc {
  margin: 0 0 20px;
  font-size: 13px;
  color: #666;
  line-height: 1.6;
  text-align: left;
}
.h5-btn-primary {
  width: 100%;
  height: 46px;
  margin-bottom: 10px;
  background: #3949ab;
  color: #fff;
  border: 0;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
}
.h5-btn-secondary {
  width: 100%;
  height: 42px;
  background: #e8eaf6;
  color: #1a237e;
  border: 0;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
}
.h5-entry-note {
  margin: 16px 0 0;
  font-size: 12px;
  color: #999;
  line-height: 1.5;
}
</style>
