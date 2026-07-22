<script setup>
defineProps({ stats: Object, skillRating: [Number, String] })

const rankNames = {
  1: 'Herald', 2: 'Guardian', 3: 'Crusader', 4: 'Archon',
  5: 'Legend', 6: 'Ancient', 7: 'Divine', 8: 'Immortal',
}

function rankLabel(rankTier) {
  if (!rankTier) return 'Ранг неизвестен'
  const medal = Math.floor(rankTier / 10)
  const star = rankTier % 10
  return `${rankNames[medal] || ''} ${star}`
}
</script>

<template>
  <div class="dota-stats" v-if="stats">
    <div class="stats-row">
      <div class="stat-box">
        <span class="stat-value">{{ stats.total_matches }}</span>
        <span class="stat-label">матчей</span>
      </div>
      <div class="stat-box">
        <span class="stat-value win">{{ stats.wins }}</span>
        <span class="stat-label">побед</span>
      </div>
      <div class="stat-box">
        <span class="stat-value loss">{{ stats.losses }}</span>
        <span class="stat-label">поражений</span>
      </div>
      <div class="stat-box">
        <span class="stat-value accent">{{ stats.winrate }}%</span>
        <span class="stat-label">винрейт</span>
      </div>
    </div>

    <div class="rank-row" v-if="stats.mmr_estimate || stats.rank_tier">
      <span class="rank-badge">{{ rankLabel(stats.rank_tier) }}</span>
      <span class="mmr" v-if="stats.mmr_estimate">≈ {{ stats.mmr_estimate }} MMR</span>
    </div>

    <div class="heroes-section" v-if="stats.top_heroes?.length">
      <h4>Любимые герои</h4>
      <div class="hero-row" v-for="h in stats.top_heroes" :key="h.name">
        <span class="hero-name">{{ h.name }}</span>
        <span class="hero-games">{{ h.games }} игр</span>
        <span class="hero-winrate" :class="{ good: h.winrate >= 50 }">{{ h.winrate }}%</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dota-stats { display: flex; flex-direction: column; gap: 16px; }

.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.stat-box {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  background: var(--bg-primary); border-radius: var(--radius-sm); padding: 10px 6px;
}
.stat-value { font-size: 18px; font-weight: 800; }
.stat-value.win { color: var(--success); }
.stat-value.loss { color: var(--danger); }
.stat-value.accent { color: var(--accent); }
.stat-label { font-size: 10px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.3px; }

.rank-row { display: flex; align-items: center; gap: 10px; }
.rank-badge {
  background: var(--accent-dim); color: var(--accent); font-weight: 700; font-size: 12px;
  padding: 5px 12px; border-radius: 20px;
}
.mmr { font-size: 12px; color: var(--text-secondary); }

.heroes-section h4 { margin: 0 0 8px; font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.3px; }
.hero-row { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid var(--border-color); font-size: 13px; }
.hero-row:last-child { border-bottom: none; }
.hero-name { flex: 1; font-weight: 600; }
.hero-games { color: var(--text-secondary); font-size: 12px; }
.hero-winrate { font-weight: 700; color: var(--text-secondary); min-width: 40px; text-align: right; }
.hero-winrate.good { color: var(--success); }
</style>