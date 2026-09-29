<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/axios'
import { useAuthStore } from '../stores/auth'
import MatchParticipantsModal from '../components/profiles/MatchParticipantsModal.vue'
import ValorantMatchModal from '../components/profiles/ValorantMatchModal.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const profile = ref(null)
const loading = ref(true)
const error = ref(null)
const activeTab = ref(null)
const historyLimit = ref(8)
const openMatchId = ref(null)
const openMatchGame = ref(null)
const isFav = ref(false)

const platformLabels = {
  steam: 'Steam', faceit: 'Faceit', opendota: 'OpenDota',
  lol: 'League of Legends', valorant: 'Valorant', pubg: 'PUBG', roblox: 'Roblox',
}

const isMe = computed(() =>
  !!(authStore.user && String(authStore.user.id) === String(route.params.id))
)

const statsAccounts = computed(() =>
  (profile.value?.accounts || []).filter(a => a.display_stats)
)

const activeAccount = computed(() =>
  statsAccounts.value.find(a => a.id === activeTab.value) || statsAccounts.value[0] || null
)

const fullHistory = computed(() => activeAccount.value?.display_stats?.match_history || [])
const visibleHistory = computed(() => fullHistory.value.slice(0, historyLimit.value))
const canExpandHistory = computed(() => fullHistory.value.length > historyLimit.value)

async function loadFav() {
  if (isMe.value) return
  try {
    const res = await api.get('favorites/status/', { params: { user_id: route.params.id } })
    isFav.value = !!res.data.favorited
  } catch {
    isFav.value = false
  }
}

async function toggleFav() {
  try {
    const res = await api.post('favorites/toggle/', { user_id: Number(route.params.id) })
    isFav.value = !!res.data.favorited
  } catch (e) {
    alert(e.response?.data?.detail || 'Не удалось')
  }
}

function goCompare() {
  router.push({ path: '/compare', query: { user_id: route.params.id } })
}

async function load() {
  loading.value = true
  error.value = null
  profile.value = null
  activeTab.value = null
  historyLimit.value = 8

  const userId = route.params.id
  if (!userId || isNaN(Number(userId))) {
    error.value = `Некорректный ID: "${userId}"`
    loading.value = false
    return
  }

  try {
    const res = await api.get(`players/${userId}/`)
    profile.value = res.data
    if (statsAccounts.value.length) activeTab.value = statsAccounts.value[0].id
    await loadFav()
  } catch (e) {
    error.value = e.response
      ? `Ошибка ${e.response.status}: ${e.response.data?.detail || 'не удалось загрузить'}`
      : 'Сервер не ответил'
  } finally {
    loading.value = false
  }
}

function allGamesFlat() {
  if (!profile.value) return []
  const byKey = {}
  for (const acc of profile.value.accounts || []) {
    for (const s of acc.snapshots || []) {
      const key = `${acc.platform}-${s.appid}`
      if (!byKey[key] || (s.date && s.date > byKey[key].date)) {
        byKey[key] = { ...s, platform: acc.platform }
      }
    }
  }
  return Object.values(byKey).sort((a, b) => (b.playtime_forever || 0) - (a.playtime_forever || 0))
}

function selectTab(id) {
  activeTab.value = id
  historyLimit.value = 8
}

function openMatch(m) {
  if (!m?.match_id || !activeAccount.value) return
  const p = activeAccount.value.platform
  if (p === 'opendota') openMatchGame.value = 'dota2'
  else if (p === 'valorant') openMatchGame.value = 'valorant'
  else return
  openMatchId.value = m.match_id
}

function closeMatch() {
  openMatchId.value = null
  openMatchGame.value = null
}

onMounted(load)
watch(() => route.params.id, load)
</script>

<template>
  <div class="public-profile">
    <div v-if="loading" class="state-message">Загружаем профиль...</div>
    <div v-else-if="error" class="state-message error-state">
      <p>{{ error }}</p>
      <button type="button" class="retry-btn" @click="load">Повторить</button>
    </div>

    <template v-else-if="profile">
      <div class="profile-header card">
        <div
          class="avatar-big"
          :style="profile.avatar_url ? { backgroundImage: `url(${profile.avatar_url})` } : {}"
        >
          <span v-if="!profile.avatar_url">{{ (profile.display_name || profile.username || '?')[0]?.toUpperCase() }}</span>
        </div>
        <div class="header-main">
          <h1>{{ profile.display_name || profile.username }}</h1>
          <p class="views-count" v-if="profile.views_count !== undefined">👁 {{ profile.views_count }} просмотров</p>
          <div class="header-actions" v-if="!isMe">
            <button type="button" class="btn-secondary" @click="goCompare">Сравнить с собой</button>
            <button type="button" class="btn-secondary" @click="toggleFav">
              {{ isFav ? '★ В избранном' : '☆ В избранное' }}
            </button>
          </div>
        </div>
      </div>

      <div class="card stats-card" v-if="statsAccounts.length">
        <div class="stats-tabs">
          <button
            v-for="acc in statsAccounts"
            :key="acc.id"
            type="button"
            class="stats-tab"
            :class="{ active: activeAccount?.id === acc.id }"
            @click="selectTab(acc.id)"
          >
            {{ acc.display_stats?.game_label || platformLabels[acc.platform] }}
          </button>
        </div>

        <div class="metrics" v-if="activeAccount?.display_stats?.metrics?.length">
          <div v-for="m in activeAccount.display_stats.metrics" :key="m.label" class="metric">
            <span class="metric-val" :class="m.tone">{{ m.value }}</span>
            <span class="metric-lab">{{ m.label }}</span>
          </div>
        </div>

        <div v-if="visibleHistory.length" class="history-block">
          <h4 class="section-title">История матчей</h4>
          <div
            v-for="(m, i) in visibleHistory"
            :key="i"
            class="match-row"
            :class="{
              win: m.won === true,
              loss: m.won === false,
              clickable: !!m.match_id && (activeAccount?.platform === 'opendota' || activeAccount?.platform === 'valorant'),
            }"
            @click="openMatch(m)"
          >
            <span class="match-result">{{ m.won ? 'W' : 'L' }}</span>
            <div class="match-info">
              <span class="match-title">{{ m.title }}</span>
              <span class="match-meta">
                {{ m.played_at }}
                <template v-if="m.duration"> · {{ m.duration }}</template>
              </span>
            </div>
            <span class="match-kda">{{ m.subtitle }}</span>
            <span v-if="m.verdict?.label" class="verdict" :class="m.verdict.tone">{{ m.verdict.label }}</span>
          </div>
          <button v-if="canExpandHistory" type="button" class="show-more" @click="historyLimit += 10">
            Показать ещё
          </button>
        </div>
      </div>

      <div class="card games-table-card" v-if="allGamesFlat().length">
        <h3 class="table-title">Библиотека игр</h3>
        <table class="games-table">
          <thead>
            <tr><th>Игра</th><th>Платформа</th><th>Часы всего</th></tr>
          </thead>
          <tbody>
            <tr v-for="row in allGamesFlat()" :key="`${row.platform}-${row.appid}`">
              <td class="game-cell">{{ row.game_name }}</td>
              <td><span class="platform-tag">{{ platformLabels[row.platform] || row.platform }}</span></td>
              <td class="hours-cell">{{ Math.round((row.playtime_forever || 0) / 60) }}ч</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="!statsAccounts.length" class="state-message">
        У игрока пока нет подключённой статистики
      </div>
    </template>

    <MatchParticipantsModal
      v-if="openMatchId && openMatchGame === 'dota2'"
      game="dota2"
      :match-id="openMatchId"
      @close="closeMatch"
    />
    <ValorantMatchModal
      v-if="openMatchId && openMatchGame === 'valorant'"
      :match-id="openMatchId"
      @close="closeMatch"
    />
  </div>
</template>

<style scoped>
.public-profile { display: flex; flex-direction: column; gap: 20px; }
.profile-header { display: flex; align-items: center; gap: 20px; }
.avatar-big {
  width: 72px; height: 72px; border-radius: 50%; background-color: var(--accent-dim);
  background-size: cover; background-position: center; border: 3px solid var(--accent);
  flex-shrink: 0; display: flex; align-items: center; justify-content: center;
  font-size: 24px; font-weight: 800; color: var(--accent);
}
.header-main { display: flex; flex-direction: column; gap: 6px; }
.profile-header h1 { margin: 0; font-size: 22px; }
.views-count { margin: 0; font-size: 12px; color: var(--text-secondary); }
.header-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
.btn-secondary {
  background: var(--bg-primary); border: 1px solid var(--border-color);
  color: var(--text-primary); padding: 7px 12px; border-radius: 8px;
  font-size: 12px; font-weight: 600; cursor: pointer;
}
.btn-secondary:hover { border-color: var(--accent); color: var(--accent); }

.stats-card { display: flex; flex-direction: column; gap: 16px; }
.stats-tabs {
  display: flex; gap: 6px; flex-wrap: wrap;
  border-bottom: 1px solid var(--border-color); padding-bottom: 12px;
}
.stats-tab {
  background: none; border: none; color: var(--text-secondary); font-size: 13px; font-weight: 600;
  padding: 7px 14px; border-radius: 20px; cursor: pointer;
}
.stats-tab.active { background: var(--accent-dim); color: var(--accent); }

.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(80px, 1fr)); gap: 8px; }
.metric {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  background: var(--bg-primary); border-radius: var(--radius-sm); padding: 10px 6px;
}
.metric-val { font-size: 18px; font-weight: 800; }
.metric-val.win { color: var(--success); }
.metric-val.loss { color: var(--danger); }
.metric-val.accent { color: var(--accent); }
.metric-lab { font-size: 10px; color: var(--text-secondary); text-transform: uppercase; }

.section-title { margin: 0 0 10px; font-size: 12px; color: var(--text-secondary); text-transform: uppercase; }
.match-row {
  display: flex; align-items: center; gap: 10px; padding: 10px 8px;
  border-bottom: 1px solid var(--border-color); font-size: 13px; border-radius: 8px;
}
.match-row.clickable { cursor: pointer; }
.match-row.clickable:hover { background: var(--bg-card-hover); }
.match-result {
  width: 24px; height: 24px; border-radius: 6px; display: flex; align-items: center;
  justify-content: center; font-size: 11px; font-weight: 800; flex-shrink: 0;
}
.match-row.win .match-result { background: rgba(74,222,128,0.15); color: var(--success); }
.match-row.loss .match-result { background: rgba(248,113,113,0.15); color: var(--danger); }
.match-info { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.match-title { font-weight: 700; }
.match-meta { font-size: 11px; color: var(--text-secondary); }
.match-kda { font-family: monospace; color: var(--text-secondary); }
.verdict { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 20px; }
.verdict.great { background: rgba(74,222,128,0.15); color: var(--success); }
.verdict.good { background: rgba(58,155,220,0.15); color: #3A9BDC; }
.verdict.bad { background: rgba(251,191,36,0.15); color: #fbbf24; }
.verdict.terrible { background: rgba(248,113,113,0.15); color: var(--danger); }
.show-more {
  width: 100%; margin-top: 8px; padding: 10px; background: var(--bg-primary);
  border: 1px solid var(--border-color); border-radius: var(--radius-sm);
  color: var(--accent); font-weight: 600; font-size: 13px; cursor: pointer;
}

.games-table-card { padding: 0; overflow: hidden; }
.table-title { padding: 16px 16px 0; margin: 0 0 8px; font-size: 15px; }
.games-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.games-table th {
  text-align: left; padding: 12px 16px; color: var(--text-secondary); font-weight: 600;
  border-bottom: 1px solid var(--border-color); font-size: 11px; text-transform: uppercase;
}
.games-table td { padding: 12px 16px; border-bottom: 1px solid var(--border-color); }
.game-cell { font-weight: 600; }
.platform-tag { font-size: 11px; color: var(--accent); font-weight: 700; text-transform: uppercase; }
.hours-cell { font-weight: 600; }

.state-message {
  padding: 60px 20px; text-align: center; color: var(--text-secondary);
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md);
}
.error-state { color: var(--danger); display: flex; flex-direction: column; align-items: center; gap: 12px; }
.retry-btn {
  background: var(--bg-card-hover); border: 1px solid var(--border-color);
  color: var(--text-primary); padding: 8px 16px; border-radius: var(--radius-sm); cursor: pointer;
}
</style>