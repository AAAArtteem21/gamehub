<script setup>
import { ref, computed, watch } from 'vue'
import { analysisApi } from '../../api/analysis'
import MatchAnalysisPanel from '../analysis/MatchAnalysisPanel.vue'
import { useAuthStore } from '../../stores/auth'

const props = defineProps({
  matches: { type: Array, default: () => [] },
  initialLimit: { type: Number, default: 8 },
  canOpenParticipants: { type: Boolean, default: true },
  /** показывать кнопку AI-разбора (только свой профиль доты) */
  enableAnalysis: { type: Boolean, default: false },
})
const emit = defineEmits(['open-match'])

const auth = useAuthStore()
const expandedIndex = ref(null)
const limit = ref(props.initialLimit)

const analysis = ref(null)
const loadingId = ref(null)
const analyzeError = ref(null)

const visibleMatches = computed(() => (props.matches || []).slice(0, limit.value))
const canShowMore = computed(() => (props.matches || []).length > limit.value)

watch(
  () => props.matches,
  () => {
    expandedIndex.value = null
    limit.value = props.initialLimit
    analyzeError.value = null
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

async function analyzeMatch(m) {
  if (!m?.match_id) return
  if (!auth.requireAuth('Войди через Steam, чтобы разобрать матч')) return

  loadingId.value = m.match_id
  analyzeError.value = null
  try {
    const res = await analysisApi.createDota(m.match_id)
    if (res.data.status === 'failed') {
      analyzeError.value = res.data.error_message || 'Не удалось разобрать матч'
      return
    }
    analysis.value = res.data
  } catch (e) {
    analyzeError.value =
      e.response?.data?.detail ||
      e.response?.data?.error_message ||
      'Ошибка анализа'
  } finally {
    loadingId.value = null
  }
}
</script>

<template>
  <div class="match-history" v-if="matches?.length">
    <h4>История матчей</h4>

    <p v-if="analyzeError" class="analyze-err">{{ analyzeError }}</p>

    <div
      v-for="(m, i) in visibleMatches"
      :key="m.match_id || i"
      class="match-row"
      :class="{ win: m.won === true, loss: m.won === false }"
    >
      <div class="match-summary" @click="toggle(i)">
        <span
          class="result-badge"
          v-if="m.won !== null && m.won !== undefined"
        >
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
            <span
              class="verdict-badge"
              v-if="m.verdict"
              :class="m.verdict.tone"
            >{{ m.verdict.label }}</span>
            <span class="solo-badge" v-if="m.solo">Соло</span>
          </div>
          <span v-if="m.played_at">{{ m.played_at }}</span>
          <span v-if="m.duration">{{ m.duration }}</span>
        </div>
        <span class="expand-arrow">{{ expandedIndex === i ? '▲' : '▼' }}</span>
      </div>

      <transition name="expand">
        <div class="match-details-expanded" v-if="expandedIndex === i">
          <div
            class="detail-item"
            v-for="d in (m.details || [])"
            :key="d.label"
          >
            <span class="detail-label">{{ d.label }}</span>
            <span class="detail-value">{{ d.value }}</span>
          </div>

          <div class="match-actions" v-if="m.match_id">
            <button
              type="button"
              class="view-participants-btn"
              v-if="canOpenParticipants"
              @click.stop="openParticipants(m)"
            >
              Кто играл
            </button>

            <button
              v-if="enableAnalysis"
              type="button"
              class="btn-analyze"
              :disabled="loadingId === m.match_id"
              @click.stop="analyzeMatch(m)"
            >
              {{ loadingId === m.match_id ? 'Анализ…' : 'Разбор AI' }}
            </button>
          </div>
        </div>
      </transition>
    </div>

    <button
      v-if="canShowMore"
      type="button"
      class="show-more-btn"
      @click="showMore"
    >
      Показать ещё
      <span class="show-more-count">
        ({{ visibleMatches.length }} / {{ matches.length }})
      </span>
    </button>

    <MatchAnalysisPanel
      v-if="analysis"
      :analysis="analysis"
      @close="analysis = null"
    />
  </div>
</template>

<style scoped>
.match-history {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.match-history h4 {
  margin: 0 0 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.analyze-err {
  margin: 0 0 6px;
  font-size: 12px;
  color: var(--danger);
}

.match-row {
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  border-left: 2px solid var(--border-color);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.match-row:hover {
  border-color: var(--border-hover);
}
.match-row.win {
  border-left-color: var(--success);
}
.match-row.loss {
  border-left-color: var(--danger);
}

.match-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  cursor: pointer;
}

.result-badge {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
  font-family: var(--font-mono);
}
.match-row.win .result-badge {
  background: rgba(106, 170, 124, 0.15);
  color: var(--success);
}
.match-row.loss .result-badge {
  background: rgba(201, 122, 114, 0.15);
  color: var(--danger);
}

.match-main {
  flex: 1;
  min-width: 0;
}
.match-top {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}
.match-title {
  font-weight: 600;
  font-size: 13px;
}
.match-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  font-family: var(--font-mono);
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
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.expand-arrow {
  font-size: 9px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.match-details-expanded {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
  padding: 10px 12px 12px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-card);
}
.detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.detail-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.detail-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.match-actions {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 2px;
}

.view-participants-btn {
  flex: 1;
  min-width: 120px;
  background: var(--accent-dim);
  border: 1px solid rgba(196, 165, 116, 0.25);
  color: var(--accent);
  padding: 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.view-participants-btn:hover {
  background: var(--accent);
  color: #12100c;
  border-color: var(--accent);
}

.btn-analyze {
  flex: 1;
  min-width: 120px;
  background: transparent;
  border: 1px solid var(--accent);
  color: var(--accent);
  padding: 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}
.btn-analyze:hover:not(:disabled) {
  background: var(--accent);
  color: #12100c;
}
.btn-analyze:disabled {
  opacity: 0.6;
  cursor: default;
}

.expand-enter-active,
.expand-leave-active {
  transition: opacity 0.15s var(--ease);
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
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
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 3px;
  text-transform: uppercase;
}
.verdict-badge.great {
  background: rgba(106, 170, 124, 0.18);
  color: var(--success);
}
.verdict-badge.good {
  background: var(--accent-dim);
  color: var(--accent);
}
.verdict-badge.neutral {
  background: var(--bg-card-hover);
  color: var(--text-secondary);
}
.verdict-badge.bad {
  background: rgba(196, 163, 90, 0.15);
  color: var(--warning);
}
.verdict-badge.terrible {
  background: rgba(201, 122, 114, 0.18);
  color: var(--danger);
}
.solo-badge {
  font-size: 9px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 3px;
  background: var(--bg-card-hover);
  color: var(--text-muted);
}

.show-more-btn {
  width: 100%;
  margin-top: 4px;
  padding: 10px;
  background: transparent;
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--accent);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}
.show-more-btn:hover {
  border-color: var(--accent);
  background: var(--accent-dim);
}
.show-more-count {
  color: var(--text-muted);
  font-weight: 500;
  font-size: 11px;
  margin-left: 4px;
}
</style>