<!-- src/components/profiles/UniversalStatsCard.vue -->
<script setup>
defineProps({ stats: Object })
</script>

<template>
  <div class="universal-stats" v-if="stats">
    <div class="stats-row" :style="{ gridTemplateColumns: `repeat(${stats.metrics.length}, 1fr)` }">
      <div class="stat-box" v-for="m in stats.metrics" :key="m.label">
        <span class="stat-value" :class="m.tone">{{ m.value }}</span>
        <span class="stat-label">{{ m.label }}</span>
      </div>
    </div>

    <div class="badge-row" v-if="stats.badge">
      <span class="rank-badge">{{ stats.badge }}</span>
    </div>

    <div class="list-section" v-if="stats.list?.length">
      <h4>{{ stats.list_title }}</h4>
      <div class="list-row" v-for="item in stats.list" :key="item.name">
        <span class="item-name">{{ item.name }}</span>
        <span class="item-sub" v-if="item.sub">{{ item.sub }}</span>
        <span class="item-value" :class="{ good: item.good }">{{ item.value }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.universal-stats { display: flex; flex-direction: column; gap: 16px; }
.stats-row { display: grid; gap: 8px; }
.stat-box { display: flex; flex-direction: column; align-items: center; gap: 2px; background: var(--bg-primary); border-radius: var(--radius-sm); padding: 10px 6px; }
.stat-value { font-size: 18px; font-weight: 800; }
.stat-value.win { color: var(--success); }
.stat-value.loss { color: var(--danger); }
.stat-value.accent { color: var(--accent); }
.stat-label { font-size: 10px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.3px; }

.badge-row { display: flex; }
.rank-badge { background: var(--accent-dim); color: var(--accent); font-weight: 700; font-size: 12px; padding: 5px 12px; border-radius: 20px; }

.list-section h4 { margin: 0 0 8px; font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.3px; }
.list-row { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid var(--border-color); font-size: 13px; }
.list-row:last-child { border-bottom: none; }
.item-name { flex: 1; font-weight: 600; }
.item-sub { color: var(--text-secondary); font-size: 12px; }
.item-value { font-weight: 700; color: var(--text-secondary); min-width: 40px; text-align: right; }
.item-value.good { color: var(--success); }
</style>