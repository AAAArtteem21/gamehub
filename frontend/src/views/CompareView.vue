<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/axios'

const route = useRoute()
const router = useRouter()
const data = ref(null)
const error = ref(null)
const loading = ref(true)
const selectedGame = ref('')

const baseParams = computed(() => {
  const p = {}
  if (route.query.user_id) p.user_id = route.query.user_id
  if (route.query.platform) p.platform = route.query.platform
  if (route.query.external_id) p.external_id = route.query.external_id
  return p
})

/** Строки детализации: показываем, если хоть у одной стороны есть значение */
const DETAIL_ROWS = [
  { key: 'elo', label: 'ELO', faceit: true },
  { key: 'level', label: 'Faceit Level', faceit: true },
  { key: 'skill_rating', label: 'Rating / MMR' },
  { key: 'kd', label: 'K/D', faceit: true },
  { key: 'adr', label: 'ADR', faceit: true },
  { key: 'avg_kills', label: 'Ср. килы (20)', faceit: true },
  { key: 'avg_kd_recent', label: 'K/D (20)', faceit: true },
  { key: 'hs_percent', label: 'HS %', faceit: true },
  { key: 'avg_kda', label: 'Ср. KDA' },
  { key: 'rr', label: 'RR', valorant: true },
  { key: 'main_agent', label: 'Мейн', valorant: true },
  { key: 'win_streak', label: 'Серия побед' },
]

function cell(stats, key) {
  if (!stats) return null
  if (key === 'skill_rating') {
    return stats.skill_rating ?? stats.extra?.mmr ?? stats.elo ?? null
  }
  if (key === 'elo') return stats.elo ?? stats.extra?.faceit_elo ?? null
  if (key === 'level') return stats.level ?? stats.extra?.skill_level ?? null
  if (key === 'hs_percent') return stats.hs_percent ?? stats.extra?.headshot_pct ?? null
  const v = stats[key]
  return v === undefined || v === null || v === '' ? null : v
}

function showRow(key) {
  if (!data.value) return false
  const a = cell(data.value.me?.stats, key)
  const b = cell(data.value.other?.stats, key)
  return a != null || b != null
}

function rankLabel(stats) {
  if (!stats) return '—'
  if (stats.tier) return stats.tier
  if (stats.level != null) return `Level ${stats.level}`
  const rt = stats.extra?.rank_tier
  if (rt == null || rt === '') return '—'
  return String(rt)
}

function formClass(c) {
  return c === 'W' ? 'w' : 'l'
}

function betterClass(key, side) {
  const a = cell(data.value?.me?.stats, key)
  const b = cell(data.value?.other?.stats, key)
  if (a == null || b == null) return ''
  const na = Number(a)
  const nb = Number(b)
  if (Number.isNaN(na) || Number.isNaN(nb)) return ''
  if (na === nb) return ''
  const higherWins = !['losses'].includes(key)
  const win = higherWins ? na > nb : na < nb
  if (side === 'me') return win ? 'better' : 'worse'
  return win ? 'worse' : 'better'
}

async function load() {
  if (!baseParams.value.user_id && !(baseParams.value.platform && baseParams.value.external_id)) {
    error.value = 'Не указан игрок'
    loading.value = false
    return
  }
  loading.value = true
  error.value = null
  try {
    const params = { ...baseParams.value }
    if (selectedGame.value) params.game = selectedGame.value
    const res = await api.get('players/compare/', { params })
    data.value = res.data
    if (!selectedGame.value && res.data.game) {
      selectedGame.value = res.data.game
    }
  } catch (e) {
    error.value = e.response?.data?.detail || 'Не удалось сравнить'
    data.value = null
  } finally {
    loading.value = false
  }
}

function setGame(g) {
  selectedGame.value = g
  load()
}

onMounted(load)
watch(
  () => route.query,
  () => {
    selectedGame.value = ''
    load()
  }
)
</script>

<template>
  <div class="compare-page">
    <button type="button" class="back" @click="router.back()">← Назад</button>
    <h1>Сравнение игроков</h1>

    <div class="game-tabs" v-if="data?.available_games?.length">
      <button
        v-for="g in data.available_games"
        :key="g.value"
        type="button"
        class="game-tab"
        :class="{ active: selectedGame === g.value, common: g.common }"
        @click="setGame(g.value)"
      >
        {{ g.label }}
        <span v-if="!g.common" class="hint">1 сторона</span>
      </button>
    </div>

    <div v-if="loading" class="state">Загрузка...</div>
    <div v-else-if="error" class="state err">{{ error }}</div>

    <template v-else-if="data">
      <div class="diff-bar" v-if="data.diff">
        <span v-if="data.diff.winrate != null">
          Δ винрейт:
          <b :class="data.diff.winrate >= 0 ? 'w' : 'l'">
            {{ data.diff.winrate > 0 ? '+' : '' }}{{ data.diff.winrate }}%
          </b>
        </span>
        <span v-if="data.diff.elo != null">
          Δ ELO:
          <b :class="data.diff.elo >= 0 ? 'w' : 'l'">
            {{ data.diff.elo > 0 ? '+' : '' }}{{ data.diff.elo }}
          </b>
        </span>
        <span v-if="data.diff.kd != null">
          Δ K/D:
          <b :class="data.diff.kd >= 0 ? 'w' : 'l'">
            {{ data.diff.kd > 0 ? '+' : '' }}{{ data.diff.kd }}
          </b>
        </span>
        <span v-if="data.diff.adr != null">
          Δ ADR:
          <b :class="data.diff.adr >= 0 ? 'w' : 'l'">
            {{ data.diff.adr > 0 ? '+' : '' }}{{ data.diff.adr }}
          </b>
        </span>
        <span v-if="data.diff.wins != null">
          Δ побед: <b>{{ data.diff.wins > 0 ? '+' : '' }}{{ data.diff.wins }}</b>
        </span>
      </div>

      <div class="grid">
        <div class="card side" v-for="key in ['me', 'other']" :key="key">
          <div class="head">
            <div
              class="av"
              :style="data[key]?.avatar_url ? { backgroundImage: `url(${data[key].avatar_url})` } : {}"
            >
              <span v-if="!data[key]?.avatar_url">
                {{ (data[key]?.display_name || '?')[0] }}
              </span>
            </div>
            <div>
              <h2>{{ data[key]?.display_name || '—' }}</h2>
              <p class="user" v-if="data[key]?.username">@{{ data[key].username }}</p>
              <p class="muted" v-else-if="data[key]?.kind === 'guest'">Гостевой профиль</p>
            </div>
          </div>

          <template v-if="data[key]?.stats">
            <p class="game">{{ data[key].stats.label || data[key].stats.game_label }}</p>
            <p class="nick" v-if="data[key].stats.nickname">{{ data[key].stats.nickname }}</p>

            <div class="metrics">
              <div>
                <b>{{ data[key].stats.winrate ?? '—' }}%</b>
                <span>винрейт</span>
              </div>
              <div>
                <b class="w">{{ data[key].stats.wins ?? 0 }}</b>
                <span>побед</span>
              </div>
              <div>
                <b class="l">{{ data[key].stats.losses ?? 0 }}</b>
                <span>пораж.</span>
              </div>
              <div>
                <b>{{ data[key].stats.matches ?? 0 }}</b>
                <span>матчей</span>
              </div>
            </div>

            <!-- Faceit quick strip -->
            <div
              class="faceit-strip"
              v-if="data[key].stats.platform === 'faceit' || data[key].stats.key === 'cs2'"
            >
              <div v-if="cell(data[key].stats, 'elo') != null">
                <b>{{ cell(data[key].stats, 'elo') }}</b>
                <span>ELO</span>
              </div>
              <div v-if="cell(data[key].stats, 'level') != null">
                <b>{{ cell(data[key].stats, 'level') }}</b>
                <span>LVL</span>
              </div>
              <div v-if="cell(data[key].stats, 'kd') != null">
                <b>{{ cell(data[key].stats, 'kd') }}</b>
                <span>K/D</span>
              </div>
              <div v-if="cell(data[key].stats, 'adr') != null">
                <b>{{ cell(data[key].stats, 'adr') }}</b>
                <span>ADR</span>
              </div>
            </div>

            <div class="detail-grid">
              <div class="drow" v-if="showRow('elo')">
                <span>ELO</span>
                <b :class="betterClass('elo', key)">{{ cell(data[key].stats, 'elo') ?? '—' }}</b>
              </div>
              <div class="drow" v-if="showRow('level')">
                <span>Faceit Level</span>
                <b :class="betterClass('level', key)">{{ cell(data[key].stats, 'level') ?? '—' }}</b>
              </div>
              <div class="drow" v-if="showRow('skill_rating')">
                <span>Rating / MMR</span>
                <b :class="betterClass('skill_rating', key)">
                  {{ cell(data[key].stats, 'skill_rating') ?? '—' }}
                </b>
              </div>
              <div class="drow">
                <span>Ранг</span>
                <b>{{ rankLabel(data[key].stats) }}</b>
              </div>
              <div class="drow" v-if="showRow('kd')">
                <span>K/D</span>
                <b :class="betterClass('kd', key)">{{ cell(data[key].stats, 'kd') ?? '—' }}</b>
              </div>
              <div class="drow" v-if="showRow('adr')">
                <span>ADR</span>
                <b :class="betterClass('adr', key)">{{ cell(data[key].stats, 'adr') ?? '—' }}</b>
              </div>
              <div class="drow" v-if="showRow('avg_kills')">
                <span>Ср. килы (20)</span>
                <b :class="betterClass('avg_kills', key)">
                  {{ cell(data[key].stats, 'avg_kills') ?? '—' }}
                </b>
              </div>
              <div class="drow" v-if="showRow('avg_kd_recent')">
                <span>K/D (20)</span>
                <b :class="betterClass('avg_kd_recent', key)">
                  {{ cell(data[key].stats, 'avg_kd_recent') ?? '—' }}
                </b>
              </div>
              <div class="drow" v-if="showRow('hs_percent')">
                <span>HS %</span>
                <b :class="betterClass('hs_percent', key)">
                  {{ cell(data[key].stats, 'hs_percent') ?? '—' }}
                </b>
              </div>
              <div class="drow" v-if="data[key].stats.key === 'valorant' || showRow('rr')">
                <span>RR</span>
                <b>{{ data[key].stats.rr ?? '—' }}</b>
              </div>
              <div class="drow" v-if="showRow('avg_kda')">
                <span>Ср. KDA</span>
                <b class="mono">{{ data[key].stats.avg_kda || '—' }}</b>
              </div>
              <div class="drow" v-if="data[key].stats.key === 'valorant'">
                <span>Мейн</span>
                <b>{{ data[key].stats.main_agent || '—' }}</b>
              </div>
              <div class="drow">
                <span>Серия побед</span>
                <b :class="{ w: data[key].stats.win_streak }">
                  {{ data[key].stats.win_streak || 0 }}
                </b>
              </div>
            </div>

            <div class="form-row">
              <span class="lbl">Форма</span>
              <div class="form" v-if="data[key].stats.recent_form?.length">
                <span
                  v-for="(c, i) in data[key].stats.recent_form"
                  :key="i"
                  class="pill"
                  :class="formClass(c)"
                >{{ c }}</span>
              </div>
              <span v-else class="muted">—</span>
            </div>

            <h4>Топ герои / агенты / карты</h4>
            <template v-if="data[key].stats.top_heroes?.length">
              <div v-for="h in data[key].stats.top_heroes" :key="h.name" class="hero">
                <span>{{ h.name }}</span>
                <span class="cnt">×{{ h.games }}</span>
              </div>
            </template>
            <p v-else class="muted">—</p>

            <h4>Вердикты</h4>
            <div class="verdicts" v-if="data[key].stats.verdicts?.length">
              <span v-for="v in data[key].stats.verdicts" :key="v.label" class="v-pill">
                {{ v.label }} ×{{ v.count }}
              </span>
            </div>
            <p v-else class="muted">Нет данных</p>
          </template>
          <p v-else class="muted">
            Нет статистики по этой игре. Подключи Faceit/Dota или выбери другую вкладку.
          </p>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.compare-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  max-width: none;
  margin: 0;
  box-sizing: border-box;
}
.side {
  min-width: 0;
  width: 100%;
}
.diff-bar {
  width: 100%;
  box-sizing: border-box;
}
.back {
  align-self: flex-start;
  background: none;
  border: none;
  color: var(--accent);
  cursor: pointer;
  font-size: 14px;
}
h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}
.game-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.game-tab {
  font-size: 12px;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: 20px;
  border: 1px solid var(--border-color);
  background: none;
  color: var(--text-secondary);
  cursor: pointer;
}
.game-tab.active {
  background: var(--accent-dim);
  color: var(--accent);
  border-color: var(--accent);
}
.game-tab .hint {
  font-size: 9px;
  opacity: 0.7;
  margin-left: 4px;
}
.diff-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
  color: var(--text-secondary);
  padding: 10px 14px;
  background: var(--bg-card);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  width: 100%;
}
@media (max-width: 800px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
.head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.av {
  width: 52px;
  height: 52px;
  border-radius: 8px;
  flex-shrink: 0;
  background: var(--accent-dim) center/cover;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  color: var(--accent);
  border: 1px solid var(--border-color);
}
.side h2 {
  margin: 0;
  font-size: 18px;
}
.user {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
}
.game {
  color: var(--accent);
  font-weight: 700;
  margin: 4px 0 0;
}
.nick {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin: 12px 0;
}
@media (max-width: 500px) {
  .metrics {
    grid-template-columns: repeat(2, 1fr);
  }
}
.metrics div {
  background: var(--bg-primary);
  border-radius: 8px;
  padding: 10px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.metrics b {
  font-size: 16px;
}
.metrics span {
  font-size: 9px;
  color: var(--text-secondary);
  text-transform: uppercase;
}
.faceit-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}
.faceit-strip div {
  background: var(--bg-sunken, var(--bg-primary));
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 8px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.faceit-strip b {
  font-size: 15px;
  font-family: var(--font-mono, monospace);
  color: var(--accent);
}
.faceit-strip span {
  font-size: 9px;
  color: var(--text-muted);
  text-transform: uppercase;
}
.w {
  color: var(--success);
}
.l {
  color: var(--danger);
}
.better {
  color: var(--success);
}
.worse {
  color: var(--text-muted);
}
.detail-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}
.drow {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 6px 0;
  border-bottom: 1px solid var(--border-color);
}
.drow span {
  color: var(--text-secondary);
}
.mono {
  font-family: monospace;
}
.form-row {
  margin: 8px 0;
}
.form-row .lbl {
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
}
.form {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}
.pill {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}
.pill.w {
  background: rgba(74, 222, 128, 0.2);
  color: var(--success);
}
.pill.l {
  background: rgba(248, 113, 113, 0.2);
  color: var(--danger);
}
h4 {
  margin: 12px 0 6px;
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
}
.hero {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
}
.cnt {
  color: var(--text-secondary);
}
.verdicts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.v-pill {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 12px;
  background: var(--bg-primary);
  color: var(--text-secondary);
}
.muted,
.state {
  color: var(--text-secondary);
}
.err {
  color: var(--danger);
}
</style>
