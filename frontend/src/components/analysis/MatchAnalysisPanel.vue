<script setup>
import { computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  analysis: { type: Object, required: true },
})
const emit = defineEmits(['close'])

const snap = computed(() => props.analysis?.input_snapshot || {})
const report = computed(() => props.analysis?.report_json || {})

const match = computed(() => {
  const fromSnap = snap.value.match
  if (fromSnap && (fromSnap.kills != null || fromSnap.gpm != null)) return fromSnap
  return report.value.match_stats || fromSnap || {}
})

const recent = computed(
  () => snap.value.recent_20 || report.value.recent_stats || {}
)
const deltas = computed(
  () => snap.value.deltas || report.value.deltas || {}
)

const score = computed(() => {
  const s = Number(report.value.score_0_100)
  return Number.isFinite(s) ? Math.min(100, Math.max(0, s)) : 0
})

const form = computed(() => recent.value.form || [])
const strengths = computed(() => report.value.strengths || [])
const weaknesses = computed(
  () => report.value.weaknesses || report.value.weakness || []
)
const recs = computed(() => report.value.recommendations || [])

const won = computed(() => match.value.won)

function fmt(v, digits = 1) {
  if (v == null || v === '' || Number.isNaN(Number(v))) return '—'
  return typeof v === 'number' ? Number(v).toFixed(digits) : String(v)
}

function fmtDelta(v, digits = 1) {
  if (v == null || v === '' || Number.isNaN(Number(v))) return '—'
  const n = Number(v)
  return (n > 0 ? '+' : '') + n.toFixed(digits)
}

function deltaClass(v) {
  if (v == null || v === '' || Number.isNaN(Number(v))) return ''
  const n = Number(v)
  if (n > 0) return 'pos'
  if (n < 0) return 'neg'
  return ''
}

const statCards = computed(() => [
  {
    label: 'K/D',
    value: fmt(match.value.kd ?? safeDiv(match.value.kills, match.value.deaths), 2),
    avg: fmt(recent.value.avg_kd, 2),
    delta: deltas.value.kd_vs_avg,
    digits: 2,
  },
  {
    label: 'Kills',
    value: match.value.kills ?? '—',
    avg: fmt(recent.value.avg_kills, 1),
    delta: deltas.value.kills_vs_avg,
    digits: 1,
  },
  {
    label: 'Deaths',
    value: match.value.deaths ?? '—',
    avg: fmt(recent.value.avg_deaths, 1),
    delta: deltas.value.deaths_vs_avg,
    digits: 1,
  },
  {
    label: 'Assists',
    value: match.value.assists ?? '—',
    avg: fmt(recent.value.avg_assists, 1),
    delta: null,
    digits: 1,
  },
  {
    label: 'GPM',
    value: match.value.gpm ?? '—',
    avg: recent.value.avg_gpm ?? '—',
    delta: deltas.value.gpm_vs_avg,
    digits: 0,
  },
  {
    label: 'XPM',
    value: match.value.xpm ?? '—',
    avg: recent.value.avg_xpm ?? '—',
    delta: deltas.value.xpm_vs_avg,
    digits: 0,
  },
  {
    label: 'Last hits',
    value: match.value.last_hits ?? '—',
    avg: null,
    delta: null,
  },
  {
    label: 'Hero dmg',
    value: match.value.hero_damage ?? '—',
    avg: null,
    delta: null,
  },
  {
    label: 'Tower dmg',
    value: match.value.tower_damage ?? '—',
    avg: null,
    delta: null,
  },
  {
    label: 'Heal',
    value: match.value.hero_healing ?? '—',
    avg: null,
    delta: null,
  },
  {
    label: 'Net worth',
    value: match.value.net_worth ?? '—',
    avg: null,
    delta: null,
  },
  {
    label: 'Level',
    value: match.value.level ?? '—',
    avg: null,
    delta: null,
  },
])

function safeDiv(a, b) {
  if (a == null) return null
  const d = b || 0
  return d ? a / d : a
}

function onKey(e) {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => {
  document.body.style.overflow = 'hidden'
  window.addEventListener('keydown', onKey)
})

onUnmounted(() => {
  document.body.style.overflow = ''
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <!-- Teleport в body — модалка не уезжает вниз из-за transform/overflow родителя -->
  <Teleport to="body">
    <div class="ma-root" @click.self="emit('close')">
      <div class="ma-panel" role="dialog" aria-modal="true" aria-label="Разбор матча">
        <header class="ma-head">
          <div class="ma-head-text">
            <div class="ma-badges">
              <span class="pill game">Dota 2</span>
              <span v-if="won === true" class="pill win">Победа</span>
              <span v-else-if="won === false" class="pill loss">Поражение</span>
              <span v-if="match.duration_min" class="pill mute">{{ match.duration_min }} мин</span>
            </div>
            <h2>{{ report.headline || 'Разбор матча' }}</h2>
            <p class="ma-sub">match {{ analysis.external_match_id }}</p>
          </div>
          <button type="button" class="ma-close" aria-label="Закрыть" @click="emit('close')">
            ✕
          </button>
        </header>

        <div class="ma-scroll">
          <!-- Score hero -->
          <section class="hero">
            <div class="ring" :style="{ '--p': score }">
              <div class="ring-inner">
                <span class="ring-num">{{ score }}</span>
                <span class="ring-lbl">score</span>
              </div>
            </div>
            <div class="hero-copy">
              <p class="one-liner">{{ report.one_liner || 'Краткий вывод появится здесь' }}</p>
              <p v-if="match.kills != null" class="kda-line">
                <b>{{ match.kills }}/{{ match.deaths }}/{{ match.assists }}</b>
                <span>KD {{ fmt(match.kd ?? safeDiv(match.kills, match.deaths), 2) }}</span>
                <span>GPM {{ match.gpm ?? '—' }}</span>
                <span>XPM {{ match.xpm ?? '—' }}</span>
              </p>
              <p v-else class="kda-line muted">
                Нет детальных цифр матча — смотри рекомендации ниже
              </p>
            </div>
          </section>

          <!-- Stats grid -->
          <section class="block">
            <div class="block-title">
              <span>Матч vs форма</span>
              <span v-if="recent.matches" class="block-meta">
                {{ recent.winrate ?? '—' }}% WR · {{ recent.matches }} игр
              </span>
            </div>
            <div class="stat-grid">
              <div v-for="s in statCards" :key="s.label" class="stat-card">
                <span class="s-label">{{ s.label }}</span>
                <span class="s-value">{{ s.value }}</span>
                <span v-if="s.avg != null" class="s-avg">ср. {{ s.avg }}</span>
                <span
                  v-if="s.delta != null && s.delta !== ''"
                  class="s-delta"
                  :class="deltaClass(s.delta)"
                >
                  {{ fmtDelta(s.delta, s.digits ?? 1) }}
                </span>
              </div>
            </div>

            <div v-if="form.length" class="form-row">
              <span class="form-lbl">Форма</span>
              <span
                v-for="(f, i) in form"
                :key="i"
                class="form-chip"
                :class="f === 'W' ? 'win' : 'loss'"
              >{{ f }}</span>
            </div>
          </section>

          <!-- Strengths / Weaknesses -->
          <div class="two-col">
            <section class="block">
              <div class="block-title ok">Сильные стороны</div>
              <div v-if="!strengths.length" class="empty">Пока не выделено</div>
              <article v-for="(s, i) in strengths" :key="'s' + i" class="insight ok">
                <b>{{ s.title }}</b>
                <p>{{ s.detail }}</p>
                <code v-if="s.evidence">{{ s.evidence }}</code>
              </article>
            </section>

            <section class="block">
              <div class="block-title bad">Слабые стороны</div>
              <div v-if="!weaknesses.length" class="empty">Пока не выделено</div>
              <article v-for="(s, i) in weaknesses" :key="'w' + i" class="insight bad">
                <b>{{ s.title }}</b>
                <p>{{ s.detail }}</p>
                <code v-if="s.evidence">{{ s.evidence }}</code>
              </article>
            </section>
          </div>

          <!-- Recommendations -->
          <section class="block">
            <div class="block-title">Что делать</div>
            <ol class="recs">
              <li v-for="(r, i) in recs" :key="'r' + i">
                <span class="rec-n">{{ r.priority || i + 1 }}</span>
                <div>
                  <b>{{ r.action }}</b>
                  <p v-if="r.why">{{ r.why }}</p>
                </div>
              </li>
            </ol>
            <div v-if="!recs.length" class="empty">Нет рекомендаций</div>
          </section>

          <p class="foot">
            OpenDota · KDA, GPM, XPM, урон, форма · без реплея
            <template v-if="analysis.model_name"> · {{ analysis.model_name }}</template>
          </p>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
/* ===== Overlay: всегда центр экрана ===== */
.ma-root {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: max(12px, 3vh) 12px;
  background: rgba(6, 6, 8, 0.78);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  overflow-y: auto;
  overscroll-behavior: contain;
}

.ma-panel {
  width: min(720px, 100%);
  max-height: min(90vh, 920px);
  display: flex;
  flex-direction: column;
  margin: auto;
  background:
    radial-gradient(ellipse 90% 60% at 100% 0%, rgba(196, 165, 116, 0.12), transparent 55%),
    var(--bg-card, #16141a);
  border: 1px solid var(--border-color, #2a2830);
  border-radius: 16px;
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.03) inset,
    0 28px 80px rgba(0, 0, 0, 0.65);
  overflow: hidden;
}

/* Header */
.ma-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--border-color, #2a2830);
  flex-shrink: 0;
}
.ma-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.pill {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 3px 9px;
  border-radius: 999px;
}
.pill.game {
  background: var(--accent-dim, rgba(196, 165, 116, 0.15));
  color: var(--accent, #c4a574);
  border: 1px solid color-mix(in srgb, var(--accent, #c4a574) 35%, transparent);
}
.pill.win {
  background: rgba(106, 170, 124, 0.15);
  color: var(--success, #6aaa7c);
}
.pill.loss {
  background: rgba(230, 57, 70, 0.12);
  color: var(--danger, #e63946);
}
.pill.mute {
  background: var(--bg-sunken, #1c1a22);
  color: var(--text-muted, #8a8694);
}
.ma-head h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 750;
  letter-spacing: -0.02em;
  line-height: 1.25;
  color: var(--text-primary, #f0ece4);
}
.ma-sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--text-muted, #8a8694);
  font-family: var(--font-mono, ui-monospace, monospace);
}
.ma-close {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 1px solid var(--border-color, #2a2830);
  background: var(--bg-sunken, #1c1a22);
  color: var(--text-muted, #8a8694);
  font-size: 16px;
  cursor: pointer;
  flex-shrink: 0;
}
.ma-close:hover {
  border-color: var(--accent, #c4a574);
  color: var(--accent, #c4a574);
}

.ma-scroll {
  overflow-y: auto;
  padding: 16px 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  -webkit-overflow-scrolling: touch;
}

/* Hero score */
.hero {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 14px 16px;
  border-radius: 14px;
  background: var(--bg-sunken, #1c1a22);
  border: 1px solid var(--border-color, #2a2830);
}
.ring {
  --p: 0;
  width: 76px;
  height: 76px;
  border-radius: 50%;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  background: conic-gradient(
    var(--accent, #c4a574) calc(var(--p) * 1%),
    rgba(255, 255, 255, 0.06) 0
  );
}
.ring-inner {
  width: 58px;
  height: 58px;
  border-radius: 50%;
  background: var(--bg-card, #16141a);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0;
}
.ring-num {
  font-size: 20px;
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.ring-lbl {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted, #8a8694);
  font-weight: 600;
}
.hero-copy {
  min-width: 0;
  flex: 1;
}
.one-liner {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.4;
  color: var(--text-primary, #f0ece4);
}
.kda-line {
  margin: 8px 0 0;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
  color: var(--text-secondary, #b8b4ac);
  font-family: var(--font-mono, ui-monospace, monospace);
}
.kda-line b {
  color: var(--text-primary, #f0ece4);
}
.kda-line.muted {
  color: var(--text-muted, #8a8694);
}

/* Blocks */
.block-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted, #8a8694);
}
.block-title.ok { color: var(--success, #6aaa7c); }
.block-title.bad { color: var(--danger, #e63946); }
.block-meta {
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0;
  font-size: 11px;
  color: var(--text-secondary, #b8b4ac);
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(104px, 1fr));
  gap: 8px;
}
.stat-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 11px;
  border-radius: 10px;
  background: var(--bg-sunken, #1c1a22);
  border: 1px solid var(--border-color, #2a2830);
  min-width: 0;
}
.s-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted, #8a8694);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.s-value {
  font-size: 17px;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono, ui-monospace, monospace);
  color: var(--text-primary, #f0ece4);
  line-height: 1.2;
}
.s-avg {
  font-size: 10px;
  color: var(--text-muted, #8a8694);
}
.s-delta {
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-mono, ui-monospace, monospace);
}
.s-delta.pos { color: var(--success, #6aaa7c); }
.s-delta.neg { color: var(--danger, #e63946); }

.form-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
}
.form-lbl {
  font-size: 11px;
  color: var(--text-muted, #8a8694);
  margin-right: 4px;
}
.form-chip {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: grid;
  place-items: center;
  font-size: 10px;
  font-weight: 800;
}
.form-chip.win {
  background: rgba(106, 170, 124, 0.15);
  color: var(--success, #6aaa7c);
}
.form-chip.loss {
  background: rgba(230, 57, 70, 0.12);
  color: var(--danger, #e63946);
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media (max-width: 560px) {
  .two-col { grid-template-columns: 1fr; }
  .hero { flex-direction: column; align-items: flex-start; }
}

.insight {
  padding: 11px 12px;
  border-radius: 10px;
  margin-bottom: 8px;
  background: var(--bg-sunken, #1c1a22);
  border: 1px solid var(--border-color, #2a2830);
}
.insight.ok {
  border-color: color-mix(in srgb, var(--success, #6aaa7c) 40%, transparent);
}
.insight.bad {
  border-color: color-mix(in srgb, var(--danger, #e63946) 40%, transparent);
}
.insight b {
  display: block;
  font-size: 13px;
  margin-bottom: 4px;
  color: var(--text-primary, #f0ece4);
}
.insight p {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--text-secondary, #b8b4ac);
}
.insight code {
  display: block;
  margin-top: 6px;
  font-size: 10px;
  color: var(--text-muted, #8a8694);
  font-family: var(--font-mono, ui-monospace, monospace);
}

.recs {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.recs li {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 12px;
  border-radius: 10px;
  background: var(--bg-sunken, #1c1a22);
  border: 1px solid var(--border-color, #2a2830);
}
.rec-n {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 800;
  color: var(--accent, #c4a574);
  background: var(--accent-dim, rgba(196, 165, 116, 0.15));
  border: 1px solid color-mix(in srgb, var(--accent, #c4a574) 35%, transparent);
}
.recs b {
  display: block;
  font-size: 13px;
  margin-bottom: 2px;
  color: var(--text-primary, #f0ece4);
}
.recs p {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary, #b8b4ac);
  line-height: 1.4;
}

.empty {
  font-size: 12px;
  color: var(--text-muted, #8a8694);
  padding: 4px 0;
}

.foot {
  margin: 0;
  font-size: 11px;
  color: var(--text-muted, #8a8694);
  line-height: 1.4;
  text-align: center;
}
</style>