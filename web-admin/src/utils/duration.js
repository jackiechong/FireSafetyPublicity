const MINUTES_PER_DAY = 1440;
const MINUTES_PER_HOUR = 60;

/**
 * 培训时长：≤60 为「XXm」；61–1439 为「XhYm」；≥1440（24h）起用「Xd…」再接不足一天部分。
 */
export function formatTrainingMinutes(minutes) {
  const m = Math.round(Number(minutes));
  if (!Number.isFinite(m) || m < 0) return "—";
  if (m <= 60) return `${m}m`;
  if (m < MINUTES_PER_DAY) {
    const h = Math.floor(m / MINUTES_PER_HOUR);
    const rest = m % MINUTES_PER_HOUR;
    return `${h}h${rest}m`;
  }
  const d = Math.floor(m / MINUTES_PER_DAY);
  const rem = m % MINUTES_PER_DAY;
  if (rem === 0) return `${d}d`;
  const remH = Math.floor(rem / MINUTES_PER_HOUR);
  const remM = rem % MINUTES_PER_HOUR;
  return `${d}d${remH}h${remM}m`;
}

/** 柱状图 Y 轴：分钟换算成天，只显示整数「Xd」，不保留小数 */
export function formatMinutesAxisDays(minutes) {
  const m = Number(minutes);
  if (!Number.isFinite(m) || m < 0) return "—";
  return `${Math.round(m / MINUTES_PER_DAY)}d`;
}
