<script setup>
import { ref, computed } from 'vue'
import MatchHistoryTable from './MatchHistoryTable.vue'
import MatchParticipantsModal from './MatchParticipantsModal.vue'
import ValorantMatchModal from './ValorantMatchModal.vue'
import FortniteStatsPanel from './FortniteStatsPanel.vue'

const props = defineProps({
  stats: Object,
  platform: String,
})

const openMatchId = ref(null)

const isFortnite = computed(() => {
  const p = String(props.platform || '').toLowerCase()
  return p === 'fortnite' || props.stats?.kind === 'fortnite_panel'
})

const matchGame = computed(() => {
  const p = String(props.platform || '').toLowerCase()
  if (p === 'valorant') return 'valorant'
  if (p === 'opendota' || p === 'dota2') return 'dota2'
  if (p === 'faceit') return 'faceit'
  if (p === 'deadlock') return 'deadlock'
  return null
})

const hasMatchHistory = computed(
  () =>
    Array.isArray(props.stats?.match_history) &&
    props.stats.match_history.length > 0
)

const metrics = computed(() =>
  (props.stats?.metrics || []).filter(
    (m) => m && m.value !== undefined && m.value !== null && m.value !== ''
  )
)

// иконки (stroke-пути 24x24) подбираются по подписи метрики
const ICONS = {
  chart: 'M3 17l6-6 4 4 8-8M14 7h7v7',
  trophy: 'M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4zM17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3',
  gauge: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 12l4-3',
  star: 'M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9L12 3z',
  aim: 'M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zM12 2v4M12 18v4M2 12h4M18 12h4',
  skull: 'M12 3a8 8 0 0 0-8 8c0 3 1.5 5 3 6v3h10v-3c1.5-1 3-3 3-6a8 8 0 0 0-8-8zM9 12h.01M15 12h.01',
  dot: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z',
}

function iconFor(label) {
  const l = String(label || '').toLowerCase()
  if (/матч/.test(l)) return ICONS.chart
  if (/побед|solo w|^w$/.test(l)) return ICONS.trophy
  if (/пораж|solo l/.test(l)) return ICONS.skull
  if (/винрейт|форма/.test(l)) return ICONS.gauge
  if (/elo|lp|rr|mmr/.test(l)) return ICONS.star
  if (/k\/d|kda|килы|adr|acs|hs/.test(l)) return ICONS.aim
  return ICONS.dot
}

function handleOpenMatch(matchId) {
  if (!matchId || !matchGame.value) return
  openMatchId.value = matchId
}

function closeMatch() {
  openMatchId.value = null
}
</script>

<template>
  <div class="universal-stats" v-if="stats">
    <FortniteStatsPanel v-if="isFortnite" :stats="stats" />

    <template v-else>
      <div class="stats-row" v-if="metrics.length">
        <div class="stat-box" v-for="m in metrics" :key="m.label">
          <span class="stat-icon" :class="m.tone">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" stroke-linejoin="round">
              <path :d="iconFor(m.label)" />
            </svg>
          </span>
          <span class="stat-text">
            <span class="stat-value" :class="m.tone">{{ m.value }}</span>
            <span class="stat-label">{{ m.label }}</span>
          </span>
        </div>
      </div>

      <div class="badges-row" v-if="stats.badge || stats.tags?.length">
        <span class="rank-badge" v-if="stats.badge">{{ stats.badge }}</span>
        <span
          class="tag-pill"
          v-for="(t, i) in (stats.tags || []).filter(Boolean)"
          :key="i"
        >
          {{ t.label }}
        </span>
      </div>

      <MatchHistoryTable
        v-if="hasMatchHistory"
        :matches="stats.match_history"
        :can-open-participants="!!matchGame"
        @open-match="handleOpenMatch"
      />

      <div class="list-section" v-if="stats.list?.length">
        <h4>{{ stats.list_title }}</h4>
        <div class="list-row" v-for="item in stats.list" :key="item.name">
          <span class="item-name">{{ item.name }}</span>
          <span class="item-sub" v-if="item.sub">{{ item.sub }}</span>
          <span class="item-value" :class="{ good: item.good }">{{ item.value }}</span>
        </div>
      </div>

      <div class="list-section" v-if="stats.list_2?.length">
        <h4>{{ stats.list_title_2 }}</h4>
        <div class="list-row" v-for="item in stats.list_2" :key="item.name">
          <span class="item-name">{{ item.name }}</span>
          <span class="item-value">{{ item.value }}</span>
        </div>
      </div>
    </template>

    <MatchParticipantsModal
      v-if="openMatchId && matchGame === 'dota2'"
      game="dota2"
      :match-id="openMatchId"
      @close="closeMatch"
    />
    <ValorantMatchModal
      v-if="openMatchId && matchGame === 'valorant'"
      :match-id="openMatchId"
      @close="closeMatch"
    />
    <MatchParticipantsModal
      v-if="openMatchId && matchGame === 'faceit'"
      game="faceit"
      :match-id="openMatchId"
      @close="closeMatch"
    />
    <MatchParticipantsModal
      v-if="openMatchId && matchGame === 'deadlock'"
      game="deadlock"
      :match-id="openMatchId"
      @close="closeMatch"
    />
  </div>
</template>

<style scoped>
.universal-stats {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.stats-row {
  display: grid;
  width: 100%;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
}

.stat-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: var(--bg-sunken);
  border: 1px solid var(--panel-border);
  border-radius: 14px;
  min-width: 0;
}
.stat-box:hover {
  border-color: var(--accent);
  box-shadow: 0 0 14px var(--glow-soft);
}

.stat-icon {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent);
  background: var(--accent-dim);
  box-shadow: 0 0 12px var(--glow-soft);
}
.stat-icon svg { width: 18px; height: 18px; }
.stat-icon.win { color: var(--success); background: color-mix(in srgb, var(--success) 15%, transparent); box-shadow: none; }
.stat-icon.loss { color: var(--danger); background: color-mix(in srgb, var(--danger) 15%, transparent); box-shadow: none; }

.stat-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.stat-value {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}
.stat-value.win { color: var(--success); }
.stat-value.loss { color: var(--danger); }
.stat-value.accent { color: var(--accent); }

.stat-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.badges-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.rank-badge {
  background: var(--accent-dim);
  color: var(--text-primary);
  font-weight: 700;
  font-size: 11px;
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid var(--accent);
  box-shadow: 0 0 12px var(--glow-soft);
}

.tag-pill {
  background: var(--bg-sunken);
  border: 1px solid var(--panel-border);
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 11px;
  padding: 4px 12px;
  border-radius: 999px;
}

.list-section h4 {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.list-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
}
.list-row:last-child { border-bottom: none; }

.item-name { flex: 1; font-weight: 500; }
.item-sub { font-size: 12px; color: var(--text-secondary); }
.item-value {
  font-weight: 600;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}
.item-value.good { color: var(--success); }
</style>