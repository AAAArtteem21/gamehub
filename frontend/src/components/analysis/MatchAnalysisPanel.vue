<script setup>
import { computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  analysis: { type: Object, required: true },
})
const emit = defineEmits(['close'])

const snap = computed(() => props.analysis?.input_snapshot || {})
const report = computed(() => props.analysis?.report_json || {})
const match = computed(() => snap.value.match || {})
const recent = computed(() => snap.value.recent_20 || snap.value.recent || {})
const deltas = computed(() => snap.value.deltas || {})

const score = computed(() => Number(report.value.score_0_100 ?? 0))
const form = computed(() => recent.value.form || [])

const k = computed(() => match.value.kills)
const d = computed(() => match.value.deaths)
const a = computed(() => match.value.assists)
const kd = computed(() => match.value.kd ?? calcKd(k.value, d.value))
const kda = computed(() => match.value.kda ?? calcKda(k.value, d.value, a.value))

function calcKd(kills, deaths) {
  if (kills == null) return null
  const dd = deaths || 0
  return dd ? +(kills / dd).toFixed(2) : +kills
}
function calcKda(kills, deaths, assists) {
  if (kills == null) return null
  const dd = deaths || 0
  return dd ? +((kills + (assists || 0)) / dd).toFixed(2) : +(kills + (assists || 0))
}

function deltaClass(v) {
  if (v == null || v === '') return ''
  const n = Number(v)
  if (n > 0) return 'pos'
  if (n < 0) return 'neg'
  return ''
}
function fmt(v, digits = 1) {
  if (v == null || v === '' || Number.isNaN(Number(v))) return '—'
  return typeof v === 'number' ? Number(v).toFixed(digits) : v
}
function fmtDelta(v, digits = 1) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  if (Number.isNaN(n)) return '—'
  const s = n > 0 ? '+' : ''
  return s + n.toFixed(digits)
}

onMounted(() => {
  document.body.style.overflow = 'hidden'
})
onUnmounted(() => {
  document.body.style.overflow = ''
})
</script>

<template>
  <div class="ma-backdrop" @click.self="emit('close')">
    <div class="ma-panel" role="dialog" aria-modal="true" aria-label="Разбор матча">
      <header class="ma-head">
        <div>
          <h2>{{ report.headline || 'Разбор матча' }}</h2>
          <p class="sub">
            Dota 2 · #{{ analysis.external_match_id }}
            <span v-if="match.won === true" class="tag win">Победа</span>
            <span v-else-if="match.won === false" class="tag loss">Поражение</span>
            <span v-if="match.duration_min" class="tag muted">{{ match.duration_min }} мин</span>
            <span v-if="match.hero_id" class="tag muted">hero {{ match.hero_id }}</span>
          </p>
        </div>
        <button type="button" class="x" aria-label="Закрыть" @click="emit('close')">✕</button>
      </header>

      <div class="ma-body">
        <!-- Score -->
        <div class="score-row">
          <div class="score-ring" :style="{ '--p': Math.min(100, Math.max(0, score)) }">
            <span>{{ score }}</span>
          </div>
          <div class="score-text">
            <p class="one-liner">{{ report.one_liner || '—' }}</p>
            <p v-if="match.kills != null" class="kda-line">
              {{ match.kills }}/{{ match.deaths }}/{{ match.assists }}
              · KD {{ fmt(kd, 2) }} · KDA {{ fmt(kda, 2) }}
              · GPM {{ match.gpm ?? '—' }} · XPM {{ match.xpm ?? '—' }}
            </p>
          </div>
        </div>

        <!-- vs form -->
        <section class="block">
          <h3>Матч vs твоя форма ({{ recent.matches || 0 }} игр)</h3>
          <div class="bars">
            <div class="bar-item">
              <span class="lbl">K/D</span>
              <span class="val">{{ fmt(kd, 2) }}</span>
              <span class="avg">ср. {{ fmt(recent.avg_kd, 2) }}</span>
              <span class="delta" :class="deltaClass(deltas.kd_vs_avg)">{{ fmtDelta(deltas.kd_vs_avg, 2) }}</span>
            </div>
            <div class="bar-item">
              <span class="lbl">Kills</span>
              <span class="val">{{ k ?? '—' }}</span>
              <span class="avg">ср. {{ fmt(recent.avg_kills, 1) }}</span>
              <span class="delta" :class="deltaClass(deltas.kills_vs_avg)">{{ fmtDelta(deltas.kills_vs_avg, 1) }}</span>
            </div>
            <div class="bar-item">
              <span class="lbl">Deaths</span>
              <span class="val">{{ d ?? '—' }}</span>
              <span class="avg">ср. {{ fmt(recent.avg_deaths, 1) }}</span>
              <span class="delta" :class="deltaClass(deltas.deaths_vs_avg)">{{ fmtDelta(deltas.deaths_vs_avg, 1) }}</span>
            </div>
            <div class="bar-item">
              <span class="lbl">Assists</span>
              <span class="val">{{ a ?? '—' }}</span>
              <span class="avg">ср. {{ fmt(recent.avg_assists, 1) }}</span>
            </div>
            <div class="bar-item">
              <span class="lbl">GPM</span>
              <span class="val">{{ match.gpm ?? '—' }}</span>
              <span class="avg">ср. {{ recent.avg_gpm ?? '—' }}</span>
              <span class="delta" :class="deltaClass(deltas.gpm_vs_avg)">{{ fmtDelta(deltas.gpm_vs_avg, 0) }}</span>
            </div>
            <div class="bar-item">
              <span class="lbl">XPM</span>
              <span class="val">{{ match.xpm ?? '—' }}</span>
              <span class="avg">ср. {{ recent.avg_xpm ?? '—' }}</span>
              <span class="delta" :class="deltaClass(deltas.xpm_vs_avg)">{{ fmtDelta(deltas.xpm_vs_avg, 0) }}</span>
            </div>
            <div class="bar-item">
              <span class="lbl">Last hits</span>
              <span class="val">{{ match.last_hits ?? '—' }}</span>
            </div>
            <div class="bar-item">
              <span class="lbl">Hero dmg</span>
              <span class="val">{{ match.hero_damage ?? '—' }}</span>
            </div>
            <div class="bar-item">
              <span class="lbl">Tower dmg</span>
              <span class="val">{{ match.tower_damage ?? '—' }}</span>
            </div>
            <div class="bar-item">
              <span class="lbl">Heal</span>
              <span class="val">{{ match.hero_healing ?? '—' }}</span>
            </div>
            <div class="bar-item">
              <span class="lbl">Net worth</span>
              <span class="val">{{ match.net_worth ?? '—' }}</span>
            </div>
            <div class="bar-item">
              <span class="lbl">Level</span>
              <span class="val">{{ match.level ?? '—' }}</span>
            </div>
          </div>

          <div class="form-row">
            <span class="lbl">Форма</span>
            <span
              v-for="(f, i) in form"
              :key="i"
              class="chip"
              :class="f === 'W' ? 'win' : 'loss'"
            >{{ f }}</span>
            <span v-if="recent.winrate != null" class="wr">
              {{ recent.winrate }}% WR · {{ recent.wins }}/{{ recent.matches }}
            </span>
          </div>
        </section>

        <div class="cols">
          <section class="block">
            <h3>Сильные стороны</h3>
            <div v-if="!(report.strengths || []).length" class="empty">Пока не выделено</div>
            <article v-for="(s, i) in report.strengths || []" :key="'s'+i" class="card ok">
              <b>{{ s.title }}</b>
              <p>{{ s.detail }}</p>
              <code v-if="s.evidence">{{ s.evidence }}</code>
            </article>
          </section>
          <section class="block">
            <h3>Слабые стороны</h3>
            <div v-if="!(report.weaknesses || []).length" class="empty">Пока не выделено</div>
            <article v-for="(s, i) in report.weaknesses || []" :key="'w'+i" class="card bad">
              <b>{{ s.title }}</b>
              <p>{{ s.detail }}</p>
              <code v-if="s.evidence">{{ s.evidence }}</code>
            </article>
          </section>
        </div>

        <section class="block">
          <h3>Что делать дальше</h3>
          <ol class="recs">
            <li v-for="(r, i) in report.recommendations || []" :key="'r'+i">
              <b>{{ r.action }}</b>
              <span v-if="r.why">{{ r.why }}</span>
            </li>
          </ol>
        </section>

        <p class="disclaimer">
          OpenDota: KDA, GPM, XPM, урон, форма. Без реплея и vision.
          <template v-if="analysis.model_name"> · {{ analysis.model_name }}</template>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Фикс «уезжает вниз»: overlay на весь viewport, панель по центру экрана */
.ma-backdrop {
  position: fixed;
  inset: 0;
  z-index: 5000;
  background: rgba(0, 0, 0, 0.72);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.ma-panel {
  width: min(680px, 100%);
  max-height: min(88vh, 900px);
  overflow: auto;
  margin: auto;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 12px);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.55);
  flex-shrink: 0;
}

.ma-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  background: var(--bg-card);
  z-index: 1;
}
.ma-head h2 { margin: 0; font-size: 16px; font-weight: 700; }
.sub { margin: 6px 0 0; font-size: 12px; color: var(--text-muted); display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.x {
  background: none; border: none; color: var(--text-muted);
  cursor: pointer; font-size: 18px; padding: 4px 8px; flex-shrink: 0;
}

.tag {
  display: inline-block;
  padding: 1px 8px; border-radius: 999px; font-size: 10px; font-weight: 700;
}
.tag.win { background: rgba(106,170,124,.15); color: var(--success, #6aaa7c); }
.tag.loss { background: rgba(230,57,70,.12); color: var(--danger, #e63946); }
.tag.muted { background: var(--bg-sunken); color: var(--text-muted); }

.ma-body { padding: 16px 18px 24px; display: flex; flex-direction: column; gap: 18px; }

.score-row { display: flex; align-items: center; gap: 16px; }
.score-ring {
  --p: 50;
  width: 68px; height: 68px; border-radius: 50%; flex-shrink: 0;
  display: grid; place-items: center;
  background: conic-gradient(var(--accent) calc(var(--p) * 1%), var(--bg-sunken) 0);
  font-weight: 800; font-size: 18px;
}
.score-ring span {
  width: 52px; height: 52px; border-radius: 50%;
  background: var(--bg-card); display: grid; place-items: center;
}
.score-text { min-width: 0; }
.one-liner { margin: 0; font-size: 14px; line-height: 1.4; font-weight: 600; }
.kda-line {
  margin: 6px 0 0; font-size: 12px; color: var(--text-secondary);
  font-family: var(--font-mono, monospace);
}

.block h3 {
  margin: 0 0 10px; font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .04em; color: var(--text-muted);
}
.bars {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 8px;
}
.bar-item {
  background: var(--bg-sunken); border: 1px solid var(--border-color);
  border-radius: 8px; padding: 10px; display: flex; flex-direction: column; gap: 2px;
}
.bar-item .lbl { font-size: 10px; color: var(--text-muted); font-weight: 600; }
.bar-item .val { font-size: 16px; font-weight: 700; font-family: var(--font-mono, monospace); }
.bar-item .avg { font-size: 10px; color: var(--text-muted); }
.delta { font-size: 11px; font-weight: 600; color: var(--text-muted); }
.delta.pos { color: var(--success, #6aaa7c); }
.delta.neg { color: var(--danger, #e63946); }

.form-row {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 12px;
}
.form-row .lbl { font-size: 11px; color: var(--text-muted); margin-right: 4px; }
.chip {
  width: 22px; height: 22px; border-radius: 6px;
  display: grid; place-items: center; font-size: 10px; font-weight: 800;
}
.chip.win { background: rgba(106,170,124,.15); color: var(--success, #6aaa7c); }
.chip.loss { background: rgba(230,57,70,.12); color: var(--danger, #e63946); }
.wr { font-size: 11px; color: var(--text-muted); margin-left: 6px; }

.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
@media (max-width: 560px) { .cols { grid-template-columns: 1fr; } }

.card {
  padding: 10px 12px; border-radius: 8px; margin-bottom: 8px;
  border: 1px solid var(--border-color); background: var(--bg-sunken);
}
.card.ok { border-color: color-mix(in srgb, var(--success, #6aaa7c) 35%, transparent); }
.card.bad { border-color: color-mix(in srgb, var(--danger, #e63946) 35%, transparent); }
.card b { display: block; font-size: 13px; margin-bottom: 4px; }
.card p { margin: 0; font-size: 12px; color: var(--text-secondary); line-height: 1.45; }
.card code {
  display: block; margin-top: 6px; font-size: 10px;
  color: var(--text-muted); font-family: var(--font-mono, monospace);
}
.empty { font-size: 12px; color: var(--text-muted); }

.recs { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 10px; }
.recs li { font-size: 13px; }
.recs b { display: block; margin-bottom: 2px; }
.recs span { font-size: 12px; color: var(--text-secondary); }

.disclaimer { margin: 0; font-size: 11px; color: var(--text-muted); line-height: 1.4; }
</style>