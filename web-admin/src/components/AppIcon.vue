<template>
  <!--
    图标来自 IconSprite 的 24×24 网格（<g id="i-xxx">）。
    必须声明 viewBox，否则 <use> 会把 24 坐标系按 1:1 画进 size×size 视口，
    只显示左上角一块（右侧与底部被裁掉）。
  -->
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <use :href="`#i-${name}`" />
  </svg>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 16 },
});

/**
 * 24 网格缩放到实际尺寸后线宽也会等比变细（16px 时 1.7 → 约 1.13px），
 * 这里反向补偿，保证不同尺寸下的视觉粗细一致。
 */
const strokeWidth = computed(() => {
  const s = Number(props.size) || 16;
  return (1.7 * (24 / s)).toFixed(2);
});
</script>
