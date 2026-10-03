<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/axios'
import { useAuthStore } from '../stores/auth'
import UniversalStatsCard from '../components/profiles/UniversalStatsCard.vue'
import MatchParticipantsModal from '../components/profiles/MatchParticipantsModal.vue'
import ValorantMatchModal from '../components/profiles/ValorantMatchModal.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const profile = ref(null)
const loading = ref(true)
const error = ref(null)
const activeTab = ref(null)
const openMatchId = ref(null)
const openMatchGame = ref(null)
const isFav = ref(false)

const platformLabels = {
  steam: 'Steam',
  faceit: 'Faceit',
  opendota: 'OpenDota',
  lol: 'League of Legends',
  valorant: 'Valorant',
  fortnite: 'Fortnite',
  pubg: 'PUBG',
  roblox: 'Roblox',
  manual: 'Ручной',
}

const isMe = computed(() =>
  !!(authStore.user && String(authStore.user.id) === String(route.params.id))
)

const statsAccounts = computed(() =>
  (profile.value?.accounts || []).filter(
    (a) =>
      a.display_stats &&
      ['opendota', 'faceit', 'lol', 'valorant', 'fortnite', 'pubg', 'roblox'].includes(a.platform)
  )
)

const activeAccount = computed(
  () =>
    statsAccounts.value.find((a) => a.id === activeStatsTab.value) ||
    statsAccounts.value[0]
)

async function loadFav() {
  if (isMe.value || !authStore.isAuthenticated) return
  try {
    const res = await api.get('favorites/status/', { params: { user_id: route.params.id } })
    isFav.value = !!res.data.favorited
  } catch {
    isFav.value = false
  }
}

async function toggleFav() {
  if (!authStore.requireAuth('Войди через Steam, чтобы добавлять в избранное.')) return
  try {
    const res = await api.post('favorites/toggle/', { user_id: Number(route.params.id) })
    isFav.value = !!res.data.favorited
  } catch (e) {
    alert(e.response?.data?.detail || 'Не удалось')
  }
}

function goCompare() {
  if (!authStore.requireAuth('Войди через Steam, чтобы сравнить статистику с собой.')) return
  router.push({ path: '/compare', query: { user_id: route.params.id } })
}

function load() {
  return doLoad(false)
}

async function doLoad(isRetry) {
  loading.value = true
  error.value = null
  profile.value = null
  activeTab.value = null

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
    if (e.response?.status === 401 && !isRetry) return doLoad(true)
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
}

function openMatch(matchId) {
  if (!matchId || !activeAccount.value) return
  const p = String(activeAccount.value.platform || '').toLowerCase()
  if (p === 'valorant') {
    openMatchGame.value = 'valorant'
    openMatchId.value = matchId
  } else if (p === 'opendota' || p === 'dota2') {
    openMatchGame.value = 'dota2'
    openMatchId.value = matchId
  }
}

function closeMatch() {
  openMatchId.value = null
  openMatchGame.value = null
}

onMounted(load)
watch(() => route.params.id, load)
</script>

<template>
  <div class="profile-page">
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
          <span v-if="!profile.avatar_url">
            {{ (profile.display_name || profile.username || '?')[0]?.toUpperCase() }}
          </span>
        </div>
        <div class="header-main">
          <h1>{{ profile.display_name || profile.username }}</h1>
          <p class="steam-id" v-if="profile.steam_id">Steam ID: {{ profile.steam_id }}</p>
          <p class="views-count" v-if="profile.views_count !== undefined">
            {{ profile.views_count }} просмотров
            <span v-if="profile.accounts_count != null"> · {{ profile.accounts_count }} акк.</span>
          </p>

          <div class="gh-block" v-if="profile.progress">
            <div class="gh-row">
              <span class="gh-lvl">GH {{ profile.progress.level }}</span>
              <div class="gh-bar"><i :style="{ width: (profile.progress.pct || 0) + '%' }" /></div>
              <span class="gh-xp">
                {{ profile.progress.xp_into_level ?? 0 }}/{{ profile.progress.xp_per_level ?? 100 }} XP
              </span>
            </div>
            <div class="gh-meta" v-if="profile.progress.tags?.length">
              <span class="gh-tag" v-for="t in profile.progress.tags" :key="t">{{ t }}</span>
            </div>
          </div>
          <div class="gh-block" v-else>
            <span class="not-gh">Не на GameEyes / без уровня</span>
          </div>

          <div class="header-actions" v-if="!isMe">
            <button type="button" class="btn-secondary" @click="goCompare">Сравнить с собой</button>
            <button type="button" class="btn-secondary" @click="toggleFav">
              {{ isFav ? '★ В избранном' : '☆ В избранное' }}
            </button>
          </div>
          <div class="header-actions" v-else>
            <button type="button" class="btn-secondary" @click="router.push('/profile')">
              Редактировать свой профиль
            </button>
          </div>
        </div>
      </div>

      <div class="section-header">
        <h2>Подключённые аккаунты</h2>
      </div>

      <div v-if="!(profile.accounts || []).length" class="state-message empty-state">
        <p>У игрока нет подключённых аккаунтов</p>
      </div>

      <template v-else>
        <div class="platforms-row">
          <div v-for="acc in profile.accounts" :key="acc.id" class="platform-chip">
            <span class="platform-label">{{ platformLabels[acc.platform] || acc.platform }}</span>
            <span class="chip-nick" v-if="acc.nickname">{{ acc.nickname }}</span>
            <span class="verified-dot" :class="{ ok: acc.verified }"></span>
          </div>
        </div>

        <div class="card stats-switcher-card" v-if="statsAccounts.length">
          <div class="stats-tabs">
            <button
              v-for="acc in statsAccounts"
              :key="acc.id"
              type="button"
              class="stats-tab"
              :class="{ active: activeAccount?.id === acc.id }"
              @click="selectTab(acc.id)"
            >
              {{
                acc.display_stats?.game_label ||
                platformLabels[acc.platform] ||
                acc.platform
              }}
            </button>
          </div>

          <UniversalStatsCard
            v-if="activeAccount?.display_stats"
            :stats="activeAccount.display_stats"
            :platform="activeAccount.platform"
          />
          <div v-else class="empty-hint">Статистика ещё не синхронизирована</div>
        </div>

        <div class="card games-table-card" v-if="allGamesFlat().length">
          <h3 class="card-title table-title">Библиотека игр</h3>
          <table class="games-table">
            <thead>
              <tr>
                <th>Игра</th>
                <th>Платформа</th>
                <th>Часы всего</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in allGamesFlat()" :key="`${row.platform}-${row.appid}`">
                <td class="game-cell">{{ row.game_name }}</td>
                <td>
                  <span class="platform-tag">{{ platformLabels[row.platform] || row.platform }}</span>
                </td>
                <td class="hours-cell">{{ Math.round((row.playtime_forever || 0) / 60) }}ч</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
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
.profile-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
  width: 100%;
  animation: fadeInUp 0.25s var(--ease) both;
}

.profile-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 18px 20px !important;
  width: 100%;
}
.avatar-big {
  width: 72px;
  height: 72px;
  border-radius: 8px;
  background: var(--accent-dim);
  background-size: cover;
  background-position: center;
  border: 1px solid var(--border-color);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 700;
  color: var(--accent);
}
.header-main { min-width: 0; flex: 1; }
.profile-header h1 {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 600;
}
.steam-id, .views-count {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
  font-family: var(--font-mono);
}

.gh-block {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.gh-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.gh-lvl {
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  background: var(--accent-dim);
  padding: 3px 9px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
}
.gh-bar {
  flex: 1;
  min-width: 100px;
  max-width: 220px;
  height: 6px;
  border-radius: 3px;
  background: var(--bg-sunken);
  overflow: hidden;
}
.gh-bar i {
  display: block;
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
}
.gh-xp {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}
.gh-meta { display: flex; gap: 6px; flex-wrap: wrap; }
.gh-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--bg-card-hover);
  color: var(--text-secondary);
}
.not-gh {
  font-size: 12px;
  color: var(--text-muted);
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.section-header h2 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
}

.platforms-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.platform-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 6px 10px;
}
.platform-label { font-weight: 600; font-size: 12px; }
.chip-nick {
  font-size: 11px;
  color: var(--text-secondary);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.verified-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-muted);
}
.verified-dot.ok { background: var(--success); }

.stats-switcher-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px 18px !important;
  width: 100%;
}
.stats-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
  flex-wrap: wrap;
}
.stats-tab {
  background: none;
  border: 1px solid transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.stats-tab:hover {
  color: var(--text-primary);
  background: var(--bg-card-hover);
}
.stats-tab.active {
  background: var(--accent-dim);
  color: var(--accent);
  border-color: rgba(196, 165, 116, 0.35);
}
.empty-hint {
  color: var(--text-secondary);
  font-size: 13px;
  text-align: center;
  padding: 24px 12px;
}

.card-title {
  margin: 0 0 12px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
}
.table-title { padding: 14px 16px 0; }
.games-table-card {
  padding: 0 !important;
  overflow: hidden;
  width: 100%;
}
.games-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.games-table th {
  text-align: left;
  padding: 10px 16px;
  color: var(--text-muted);
  font-weight: 600;
  border-bottom: 1px solid var(--border-color);
  font-size: 10px;
  text-transform: uppercase;
}
.games-table td {
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-color);
}
.games-table tr:last-child td { border-bottom: none; }
.game-cell { font-weight: 500; }
.platform-tag {
  font-size: 11px;
  color: var(--accent);
  font-weight: 700;
}
.hours-cell {
  font-weight: 600;
  font-family: var(--font-mono);
}

.state-message {
  padding: 48px 20px;
  text-align: center;
  color: var(--text-secondary);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}
.error-state {
  color: var(--danger);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.retry-btn {
  background: var(--bg-card-hover);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

@media (max-width: 900px) {
  .profile-header { flex-direction: column; align-items: stretch; }
  .avatar-big { width: 56px; height: 56px; }
  .games-table-card { overflow-x: auto; }
  .games-table { min-width: 420px; }
  .gh-bar { max-width: none; }
}
</style>