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
  return null
})

const hasMatchHistory = computed(
  () => Array.isArray(props.stats?.match_history) && props.stats.match_history.length > 0
)

/** Только метрики с реальным value */
const metrics = computed(() =>
  (props.stats?.metrics || []).filter(
    (m) => m && m.value !== undefined && m.value !== null && m.value !== ''
  )
)

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
          <span class="stat-value" :class="m.tone">{{ m.value }}</span>
          <span class="stat-label">{{ m.label }}</span>
        </div>
      </div>

      <div class="badges-row" v-if="stats.badge || stats.tags?.length">
        <span class="rank-badge" v-if="stats.badge">{{ stats.badge }}</span>
        <span
          class="tag-pill"
          v-for="(t, i) in (stats.tags || []).filter(Boolean)"
          :key="i"
        >{{ t.label }}</span>
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
  </div>
</template>

<style scoped>
.universal-stats {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.stats-row {
  display: grid;
  width: 100%;
  gap: 10px;
  /* 2–6 метрик равномерно на всю ширину */
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
}

.stat-box {
  width: 100%;
  min-height: 78px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 14px 10px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  transition: border-color 0.2s var(--ease), background 0.2s var(--ease);
}
.stat-box:hover {
  border-color: var(--border-hover);
  background: var(--bg-card-hover);
}

.stat-value {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
.stat-value.win { color: var(--success); }
.stat-value.loss { color: var(--danger); }
.stat-value.accent { color: var(--accent); }

.stat-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  text-align: center;
}

.badges-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.rank-badge {
  background: var(--accent-dim);
  color: var(--accent);
  font-weight: 800;
  font-size: 11px;
  padding: 5px 12px;
  border-radius: 999px;
  letter-spacing: 0.04em;
}

.tag-pill {
  background: var(--bg-card-hover);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 11px;
  padding: 4px 11px;
  border-radius: 999px;
}

.list-section h4 {
  margin: 0 0 10px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.list-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
}
.list-row:last-child { border-bottom: none; }

.item-name { flex: 1; font-weight: 600; }
.item-sub { font-size: 12px; color: var(--text-secondary); }
.item-value {
  font-weight: 700;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}
.item-value.good { color: var(--success); }
</style>