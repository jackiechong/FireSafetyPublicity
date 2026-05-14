<template>
  <div class="wrap">
    <el-card class="card">
      <template #header>
        <div class="title">葫芦岛市消防救援支队</div>
        <div class="sub">培训实名制 · 管理端</div>
      </template>
      <el-form :model="form" @submit.prevent="submit">
        <el-form-item label="账号">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password autocomplete="current-password" />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">
          登录
        </el-button>
      </el-form>
      <p class="hint">默认账号见项目说明（请及时修改密码）</p>
      <p class="hint-mobile">使用手机浏览器登录时将自动进入数据看板；若需录入数据，可在看板内切换「电脑版」。</p>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import http from "../api/http";

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const form = reactive({
  username: "",
  password: "",
});

async function submit() {
  loading.value = true;
  try {
    const { data } = await http.post("/api/admin/login", {
      username: form.username,
      password: form.password,
    });
    localStorage.setItem("admin_token", data.access_token);
    const redirect = route.query.redirect || "/";
    router.replace(redirect);
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(160deg, #1a237e 0%, #3949ab 50%, #5c6bc0 100%);
}
.card {
  width: 400px;
  max-width: 92vw;
}
.title {
  font-size: 1.15rem;
  font-weight: 600;
  text-align: center;
}
.sub {
  text-align: center;
  color: #666;
  font-size: 0.9rem;
  margin-top: 6px;
}
.hint {
  margin-top: 16px;
  font-size: 12px;
  color: #999;
  text-align: center;
}
.hint-mobile {
  margin-top: 10px;
  font-size: 12px;
  color: #666;
  text-align: center;
  line-height: 1.5;
}
</style>
