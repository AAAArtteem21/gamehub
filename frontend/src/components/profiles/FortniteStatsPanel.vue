<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  stats: { type: Object, required: true },
})

const windowKey = ref(props.stats?.default_window || 'lifetime')

watch(
  () => props.stats?.default_window,
  (v) => {
    if (v) windowKey.value = v
  }
)

const windows = computed(() => props.stats?.windows || {})
const hasSeason = computed(() => {
  const s = windows.value.season
  return !!(s && (s.overall?.matches || 0) > 0)
})

const current = computed(() => windows.value[windowKey.value] || windows.value.lifetime || {})
const overall = computed(() => current.value.overall || {})
const modes = computed(() => current.value.modes || {})

const hours = computed(() => {
  const m = overall.value.minutes || 0
  return m ? Math.round((m / 60) * 10) / 10 : 0
})

const modeEntries = computed(() => {
  const labels = { solo: 'Solo', duo: 'Duo', squad: 'Squad', ltm: 'LTM' }
  return Object.entries(labels)
    .map(([key, label]) => ({ key, label, data: modes.value[key] }))
    .filter((x) => x.data?.matches)
})

function fmt(n) {
  if (n == null || n === '') return '—'
  if (typeof n === 'number' && !Number.isInteger(n)) return n.toFixed(2)
  return n
}
</script>

<template>
  <div class="fn-panel">
    <div class="fn-top">
      <div class="fn-titles">
        <h3>Fortnite</h3>
        <span class="fn-bp" v-if="stats.bp_level != null">
          Battle Pass <b>{{ stats.bp_level }}</b>
          <span v-if="stats.bp_progress != null" class="fn-bp-bar-wrap">
            <span class="fn-bp-bar" :style="{ width: Math.min(stats.bp_progress, 100) + '%' }"></span>
          </span>
        </span>
      </div>

      <div class="fn-switch" role="tablist">
        <button
          type="button"
          class="fn-tab"
          :class="{ active: windowKey === 'lifetime' }"
          @click="windowKey = 'lifetime'"
        >
          Lifetime
        </button>
        <button
          type="button"
          class="fn-tab"
          :class="{ active: windowKey === 'season' }"
          :disabled="!hasSeason"
          @click="hasSeason && (windowKey = 'season')"
        >
          Season
        </button>
      </div>
    </div>

    <p class="fn-hint" v-if="windowKey === 'season'">
      Текущий сезон Epic (fortnite-api) · прошлые сезоны по номеру API не отдаёт
    </p>
    <p class="fn-hint muted" v-else>Вся карьера</p>

    <div class="fn-metrics">
      <div class="fn-metric">
        <span class="v win">{{ fmt(overall.wins) }}</span>
        <span class="l">побед</span>
      </div>
      <div class="fn-metric">
        <span class="v">{{ fmt(overall.matches) }}</span>
        <span class="l">матчей</span>
      </div>
      <div class="fn-metric">
        <span class="v accent">{{ fmt(overall.winrate) }}%</span>
        <span class="l">винрейт</span>
      </div>
      <div class="fn-metric">
        <span class="v accent">{{ fmt(overall.kd) }}</span>
        <span class="l">K/D</span>
      </div>
      <div class="fn-metric">
        <span class="v">{{ fmt(overall.kills) }}</span>
        <span class="l">убийств</span>
      </div>
      <div class="fn-metric">
        <span class="v">{{ hours }}</span>
        <span class="l">часов</span>
      </div>
    </div>

    <div class="fn-chips">
      <span class="chip">Top10 {{ fmt(overall.top10) }}</span>
      <span class="chip">Top25 {{ fmt(overall.top25) }}</span>
      <span class="chip">Outlived {{ fmt(overall.players_outlived) }}</span>
      <span class="chip">K/match {{ fmt(overall.kills_per_match) }}</span>
      <span class="chip">Score/match {{ fmt(overall.score_per_match) }}</span>
    </div>

    <div class="fn-pr-row">
      <div class="fn-pr-card">
        <span class="pr-label">Power Rank (PR)</span>
        <span class="pr-value muted">{{ stats.pr != null ? stats.pr : 'нет в API' }}</span>
      </div>
      <div class="fn-pr-card">
        <span class="pr-label">Earnings</span>
        <span class="pr-value muted">{{ stats.earnings != null ? stats.earnings : 'нет в API' }}</span>
      </div>
    </div>

    <div class="fn-modes" v-if="modeEntries.length">
      <h4>Режимы</h4>
      <div class="mode-grid">
        <div class="mode-card" v-for="m in modeEntries" :key="m.key">
          <div class="mode-name">{{ m.label }}</div>
          <div class="mode-stats">
            <span><b>{{ m.data.wins }}</b> W</span>
            <span>{{ m.data.matches }} игр</span>
            <span class="accent">{{ fmt(m.data.winrate) }}%</span>
            <span>KD {{ fmt(m.data.kd) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fn-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  animation: fn-in 0.35s var(--ease, ease);
}
@keyframes fn-in {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: none; }
}

.fn-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.fn-titles h3 {
  margin: 0 0 6px;
  font-size: 16px;
}
.fn-bp {
  font-size: 12px;
  color: var(--text-secondary);
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.fn-bp b { color: var(--accent); }
.fn-bp-bar-wrap {
  width: 72px;
  height: 6px;
  border-radius: 99px;
  background: var(--bg-card-hover);
  overflow: hidden;
}
.fn-bp-bar {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--accent), #a78bfa);
  border-radius: 99px;
  transition: width 0.4s ease;
}

.fn-switch {
  display: flex;
  padding: 3px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 999px;
  gap: 2px;
}
.fn-tab {
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
  padding: 7px 14px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}
.fn-tab:hover:not(:disabled) { color: var(--text-primary); }
.fn-tab.active {
  background: var(--accent-dim);
  color: var(--accent);
}
.fn-tab:disabled { opacity: 0.35; cursor: not-allowed; }

.fn-hint {
  margin: 0;
  font-size: 11px;
  color: var(--text-secondary);
}
.fn-hint.muted { color: var(--text-muted); }

.fn-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(88px, 1fr));
  gap: 8px;
}
.fn-metric {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  transition: border-color 0.2s ease, transform 0.2s ease;
}
.fn-metric:hover {
  border-color: var(--border-hover, var(--accent));
  transform: translateY(-1px);
}
.fn-metric .v { font-size: 18px; font-weight: 800; }
.fn-metric .v.win { color: var(--success); }
.fn-metric .v.accent { color: var(--accent); }
.fn-metric .l {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  color: var(--text-secondary);
}

.fn-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chip {
  font-size: 11px;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 999px;
  background: var(--bg-card-hover);
  color: var(--text-secondary);
}

.fn-pr-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.fn-pr-card {
  background: linear-gradient(135deg, var(--bg-primary), var(--bg-card-hover));
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.pr-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; }
.pr-value { font-size: 16px; font-weight: 800; }
.pr-value.muted { color: var(--text-muted); font-size: 13px; font-weight: 600; }

.fn-modes h4 {
  margin: 0 0 8px;
  font-size: 12px;
  text-transform: uppercase;
  color: var(--text-secondary);
}
.mode-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 8px;
}
.mode-card {
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 12px;
  background: var(--bg-primary);
  transition: border-color 0.2s ease;
}
.mode-card:hover { border-color: var(--accent); }
.mode-name { font-weight: 800; font-size: 13px; margin-bottom: 8px; }
.mode-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
  color: var(--text-secondary);
}
.mode-stats .accent { color: var(--accent); font-weight: 700; }
.mode-stats b { color: var(--text-primary); }
</style>