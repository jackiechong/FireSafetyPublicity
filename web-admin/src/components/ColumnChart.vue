<template>
  <svg class="chart" :viewBox="`0 0 ${W} ${H}`" role="img" :aria-label="ariaLabel">
    <defs>
      <linearGradient :id="`gCool-${uid}`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#8fbcd8" /><stop offset="1" stop-color="#cfe2ef" />
      </linearGradient>
      <linearGradient :id="`gHot-${uid}`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#1b6da3" /><stop offset="1" stop-color="#4d9ac9" />
      </linearGradient>
    </defs>

    <g v-for="(row, i) in gridRows" :key="`g${i}`">
      <line class="grid-line" :x1="pad.l" :y1="row.y" :x2="W - pad.r" :y2="row.y" />
      <text
        :x="pad.l - 8"
        :y="row.y + 3.5"
        text-anchor="end"
        font-size="11"
        fill="#7d8fa1"
        font-family="var(--font-num)"
      >{{ row.label }}</text>
    </g>

    <g v-for="(bar, i) in bars" :key="`b${i}`" class="bar-row">
      <title>{{ labels[i] }}：{{ values[i] }} {{ unit }}</title>
      <rect :x="bar.x" :y="bar.y" :width="bar.w" :height="bar.h" rx="2" :fill="`url(#${i === peakIndex ? 'gHot' : 'gCool'}-${uid})`" />
      <text
        v-if="i === peakIndex"
        :x="bar.x + bar.w / 2"
        :y="bar.y - 7"
        text-anchor="middle"
        font-size="11"
        font-weight="600"
        fill="#155583"
        font-family="var(--font-num)"
      >{{ values[i] }}</text>
      <text :x="bar.x + bar.w / 2" :y="H - 8" text-anchor="middle" font-size="11" fill="#5a6e82">{{ labels[i] }}</text>
    </g>

    <line class="axis-line" :x1="pad.l" :y1="pad.t + ih" :x2="W - pad.r" :y2="pad.t + ih" />
  </svg>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  values: { type: Array, default: () => [] },
  labels: { type: Array, default: () => [] },
  unit: { type: String, default: "场" },
  ariaLabel: { type: String, default: "月度趋势图" },
});

const W = 660;
const H = 236;
const pad = { t: 18, r: 12, b: 28, l: 40 };
const ih = H - pad.t - pad.b;
const uid = `c${Math.random().toString(36).slice(2, 8)}`;

const maxValue = computed(() => {
  const m = Math.max(...props.values, 1);
  return Math.max(10, Math.ceil(m / 10) * 10);
});

const peakIndex = computed(() => {
  if (!props.values.length) return -1;
  return props.values.indexOf(Math.max(...props.values));
});

const gridRows = computed(() =>
  Array.from({ length: 5 }, (_, i) => ({
    y: pad.t + ih - (ih * i) / 4,
    label: ((maxValue.value * i) / 4).toFixed(0),
  }))
);

const bars = computed(() => {
  const n = props.values.length || 1;
  const step = (W - pad.l - pad.r) / n;
  const bw = Math.min(28, step * 0.46);
  return props.values.map((v, i) => {
    const h = (v / maxValue.value) * ih;
    return {
      x: pad.l + step * i + (step - bw) / 2,
      y: pad.t + ih - h,
      w: bw,
      h: Math.max(h, 1),
    };
  });
});
</script>
