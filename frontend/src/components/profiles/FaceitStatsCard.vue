<!-- src/components/profiles/FaceitStatsCard.vue -->
<script setup>
defineProps({ stats: Object })
</script>

<template>
  <div class="faceit-stats" v-if="stats">
    <div class="stats-row">
      <div class="stat-box">
        <span class="stat-value">{{ stats.matches }}</span>
        <span class="stat-label">матчей</span>
      </div>
      <div class="stat-box">
        <span class="stat-value win">{{ stats.wins }}</span>
        <span class="stat-label">побед</span>
      </div>
      <div class="stat-box">
        <span class="stat-value accent">{{ stats.winrate }}%</span>
        <span class="stat-label">винрейт</span>
      </div>
      <div class="stat-box">
        <span class="stat-value">{{ stats.avg_kd }}</span>
        <span class="stat-label">K/D</span>
      </div>
    </div>

    <div class="rank-row" v-if="stats.elo">
      <span class="rank-badge">Level {{ stats.skill_level }}</span>
      <span class="mmr">{{ stats.elo }} ELO</span>
    </div>

    <div class="extra-row">
      <span>Средний HS%: <b>{{ stats.avg_headshots }}%</b></span>
      <span>Текущая серия: <b>{{ stats.current_streak }}</b></span>
      <span>Лучшая серия: <b>{{ stats.longest_streak }}</b></span>
    </div>
  </div>
</template>

<style scoped>
.faceit-stats { display: flex; flex-direction: column; gap: 16px; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.stat-box { display: flex; flex-direction: column; align-items: center; gap: 2px; background: var(--bg-primary); border-radius: var(--radius-sm); padding: 10px 6px; }
.stat-value { font-size: 18px; font-weight: 800; }
.stat-value.win { color: var(--success); }
.stat-value.accent { color: var(--accent); }
.stat-label { font-size: 10px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.3px; }
.rank-row { display: flex; align-items: center; gap: 10px; }
.rank-badge { background: var(--accent-dim); color: var(--accent); font-weight: 700; font-size: 12px; padding: 5px 12px; border-radius: 20px; }
.mmr { font-size: 12px; color: var(--text-secondary); }
.extra-row { display: flex; gap: 16px; font-size: 12px; color: var(--text-secondary); flex-wrap: wrap; }
.extra-row b { color: var(--text-primary); }
</style>