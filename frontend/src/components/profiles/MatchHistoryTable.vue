<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  matches: { type: Array, default: () => [] },
  initialLimit: { type: Number, default: 8 },
  canOpenParticipants: { type: Boolean, default: true },
})
const emit = defineEmits(['open-match'])

const expandedIndex = ref(null)
const limit = ref(props.initialLimit)

const visibleMatches = computed(() => (props.matches || []).slice(0, limit.value))
const canShowMore = computed(() => (props.matches || []).length > limit.value)

watch(
  () => props.matches,
  () => {
    expandedIndex.value = null
    limit.value = props.initialLimit
  }
)

function toggle(i) {
  expandedIndex.value = expandedIndex.value === i ? null : i
}

function openParticipants(m) {
  if (!m.match_id) return
  emit('open-match', m.match_id)
}

function showMore() {
  limit.value = Math.min(limit.value + 10, (props.matches || []).length)
}
</script>

<template>
  <div class="match-history" v-if="matches?.length">
    <h4>История матчей</h4>
    <div
      v-for="(m, i) in visibleMatches"
      :key="m.match_id || i"
      class="match-row"
      :class="{ win: m.won === true, loss: m.won === false }"
    >
      <div class="match-summary" @click="toggle(i)">
        <span class="result-badge" v-if="m.won !== null && m.won !== undefined">
          {{ m.won ? 'W' : 'L' }}
        </span>
        <div class="match-main">
          <div class="match-top">
            <span class="match-title">{{ m.title }}</span>
            <span class="match-subtitle">{{ m.subtitle }}</span>
          </div>
        </div>
        <div class="match-right">
          <div class="verdict-row">
            <span class="verdict-badge" v-if="m.verdict" :class="m.verdict.tone">{{ m.verdict.label }}</span>
            <span class="solo-badge" v-if="m.solo">Соло</span>
          </div>
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
          <button
          type="button"
          class="view-participants-btn"
          v-if="m.match_id && canOpenParticipants"
          @click.stop="openParticipants(m)"
        >
          👥 Кто играл
        </button>
        </div>
      </transition>
    </div>

    <button v-if="canShowMore" type="button" class="show-more-btn" @click="showMore">
      Показать ещё
      <span class="show-more-count">
        ({{ visibleMatches.length }} / {{ matches.length }})
      </span>
    </button>
  </div>
</template>

<style scoped>
.match-history {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.match-history h4 {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.match-row {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-left: 3px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  transition: border-color 0.15s var(--ease), background 0.15s var(--ease);
}
.match-row:hover {
  border-color: var(--border-hover);
  background: var(--bg-card-hover);
}
.match-row.win { border-left-color: var(--success); }
.match-row.loss { border-left-color: var(--danger); }

.match-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  cursor: pointer;
}

.result-badge {
  width: 24px;
  height: 24px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
  flex-shrink: 0;
}
.match-row.win .result-badge {
  background: rgba(74, 222, 128, 0.15);
  color: var(--success);
}
.match-row.loss .result-badge {
  background: rgba(248, 113, 113, 0.15);
  color: var(--danger);
}

.match-main { flex: 1; min-width: 0; }
.match-top {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}
.match-title {
  font-weight: 700;
  font-size: 13px;
  letter-spacing: -0.01em;
}
.match-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  font-family: ui-monospace, 'Cascadia Code', monospace;
  font-variant-numeric: tabular-nums;
}

.match-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}

.expand-arrow {
  font-size: 9px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.match-details-expanded {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 10px;
  padding: 12px 14px 14px;
  border-top: 1px solid var(--border-color);
  background: rgba(0, 0, 0, 0.15);
}
.detail-item { display: flex; flex-direction: column; gap: 3px; }
.detail-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.detail-value {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.view-participants-btn {
  grid-column: 1 / -1;
  margin-top: 4px;
  background: var(--accent-dim);
  border: none;
  color: var(--accent);
  padding: 9px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s var(--ease), color 0.15s var(--ease);
}
.view-participants-btn:hover {
  background: var(--accent);
  color: #fff;
}

.expand-enter-active,
.expand-leave-active {
  transition: opacity 0.2s var(--ease), max-height 0.25s var(--ease);
  overflow: hidden;
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.verdict-row {
  display: flex;
  gap: 4px;
  margin-bottom: 2px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.verdict-badge {
  font-size: 9px;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 10px;
  text-transform: uppercase;
}
.verdict-badge.great { background: rgba(74, 222, 128, 0.2); color: var(--success); }
.verdict-badge.good { background: var(--accent-dim); color: var(--accent); }
.verdict-badge.neutral { background: var(--bg-card-hover); color: var(--text-secondary); }
.verdict-badge.bad { background: rgba(240, 160, 32, 0.15); color: var(--warning, #F0A020); }
.verdict-badge.terrible { background: rgba(248, 113, 113, 0.2); color: var(--danger); }
.solo-badge {
  font-size: 9px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 10px;
  background: var(--bg-card-hover);
  color: var(--text-muted);
}

.show-more-btn {
  width: 100%;
  margin-top: 6px;
  padding: 11px;
  background: transparent;
  border: 1px dashed var(--border-color);
  border-radius: 12px;
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s var(--ease), background 0.15s var(--ease);
}
.show-more-btn:hover {
  border-color: var(--accent);
  background: var(--accent-dim);
}
.show-more-count {
  color: var(--text-muted);
  font-weight: 500;
  font-size: 12px;
  margin-left: 4px;
}
</style>