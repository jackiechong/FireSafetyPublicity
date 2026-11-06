<template>
  <div class="login">
    <section class="login__brand">
      <div class="login__mark">
        <div class="login__emblem"><AppIcon name="flame" :size="26" /></div>
        <div>
          <div class="login__org">葫芦岛市消防救援支队</div>
          <div class="login__sys">TRAINING INFORMATION PLATFORM</div>
        </div>
      </div>

      <div class="login__pitch">
        <h1>培训实名制<br /><em>一处登记</em>，全市留痕</h1>
        <p>
          覆盖支队、9 个大队与全市社会单位。培训登记、现场签到、人员档案与统计报表在同一条数据链上流转。
        </p>
        <div class="login__stats">
          <div class="login__stat">
            <b class="num">{{ stats.orgs }}</b><span>纳管单位</span>
          </div>
          <div class="login__stat">
            <b class="num">{{ stats.attendances }}</b><span>年度参训人次</span>
          </div>
          <div class="login__stat">
            <b class="num">{{ stats.trainings }}</b><span>培训场次</span>
          </div>
        </div>
      </div>

      <div class="login__foot">政务内网系统 · 请勿向无关人员泄露账号信息</div>
    </section>

    <section class="login__panel">
      <form class="login__form" @submit.prevent="submit">
        <h2>登录管理端</h2>
        <p>使用支队统一分配的管理员账号</p>

        <div class="login__fields">
          <div class="field">
            <label for="lg-user">账号</label>
            <div class="input-wrap">
              <AppIcon name="users" class="ico" :size="16" />
              <input
                id="lg-user"
                v-model.trim="form.username"
                class="input"
                :class="{ 'is-error': errors.username }"
                type="text"
                autocomplete="username"
                placeholder="请输入管理员账号"
                @input="errors.username = ''"
              />
            </div>
            <div v-if="errors.username" class="hint is-error">{{ errors.username }}</div>
          </div>

          <div class="field">
            <label for="lg-pass">密码</label>
            <div class="input-wrap">
              <AppIcon name="key" class="ico" :size="16" />
              <input
                id="lg-pass"
                v-model="form.password"
                class="input"
                :class="{ 'is-error': errors.password || errors.submit }"
                type="password"
                autocomplete="current-password"
                placeholder="请输入密码"
                @input="onPasswordInput"
              />
            </div>
            <div v-if="errors.password || errors.submit" class="hint is-error">
              {{ errors.password || errors.submit }}
            </div>
          </div>

          <div class="login__row">
            <label class="check"><input v-model="remember" type="checkbox" /> 7 天内免登录</label>
            <span class="hint" style="margin: 0">忘记密码请联系支队管理员</span>
          </div>

          <button class="btn btn--primary btn--block" type="submit" :disabled="loading">
            {{ loading ? "正在登录…" : "进入管理端" }}
            <AppIcon v-if="!loading" name="chevron" :size="15" />
          </button>
        </div>

        <p class="hint" style="margin-top: 18px">首次登录后请立即修改初始密码</p>
      </form>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import http from "../api/http";
import AppIcon from "../components/AppIcon.vue";
import { setToken } from "../utils/auth";

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const remember = ref(true);
const stats = reactive({ orgs: "—", attendances: "—", trainings: "—" });
const form = reactive({ username: "", password: "" });
const errors = reactive({ username: "", password: "", submit: "" });

function nf(n) {
  return Number(n || 0).toLocaleString("zh-CN");
}

onMounted(async () => {
  try {
    const { data } = await http.get("/health");
    stats.orgs = nf(data.counts?.organizations);
    stats.attendances = nf(data.counts?.attendances);
    stats.trainings = nf(data.counts?.trainings);
  } catch {
    /* 统计拿不到不影响登录 */
  }
});

function onPasswordInput() {
  errors.password = "";
  errors.submit = "";
}

async function submit() {
  errors.username = form.username ? "" : "请输入账号";
  errors.password = form.password ? "" : "请输入密码";
  errors.submit = "";
  if (errors.username || errors.password) return;

  loading.value = true;
  try {
    const { data } = await http.post("/api/admin/login", {
      username: form.username,
      password: form.password,
    });
    setToken(data.access_token, remember.value);
    const redirect = route.query.redirect;
    const target =
      typeof redirect === "string" && redirect.startsWith("/") && !redirect.startsWith("//")
        ? redirect
        : "/";
    router.replace(target);
  } catch (e) {
    const status = e.response?.status;
    errors.submit = status === 401 ? "账号或密码不正确" : "登录失败，请稍后重试";
  } finally {
    loading.value = false;
  }
}
</script>
