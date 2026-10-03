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
  gap: 8px;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
}

.stat-box {
  width: 100%;
  min-height: 72px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 12px 8px;
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}
.stat-box:hover {
  border-color: var(--border-hover);
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}
.stat-value.win {
  color: var(--success);
}
.stat-value.loss {
  color: var(--danger);
}
.stat-value.accent {
  color: var(--accent);
}

.stat-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  text-align: center;
}

.badges-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}

.rank-badge {
  background: var(--accent-dim);
  color: var(--accent);
  font-weight: 700;
  font-size: 11px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(196, 165, 116, 0.25);
  letter-spacing: 0.02em;
}

.tag-pill {
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 11px;
  padding: 3px 9px;
  border-radius: var(--radius-sm);
}

.list-section h4 {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.list-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
}
.list-row:last-child {
  border-bottom: none;
}

.item-name {
  flex: 1;
  font-weight: 500;
}
.item-sub {
  font-size: 12px;
  color: var(--text-secondary);
}
.item-value {
  font-weight: 600;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}
.item-value.good {
  color: var(--success);
}
</style>