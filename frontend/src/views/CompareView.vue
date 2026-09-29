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

function rankLabel(stats) {
  if (!stats) return '—'
  if (stats.tier) return stats.tier
  const rt = stats.extra?.rank_tier
  if (rt == null || rt === '') return '—'
  // OpenDota rank_tier: 62 = Archon 2 и т.п. — можно оставить число или маппинг
  return String(rt)
}

function formClass(c) {
  return c === 'W' ? 'w' : 'l'
}

onMounted(load)
watch(() => route.query, () => {
  selectedGame.value = ''
  load()
})
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
        <span>Δ винрейт: <b :class="data.diff.winrate >= 0 ? 'w' : 'l'">{{ data.diff.winrate > 0 ? '+' : '' }}{{ data.diff.winrate }}%</b></span>
        <span>Δ побед: <b>{{ data.diff.wins > 0 ? '+' : '' }}{{ data.diff.wins }}</b></span>
      </div>

      <div class="grid">
        <div class="card side" v-for="key in ['me', 'other']" :key="key">
          <div class="head">
            <div
              class="av"
              :style="data[key]?.avatar_url ? { backgroundImage: `url(${data[key].avatar_url})` } : {}"
            >
              <span v-if="!data[key]?.avatar_url">{{ (data[key]?.display_name || '?')[0] }}</span>
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

            <!-- одинаковый список для обеих колонок -->
            <div class="detail-grid">
              <div class="drow">
                <span>Rating / MMR</span>
                <b>{{ data[key].stats.skill_rating ?? data[key].stats.extra?.mmr ?? '—' }}</b>
              </div>
              <div class="drow">
                <span>Ранг</span>
                <b>{{ rankLabel(data[key].stats) }}</b>
              </div>
              <div class="drow" v-if="data[key].stats.key === 'valorant'">
                <span>RR</span>
                <b>{{ data[key].stats.rr ?? '—' }}</b>
              </div>
              <div class="drow">
                <span>Ср. KDA</span>
                <b class="mono">{{ data[key].stats.avg_kda || '—' }}</b>
              </div>
              <div class="drow" v-if="data[key].stats.key === 'valorant'">
                <span>Мейн</span>
                <b>{{ data[key].stats.main_agent || '—' }}</b>
              </div>
              <div class="drow">
                <span>Серия побед</span>
                <b :class="{ w: data[key].stats.win_streak }">{{ data[key].stats.win_streak || 0 }}</b>
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

            <h4>Топ герои / агенты</h4>
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
            <p v-else class="muted">Нет данных (только у синкнутого аккаунта)</p>
          </template>
          <p v-else class="muted">
            Нет статистики по этой игре. Подключи аккаунт или выбери другую вкладку.
          </p>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.compare-page { display: flex; flex-direction: column; gap: 16px; }
.back {
  align-self: flex-start; background: none; border: none; color: var(--accent);
  cursor: pointer; font-size: 14px;
}
.game-tabs { display: flex; flex-wrap: wrap; gap: 8px; }
.game-tab {
  font-size: 12px; font-weight: 700; padding: 6px 12px; border-radius: 20px;
  border: 1px solid var(--border-color); background: none; color: var(--text-secondary);
  cursor: pointer;
}
.game-tab.active {
  background: var(--accent-dim); color: var(--accent); border-color: var(--accent);
}
.game-tab .hint { font-size: 9px; opacity: 0.7; margin-left: 4px; }
.diff-bar {
  display: flex; gap: 16px; font-size: 13px; color: var(--text-secondary);
  padding: 8px 12px; background: var(--bg-card); border-radius: 8px;
  border: 1px solid var(--border-color);
}
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 800px) { .grid { grid-template-columns: 1fr; } }
.head { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.av {
  width: 52px; height: 52px; border-radius: 50%; flex-shrink: 0;
  background: var(--accent-dim) center/cover; display: flex; align-items: center;
  justify-content: center; font-weight: 800; color: var(--accent); border: 2px solid var(--border-color);
}
.side h2 { margin: 0; font-size: 18px; }
.user { margin: 0; color: var(--text-secondary); font-size: 13px; }
.game { color: var(--accent); font-weight: 700; margin: 4px 0 0; }
.nick { font-size: 12px; color: var(--text-muted); margin: 0; }
.metrics {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 12px 0;
}
@media (max-width: 500px) { .metrics { grid-template-columns: repeat(2, 1fr); } }
.metrics div {
  background: var(--bg-primary); border-radius: 8px; padding: 10px; text-align: center;
  display: flex; flex-direction: column; gap: 2px;
}
.metrics b { font-size: 16px; }
.metrics span { font-size: 9px; color: var(--text-secondary); text-transform: uppercase; }
.w { color: var(--success); }
.l { color: var(--danger); }
.detail-grid { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; }
.drow {
  display: flex; justify-content: space-between; font-size: 13px;
  padding: 6px 0; border-bottom: 1px solid var(--border-color);
}
.drow span { color: var(--text-secondary); }
.mono { font-family: monospace; }
.form-row { margin: 8px 0; }
.form-row .lbl { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; }
.form { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
.pill {
  width: 22px; height: 22px; border-radius: 6px; font-size: 10px; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
}
.pill.w { background: rgba(74,222,128,0.2); color: var(--success); }
.pill.l { background: rgba(248,113,113,0.2); color: var(--danger); }
h4 { margin: 12px 0 6px; font-size: 12px; color: var(--text-secondary); text-transform: uppercase; }
.hero {
  display: flex; justify-content: space-between; padding: 6px 0;
  border-bottom: 1px solid var(--border-color); font-size: 13px;
}
.cnt { color: var(--text-secondary); }
.verdicts { display: flex; flex-wrap: wrap; gap: 6px; }
.v-pill {
  font-size: 11px; font-weight: 600; padding: 4px 8px; border-radius: 12px;
  background: var(--bg-primary); color: var(--text-secondary);
}
.muted, .state { color: var(--text-secondary); }
.err { color: var(--danger); }
</style>