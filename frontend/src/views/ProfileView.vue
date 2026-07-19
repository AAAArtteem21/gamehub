<script setup>
import { ref, onMounted, computed } from 'vue'
import { profilesApi } from '../api/profiles'
import { useAuthStore } from '../stores/auth'
import ConnectAccountModal from '../components/profiles/ConnectAccountModal.vue'
import UniversalStatsCard from '../components/profiles/UniversalStatsCard.vue'

const authStore = useAuthStore()
const accounts = ref([])
const loading = ref(true)
const error = ref(null)
const showConnectModal = ref(false)
const syncingIds = ref(new Set())
const activeStatsTab = ref(null) // account.id выбранной вкладки со статистикой

const platformLabels = { steam: 'Steam', faceit: 'Faceit', opendota: 'OpenDota', manual: 'Ручной' }

// платформы, у которых вообще есть детальная статистика (не просто часы)
const statsAccounts = computed(() =>
  accounts.value.filter(a => a.platform === 'opendota' || a.platform === 'faceit')
)

const activeAccount = computed(() =>
  statsAccounts.value.find(a => a.id === activeStatsTab.value) || statsAccounts.value[0]
)

async function loadAccounts() {
  loading.value = true
  error.value = null
  try {
    const res = await profilesApi.list()
    accounts.value = res.data.results || res.data
    if (!activeStatsTab.value && statsAccounts.value.length) {
      activeStatsTab.value = statsAccounts.value[0].id
    }
  } catch (e) {
    error.value = 'Не удалось загрузить аккаунты'
  } finally {
    loading.value = false
  }
}

async function handleSync(id) {
  syncingIds.value.add(id)
  try {
    const res = await profilesApi.sync(id)
    const idx = accounts.value.findIndex(a => a.id === id)
    if (idx !== -1) accounts.value[idx] = res.data
  } catch (e) {
    alert(e.response?.data?.detail || 'Не удалось синхронизировать')
  } finally {
    syncingIds.value.delete(id)
  }
}

async function handleRemove(id) {
  if (!confirm('Отключить этот аккаунт?')) return
  await profilesApi.remove(id)
  accounts.value = accounts.value.filter(a => a.id !== id)
  if (activeStatsTab.value === id) activeStatsTab.value = statsAccounts.value[0]?.id ?? null
}

function onAccountCreated(newAccount) {
  accounts.value.unshift(newAccount)
}

function steamGamesFlat() {
  const rows = []
  for (const acc of accounts.value) {
    if (acc.platform !== 'steam') continue
    for (const s of acc.snapshots || []) rows.push({ ...s })
  }
  return rows.sort((a, b) => b.playtime_forever - a.playtime_forever)
}

onMounted(loadAccounts)
</script>

<template>
  <div class="profile-page">
    <div class="profile-header card">
      <div class="avatar-big" :style="authStore.user?.avatar_url ? { backgroundImage: `url(${authStore.user.avatar_url})` } : {}"></div>
      <div>
        <h1>{{ authStore.user?.display_name || authStore.user?.username }}</h1>
        <p class="steam-id" v-if="authStore.user?.steam_id">Steam ID: {{ authStore.user.steam_id }}</p>
      </div>
    </div>

    <div class="section-header">
      <h2>Подключённые аккаунты</h2>
      <button class="btn-primary" @click="showConnectModal = true">+ Подключить аккаунт</button>
    </div>

    <div v-if="loading" class="state-message">Загружаем аккаунты...</div>
    <div v-else-if="error" class="state-message error-state">{{ error }}</div>
    <div v-else-if="accounts.length === 0" class="state-message empty-state">
      <p>Пока нет подключённых аккаунтов.</p>
      <button class="btn-primary" @click="showConnectModal = true">Подключить первый аккаунт</button>
    </div>

    <template v-else>
      <div class="platforms-row">
        <div v-for="acc in accounts" :key="acc.id" class="platform-chip">
          <span class="platform-label">{{ platformLabels[acc.platform] }}</span>
          <span class="verified-dot" :class="{ ok: acc.verified }"></span>
          <button class="icon-btn" @click="handleSync(acc.id)" :disabled="syncingIds.has(acc.id)" title="Синхронизировать">
            {{ syncingIds.has(acc.id) ? '…' : '↻' }}
          </button>
          <button class="icon-btn danger" @click="handleRemove(acc.id)" title="Отключить">✕</button>
        </div>
      </div>

      <!-- ЕДИНАЯ переключаемая карточка статистики -->
      <div class="card stats-switcher-card" v-if="statsAccounts.length">
        <div class="stats-tabs">
          <button
            v-for="acc in statsAccounts"
            :key="acc.id"
            class="stats-tab"
            :class="{ active: activeAccount?.id === acc.id }"
            @click="activeStatsTab = acc.id"
          >
            {{ acc.display_stats?.game_label || platformLabels[acc.platform] }}
          </button>
        </div>

        <UniversalStatsCard
          v-if="activeAccount?.display_stats"
          :stats="activeAccount.display_stats"
        />
        <div v-else class="empty-hint">Нажми ↻ на {{ platformLabels[activeAccount?.platform] }}, чтобы подтянуть статистику</div>
      </div>

      <!-- простые часы всех Steam-игр -->
      <div class="card games-table-card" v-if="steamGamesFlat().length">
        <h3 class="card-title table-title">Библиотека Steam — все игры</h3>
        <table class="games-table">
          <thead>
            <tr><th>Игра</th><th>Часы всего</th><th>Сегодня</th></tr>
          </thead>
          <tbody>
            <tr v-for="row in steamGamesFlat()" :key="row.id">
              <td class="game-cell">{{ row.game_name }}</td>
              <td class="hours-cell">{{ Math.round(row.playtime_forever / 60) }}ч</td>
              <td class="today-cell">
                <span v-if="row.today_playtime_minutes">+{{ row.today_playtime_minutes }}м</span>
                <span v-else class="muted">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <ConnectAccountModal v-if="showConnectModal" @close="showConnectModal = false" @created="onAccountCreated" />
  </div>
</template>

<style scoped>
.profile-page { display: flex; flex-direction: column; gap: 20px; }
.profile-header { display: flex; align-items: center; gap: 20px; }
.avatar-big { width: 72px; height: 72px; border-radius: 50%; background: var(--accent-dim); background-size: cover; border: 3px solid var(--accent); flex-shrink: 0; }
.profile-header h1 { margin: 0 0 4px; font-size: 22px; }
.steam-id { margin: 0; color: var(--text-secondary); font-size: 13px; }

.section-header { display: flex; justify-content: space-between; align-items: center; }
.section-header h2 { margin: 0; font-size: 18px; }

.platforms-row { display: flex; gap: 10px; flex-wrap: wrap; }
.platform-chip { display: flex; align-items: center; gap: 8px; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 8px 12px; }
.platform-label { font-weight: 700; font-size: 13px; }
.verified-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); }
.verified-dot.ok { background: var(--success); }
.icon-btn { background: var(--bg-card-hover); border: 1px solid var(--border-color); color: var(--text-secondary); width: 26px; height: 26px; border-radius: 6px; cursor: pointer; font-size: 12px; }
.icon-btn.danger:hover { color: var(--danger); border-color: var(--danger); }

.stats-switcher-card { display: flex; flex-direction: column; gap: 18px; }
.stats-tabs { display: flex; gap: 6px; border-bottom: 1px solid var(--border-color); padding-bottom: 12px; flex-wrap: wrap; }
.stats-tab {
  background: none; border: none; color: var(--text-secondary); font-size: 13px; font-weight: 600;
  padding: 7px 14px; border-radius: 20px; cursor: pointer; transition: all 0.2s var(--ease);
}
.stats-tab:hover { color: var(--text-primary); background: var(--bg-card-hover); }
.stats-tab.active { background: var(--accent-dim); color: var(--accent); }
.empty-hint { color: var(--text-secondary); font-size: 13px; text-align: center; padding: 20px 0; }

.card-title { margin: 0 0 14px; font-size: 15px; }
.table-title { padding: 16px 16px 0; }
.games-table-card { padding: 0; overflow: hidden; }
.games-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.games-table th { text-align: left; padding: 12px 16px; color: var(--text-secondary); font-weight: 600; border-bottom: 1px solid var(--border-color); font-size: 11px; text-transform: uppercase; }
.games-table td { padding: 12px 16px; border-bottom: 1px solid var(--border-color); }
.games-table tr:last-child td { border-bottom: none; }
.game-cell { font-weight: 600; }
.hours-cell { font-weight: 600; }
.today-cell { color: var(--success); font-size: 12px; }
.muted { color: var(--text-muted); }

.state-message { padding: 60px 20px; text-align: center; color: var(--text-secondary); background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); }
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 16px; }
.error-state { color: var(--danger); }
</style>Preferences: Open User Settings (JSON)