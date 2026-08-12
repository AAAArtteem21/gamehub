<script setup>
import { ref } from 'vue'
import MatchHistoryTable from './MatchHistoryTable.vue'
import MatchParticipantsModal from './MatchParticipantsModal.vue'

defineProps({ stats: Object })

const openMatchId = ref(null)

function handleOpenMatch(matchId) {
  if (!matchId) return
  openMatchId.value = matchId
}
</script>

<template>
  <div class="universal-stats" v-if="stats">
    <div class="stats-row" v-if="stats.metrics?.length" :style="{ gridTemplateColumns: `repeat(${stats.metrics.length}, 1fr)` }">
      <div class="stat-box" v-for="m in stats.metrics" :key="m.label">
        <span class="stat-value" :class="m.tone">{{ m.value }}</span>
        <span class="stat-label">{{ m.label }}</span>
      </div>
    </div>

    <div class="badges-row" v-if="stats.badge || stats.tags?.length">
      <span class="rank-badge" v-if="stats.badge">{{ stats.badge }}</span>
      <span class="tag-pill" v-for="(t, i) in (stats.tags || []).filter(Boolean)" :key="i">{{ t.label }}</span>
    </div>

    <MatchHistoryTable :matches="stats.match_history" @open-match="handleOpenMatch" />

    <div class="list-section" v-if="stats.list?.length">
      <h4>{{ stats.list_title }}</h4>
      <div class="list-row" v-for="item in stats.list" :key="item.name">
        <span class="item-name">{{ item.name }}</span>
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

    <MatchParticipantsModal v-if="openMatchId" game="dota2" :match-id="openMatchId" @close="openMatchId = null" />
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
.badges-row { display: flex; gap: 6px; flex-wrap: wrap; }
.rank-badge { background: var(--accent-dim); color: var(--accent); font-weight: 700; font-size: 12px; padding: 5px 12px; border-radius: 20px; }
.tag-pill { background: var(--bg-card-hover); color: var(--text-secondary); font-weight: 600; font-size: 11px; padding: 4px 10px; border-radius: 20px; }
.list-section h4 { margin: 0 0 8px; font-size: 12px; color: var(--text-secondary); text-transform: uppercase; }
.list-row { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid var(--border-color); font-size: 13px; }
.list-row:last-child { border-bottom: none; }
.item-name { flex: 1; font-weight: 600; }
.item-value { font-weight: 700; color: var(--text-secondary); }
.item-value.good { color: var(--success); }
</style>