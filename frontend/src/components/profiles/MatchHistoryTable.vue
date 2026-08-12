<script setup>
const props = defineProps({ matches: Array })
const emit = defineEmits(['open-match'])

import { ref } from 'vue'
const expandedIndex = ref(null)

function toggle(i) {
  expandedIndex.value = expandedIndex.value === i ? null : i
}

function openParticipants(m) {
  if (!m.match_id) return
  emit('open-match', m.match_id)
}
</script>

<template>
  <div class="match-history" v-if="matches?.length">
    <h4>История матчей</h4>
    <div
      v-for="(m, i) in matches" :key="i"
      class="match-row" :class="{ win: m.won === true, loss: m.won === false }"
    >
      <div class="match-summary" @click="toggle(i)">
        <span class="result-badge" v-if="m.won !== null">{{ m.won ? 'W' : 'L' }}</span>
        <div class="match-main">
          <div class="match-top">
            <span class="match-title">{{ m.title }}</span>
            <span class="match-subtitle">{{ m.subtitle }}</span>
          </div>
        </div>
        <div class="match-right">
          <span v-if="m.played_at">{{ m.played_at }}</span>
          <span v-if="m.duration">{{ m.duration }}</span>
        </div>
        <span class="expand-arrow">{{ expandedIndex === i ? '▲' : '▼' }}</span>
      </div>

      <transition name="expand">
        <div class="match-details-expanded" v-if="expandedIndex === i">
          <div class="detail-item" v-for="d in (m.details || [])" :key="d.label">
            <span class="detail-label">{{ d.label }}</span>
            <span class="detail-value">{{ d.value }}</span>
          </div>
          <button class="view-participants-btn" v-if="m.match_id" @click.stop="openParticipants(m)">
            👥 Кто играл
          </button>
        </div>
      </transition>
    </div>
  </div>
</template>

<style scoped>
.match-history { display: flex; flex-direction: column; gap: 8px; }
.match-history h4 { margin: 0 0 4px; font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.3px; }

.match-row {
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--border-color);
  overflow: hidden;
}
.match-row.win { border-left-color: var(--success); }
.match-row.loss { border-left-color: var(--danger); }

.match-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  cursor: pointer;
}

.result-badge {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
  flex-shrink: 0;
}
.match-row.win .result-badge { background: rgba(74, 222, 128, 0.15); color: var(--success); }
.match-row.loss .result-badge { background: rgba(248, 113, 113, 0.15); color: var(--danger); }

.match-main { flex: 1; min-width: 0; }
.match-top { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.match-title { font-weight: 700; font-size: 13px; }
.match-subtitle { font-size: 12px; color: var(--text-secondary); font-family: monospace; }

.match-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.expand-arrow { font-size: 9px; color: var(--text-muted); flex-shrink: 0; }

.match-details-expanded {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
  padding: 0 10px 12px;
  border-top: 1px solid var(--border-color);
  margin-top: 4px;
  padding-top: 10px;
}
.detail-item { display: flex; flex-direction: column; gap: 2px; }
.detail-label { font-size: 10px; color: var(--text-secondary); text-transform: uppercase; }
.detail-value { font-size: 13px; font-weight: 700; color: var(--text-primary); }

.view-participants-btn {
  grid-column: 1 / -1;
  margin-top: 6px;
  background: var(--accent-dim);
  border: none;
  color: var(--accent);
  padding: 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}
.view-participants-btn:hover { background: var(--accent); color: white; }

.expand-enter-active, .expand-leave-active { transition: all 0.2s var(--ease); }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; }
</style>