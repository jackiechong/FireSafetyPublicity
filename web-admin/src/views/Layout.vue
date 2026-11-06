<template>
  <div class="app" :class="{ 'is-mini': mini }">
    <aside class="nav">
      <div class="nav__head">
        <div class="nav__emblem"><AppIcon name="flame" :size="17" /></div>
        <div class="nav__title">
          <b>消防培训管理</b>
          <span>HULUDAO · FIRE RESCUE</span>
        </div>
      </div>

      <div class="nav__scroll">
        <div v-for="g in groups" :key="g.group" class="nav__group">
          <div class="nav__label">{{ g.group }}</div>
          <router-link
            v-for="item in g.items"
            :key="item.to"
            :to="item.to"
            class="nav__item"
            :class="{ 'is-active': isActive(item.to) }"
            :aria-label="item.label"
            @mouseenter="showTip(item.label, $event)"
            @mouseleave="hideTip"
            @focus="showTip(item.label, $event)"
            @blur="hideTip"
          >
            <AppIcon :name="item.icon" :size="rail ? 18 : 16" />
            <span class="nav__text">{{ item.label }}</span>
          </router-link>
        </div>
      </div>

      <div class="nav__foot">
        <button class="nav__collapse" type="button" :aria-label="mini ? '展开侧栏' : '收起侧栏'" @click="toggleMini">
          <AppIcon :name="mini ? 'chevron' : 'chevron-l'" :size="15" />
          <span>收起侧栏</span>
        </button>
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <nav class="crumb" aria-label="面包屑">
          <template v-if="crumb.group !== crumb.label">
            <span>{{ crumb.group }}</span>
            <AppIcon name="chevron" :size="12" />
          </template>
          <b>{{ crumb.label }}</b>
        </nav>

        <div class="topbar__spacer"></div>

        <div class="searchbox" role="button" tabindex="0" @click="openPalette" @keydown.enter="openPalette">
          <AppIcon name="search" :size="15" />
          <input placeholder="搜索功能页面…" readonly aria-label="搜索功能页面" />
          <span class="kbd">Ctrl K</span>
        </div>

        <el-dropdown trigger="click" @command="onUserCommand">
          <button class="userchip" type="button">
            <span class="avatar">{{ avatarText }}</span>
            <span class="userchip__meta">
              <b>{{ username || "…" }}</b>
              <span>{{ roleLabel }}</span>
            </span>
            <AppIcon name="chevron-d" :size="13" />
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="mobile">学员端预览（手机看板）</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </header>

      <main class="content">
        <div class="wrap">
          <router-view />
        </div>
      </main>
    </div>

    <div class="scrim" :class="{ 'is-open': paletteOpen }" @click="closePalette"></div>
    <div class="cmdk" :class="{ 'is-open': paletteOpen }" role="dialog" aria-label="功能搜索">
      <div class="cmdk__input">
        <AppIcon name="search" :size="17" />
        <input
          ref="paletteInput"
          v-model="paletteQuery"
          placeholder="跳转到页面…"
          @keydown.down.prevent="move(1)"
          @keydown.up.prevent="move(-1)"
          @keydown.enter.prevent="runActive"
        />
        <span class="kbd">ESC</span>
      </div>
      <div class="cmdk__list">
        <div
          v-for="(item, idx) in paletteItems"
          :key="item.to"
          class="cmdk__item"
          :class="{ 'is-on': idx === paletteIndex }"
          @mouseenter="paletteIndex = idx"
          @click="go(item.to)"
        >
          <AppIcon :name="item.icon" :size="15" />
          <span>{{ item.label }}</span>
          <span class="sub">{{ item.group }}</span>
        </div>
        <div v-if="!paletteItems.length" class="cmdk__item" style="cursor: default">没有匹配的页面</div>
      </div>
      <div class="cmdk__foot"><span>↑↓ 选择</span><span>↵ 进入</span><span>ESC 关闭</span></div>
    </div>

    <!-- 收起态标签气泡：.nav 有 overflow:hidden，只能用独立 fixed 图层 -->
    <div
      v-if="rail && tip.visible"
      class="nav-tip"
      :style="{ top: tip.top + 'px', left: tip.left + 'px' }"
      role="tooltip"
    >
      {{ tip.text }}
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import http from "../api/http";
import AppIcon from "../components/AppIcon.vue";
import { clearToken } from "../utils/auth";
import { findNavItem, visibleNav } from "../nav";

const route = useRoute();
const router = useRouter();

const role = ref("");
const username = ref("");
const mini = ref(localStorage.getItem("nav_mini") === "1");

/** 窄屏（≤980px）由 CSS 强制成图标轨道，这里同步一份状态，气泡与图标尺寸才会跟着变 */
const narrow = ref(false);
let mq = null;
function syncNarrow(e) {
  narrow.value = e.matches;
}
const rail = computed(() => mini.value || narrow.value);

const tip = reactive({ visible: false, text: "", top: 0, left: 0 });

function showTip(text, event) {
  if (!rail.value) return;
  const rect = event.currentTarget.getBoundingClientRect();
  tip.text = text;
  tip.top = rect.top + rect.height / 2;
  tip.left = rect.right + 10;
  tip.visible = true;
}

function hideTip() {
  tip.visible = false;
}

// 路由切换后光标可能已经不在图标上了，直接收起气泡
watch(() => route.path, hideTip);

const groups = computed(() => visibleNav(role.value));
const crumb = computed(() => {
  const hit = findNavItem(route.path);
  return hit ? { group: hit.group, label: hit.label } : { group: "管理端", label: "未命名页面" };
});
const avatarText = computed(() => (role.value === "detachment" ? "支队" : "大队"));
const roleLabel = computed(() => (role.value === "detachment" ? "支队 · 全市权限" : "大队 · 本辖区"));

const paletteOpen = ref(false);
const paletteQuery = ref("");
const paletteIndex = ref(0);
const paletteInput = ref(null);

const allItems = computed(() =>
  groups.value.flatMap((g) => g.items.map((it) => ({ ...it, group: g.group })))
);
const paletteItems = computed(() => {
  const q = paletteQuery.value.trim();
  if (!q) return allItems.value;
  return allItems.value.filter((it) => it.label.includes(q) || it.group.includes(q));
});

function isActive(to) {
  return route.path === to || route.path.startsWith(to + "/");
}

function toggleMini() {
  mini.value = !mini.value;
  hideTip();
  localStorage.setItem("nav_mini", mini.value ? "1" : "0");
}

function onUserCommand(cmd) {
  if (cmd === "logout") {
    clearToken();
    router.push("/login");
    return;
  }
  if (cmd === "mobile") {
    try {
      localStorage.removeItem("prefer_desktop");
    } catch {
      /* ignore */
    }
    router.push("/m");
  }
}

function openPalette() {
  paletteOpen.value = true;
  paletteQuery.value = "";
  paletteIndex.value = 0;
  requestAnimationFrame(() => paletteInput.value?.focus());
}

function closePalette() {
  paletteOpen.value = false;
}

function move(step) {
  const n = paletteItems.value.length;
  if (!n) return;
  paletteIndex.value = (paletteIndex.value + step + n) % n;
}

function runActive() {
  const item = paletteItems.value[paletteIndex.value];
  if (item) go(item.to);
}

function go(to) {
  closePalette();
  router.push(to);
}

function onKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    paletteOpen.value ? closePalette() : openPalette();
    return;
  }
  if (e.key === "Escape" && paletteOpen.value) closePalette();
}

onMounted(async () => {
  window.addEventListener("keydown", onKeydown);
  mq = window.matchMedia("(max-width: 980px)");
  narrow.value = mq.matches;
  mq.addEventListener("change", syncNarrow);
  try {
    const { data } = await http.get("/api/admin/me");
    role.value = data.role || "";
    username.value = data.username || "";
  } catch {
    role.value = "";
  }
});

onUnmounted(() => {
  window.removeEventListener("keydown", onKeydown);
  mq?.removeEventListener("change", syncNarrow);
});
</script>
