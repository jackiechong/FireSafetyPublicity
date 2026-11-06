<template>
  <div class="h5-entry">
    <section class="card entry-hero">
      <div class="entry-mark"><AppIcon name="flame" :size="26" /></div>
      <h1 class="entry-title">学员培训签到</h1>
      <p class="entry-desc">
        请使用微信打开本页。首次使用需登记姓名、单位与手机号；之后再次扫码将自动识别您的微信身份。
      </p>
    </section>

    <div class="entry-steps">
      <div class="entry-step">
        <span class="entry-step__no num">01</span>
        <div><b>扫码进入</b><span>扫描现场培训二维码</span></div>
      </div>
      <div class="entry-step">
        <span class="entry-step__no num">02</span>
        <div><b>实名登记</b><span>填写姓名、单位与手机号</span></div>
      </div>
      <div class="entry-step">
        <span class="entry-step__no num">03</span>
        <div><b>确认签到</b><span>一次签到计入个人培训档案</span></div>
      </div>
    </div>

    <div class="entry-actions">
      <button class="btn btn--primary btn--block" @click="goWxLogin">
        微信登录 · 选择培训签到
        <AppIcon name="chevron" :size="15" />
      </button>
      <button class="btn btn--ghost btn--block" @click="goWxMe">微信登录 · 我的培训记录</button>
    </div>

    <p class="entry-note">若您扫描的是现场培训二维码，也可直接扫二维码进入，无需从此页进入。</p>
  </div>
</template>

<script setup>
import AppIcon from "../../components/AppIcon.vue";

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
.entry-hero {
  padding: 26px 20px 22px;
  text-align: center;
}
.entry-mark {
  width: 52px;
  height: 52px;
  margin: 0 auto 14px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--brand-50);
  border: 1px solid #cfe0ee;
  color: var(--brand-700);
}
.entry-title {
  font-size: var(--fs-20);
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--ink-900);
}
.entry-desc {
  margin-top: 8px;
  font-size: var(--fs-13);
  line-height: 1.7;
  color: var(--ink-500);
  text-align: left;
}
.entry-steps {
  display: grid;
  gap: 1px;
  margin-top: 12px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  overflow: hidden;
}
.entry-step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--surface);
}
.entry-step__no {
  font-size: var(--fs-12);
  font-weight: 600;
  color: var(--ink-300);
  letter-spacing: 0.04em;
}
.entry-step b {
  display: block;
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--ink-900);
}
.entry-step span:last-child {
  font-size: var(--fs-12);
  color: var(--ink-500);
}
.entry-actions {
  display: grid;
  gap: 10px;
  margin-top: 16px;
}
.entry-actions .btn {
  height: 46px;
  font-size: var(--fs-14);
}
.entry-note {
  margin-top: 16px;
  font-size: var(--fs-12);
  line-height: 1.6;
  color: var(--ink-500);
  text-align: center;
}
</style>
