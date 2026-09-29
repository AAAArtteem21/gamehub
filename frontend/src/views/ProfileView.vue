<script setup>
import { ref, onMounted, computed } from 'vue'
import { profilesApi } from '../api/profiles'
import { useAuthStore } from '../stores/auth'
import api from '../api/axios'
import { useToast } from '../composables/useToast'
import ConnectAccountModal from '../components/profiles/ConnectAccountModal.vue'
import UniversalStatsCard from '../components/profiles/UniversalStatsCard.vue'
import MatchParticipantsModal from '../components/profiles/MatchParticipantsModal.vue'
import ValorantMatchModal from '../components/profiles/ValorantMatchModal.vue'

const authStore = useAuthStore()
const toast = useToast()

const accounts = ref([])
const loading = ref(true)
const error = ref(null)
const showConnectModal = ref(false)
const syncingIds = ref(new Set())
const activeStatsTab = ref(null)

const openMatchId = ref(null)
const openMatchGame = ref(null)

const progress = ref(null)
const refCodeInput = ref('')
const refBusy = ref(false)

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

const statsAccounts = computed(() =>
  accounts.value.filter(
    (a) =>
      ['opendota', 'faceit', 'lol', 'valorant', 'fortnite', 'pubg', 'roblox'].includes(a.platform) ||
      (a.platform === 'steam' && a.display_stats)
  )
)

const activeAccount = computed(
  () => statsAccounts.value.find((a) => a.id === activeStatsTab.value) || statsAccounts.value[0]
)

async function loadProgress() {
  try {
    const res = await api.get('me/progress/')
    progress.value = res.data
  } catch {
    progress.value = null
  }
}

async function claimReferral() {
  if (!refCodeInput.value.trim() || refBusy.value) return
  refBusy.value = true
  try {
    const res = await api.post('referrals/claim/', { code: refCodeInput.value.trim() })
    progress.value = res.data.progress || progress.value
    toast.success(res.data.detail || 'Реферал активирован')
    refCodeInput.value = ''
    await loadProgress()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Не удалось активировать код')
  } finally {
    refBusy.value = false
  }
}

function copyRefCode() {
  const code = progress.value?.referral_code
  if (!code) return
  navigator.clipboard?.writeText(code)
  toast.success('Код скопирован')
}

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
  syncingIds.value = new Set([...syncingIds.value, id])
  try {
    await profilesApi.sync(id)
  } catch (e) {
    const msg = e.response?.data?.detail || 'Не удалось запустить синхронизацию'
    if (e.response?.status === 429 || /подожд|cooldown|секунд/i.test(String(msg))) {
      toast.info(msg)
    } else {
      toast.error(msg)
    }
    const next = new Set(syncingIds.value)
    next.delete(id)
    syncingIds.value = next
    return
  }

  const poll = setInterval(async () => {
    try {
      const res = await profilesApi.syncStatus(id)
      if (res.data.status === 'done') {
        clearInterval(poll)
        const idx = accounts.value.findIndex((a) => a.id === id)
        if (idx !== -1 && res.data.account) {
          accounts.value[idx] = { ...accounts.value[idx], ...res.data.account }
        }
        const next = new Set(syncingIds.value)
        next.delete(id)
        syncingIds.value = next
        toast.success('Синхронизация завершена')
        loadProgress()
      } else if (res.data.status === 'error') {
        clearInterval(poll)
        toast.error(res.data.detail || 'Ошибка синхронизации')
        const next = new Set(syncingIds.value)
        next.delete(id)
        syncingIds.value = next
      }
    } catch (e) {
      clearInterval(poll)
      const next = new Set(syncingIds.value)
      next.delete(id)
      syncingIds.value = next
      toast.error('Сбой проверки статуса синхронизации')
    }
  }, 2000)
}

async function handleRemove(id) {
  if (!confirm('Отключить этот аккаунт?')) return
  try {
    await profilesApi.remove(id)
    accounts.value = accounts.value.filter((a) => a.id !== id)
    if (activeStatsTab.value === id) {
      activeStatsTab.value = statsAccounts.value[0]?.id ?? null
    }
    toast.success('Аккаунт отключён')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Не удалось отключить')
  }
}

function onAccountCreated(newAccount) {
  accounts.value.unshift(newAccount)
  showConnectModal.value = false
  if (newAccount?.id) {
    activeStatsTab.value = newAccount.id
    handleSync(newAccount.id)
  }
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

function steamGamesFlat() {
  const map = {}
  for (const acc of accounts.value) {
    if (acc.platform !== 'steam') continue
    for (const s of acc.snapshots || []) {
      if (!map[s.appid]) map[s.appid] = { name: s.game_name, byDate: {} }
      map[s.appid].byDate[s.date] = s.playtime_forever || 0
      if (!map[s.appid].latestDate || s.date > map[s.appid].latestDate) {
        map[s.appid].latestDate = s.date
        map[s.appid].name = s.game_name
        map[s.appid].latestMinutes = s.playtime_forever || 0
      }
    }
  }

  const today = new Date()
  const iso = (d) => d.toISOString().slice(0, 10)
  const weekAgo = new Date(today)
  weekAgo.setDate(weekAgo.getDate() - 7)
  const monthAgo = new Date(today)
  monthAgo.setDate(monthAgo.getDate() - 30)

  function deltaSince(byDate, sinceDate) {
    const dates = Object.keys(byDate).sort()
    if (!dates.length) return null
    const latest = dates[dates.length - 1]
    let baseline = null
    for (const d of dates) {
      if (d < iso(sinceDate)) baseline = byDate[d]
      else break
    }
    if (baseline == null) baseline = byDate[dates[0]]
    return Math.max((byDate[latest] || 0) - baseline, 0)
  }

  return Object.entries(map)
    .map(([appid, g]) => ({
      appid: Number(appid),
      game_name: g.name,
      playtime_forever: g.latestMinutes || 0,
      week_minutes: deltaSince(g.byDate, weekAgo),
      month_minutes: deltaSince(g.byDate, monthAgo),
    }))
    .sort((a, b) => b.playtime_forever - a.playtime_forever)
}

onMounted(() => {
  loadAccounts()
  loadProgress()
})
</script>

<template>
  <div class="profile-page">
    <div class="profile-header card">
      <div
        class="avatar-big"
        :style="authStore.user?.avatar_url ? { backgroundImage: `url(${authStore.user.avatar_url})` } : {}"
      ></div>
      <div class="header-main">
        <h1>{{ authStore.user?.display_name || authStore.user?.username }}</h1>
        <p class="steam-id" v-if="authStore.user?.steam_id">Steam ID: {{ authStore.user.steam_id }}</p>

        <div class="gh-block" v-if="progress">
          <div class="gh-row">
            <span class="gh-lvl">GH {{ progress.level }}</span>
            <div class="gh-bar"><i :style="{ width: (progress.pct || 0) + '%' }" /></div>
            <span class="gh-xp">{{ progress.xp_into_level ?? 0 }}/{{ progress.xp_per_level ?? 100 }} XP</span>
          </div>
          <div class="gh-meta">
            <span class="gh-tag" v-for="t in (progress.tags || [])" :key="t">{{ t }}</span>
            <span class="gh-boost" v-if="progress.boost_credits">Бусты: {{ progress.boost_credits }}</span>
          </div>
          <div class="gh-ref" v-if="progress.referral_code">
            <span>Твой код:</span>
            <code class="ref-code" @click="copyRefCode" title="Скопировать">{{ progress.referral_code }}</code>
          </div>
          <div class="gh-ref-claim" v-if="!progress.has_referrer">
            <input v-model="refCodeInput" placeholder="Код друга" maxlength="16" />
            <button type="button" class="btn-ref" :disabled="refBusy" @click="claimReferral">
              Активировать
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="section-header">
      <h2>Подключённые аккаунты</h2>
      <button class="btn-primary" type="button" @click="showConnectModal = true">+ Подключить аккаунт</button>
    </div>

    <div v-if="loading" class="state-message">Загружаем аккаунты...</div>
    <div v-else-if="error" class="state-message error-state">{{ error }}</div>
    <div v-else-if="accounts.length === 0" class="state-message empty-state">
      <p>Пока нет подключённых аккаунтов.</p>
      <button class="btn-primary" type="button" @click="showConnectModal = true">Подключить первый аккаунт</button>
    </div>

    <template v-else>
      <div class="platforms-row">
        <div v-for="acc in accounts" :key="acc.id" class="platform-chip">
          <span class="platform-label">{{ platformLabels[acc.platform] || acc.platform }}</span>
          <span class="chip-nick" v-if="acc.nickname">{{ acc.nickname }}</span>
          <span class="verified-dot" :class="{ ok: acc.verified }"></span>
          <button
            class="icon-btn"
            type="button"
            @click="handleSync(acc.id)"
            :disabled="syncingIds.has(acc.id)"
            title="Синхронизировать"
          >
            {{ syncingIds.has(acc.id) ? '…' : '↻' }}
          </button>
          <button class="icon-btn danger" type="button" @click="handleRemove(acc.id)" title="Отключить">✕</button>
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
            @click="activeStatsTab = acc.id"
          >
            {{ acc.display_stats?.game_label || platformLabels[acc.platform] || acc.platform }}
          </button>
        </div>

        <UniversalStatsCard
          v-if="activeAccount?.display_stats"
          :stats="activeAccount.display_stats"
          :platform="activeAccount.platform"
          @open-match="openMatch"
        />
        <div v-else class="empty-hint">
          Нажми ↻ на {{ platformLabels[activeAccount?.platform] || 'аккаунт' }}, чтобы подтянуть статистику
        </div>
      </div>

      <div class="card games-table-card" v-if="steamGamesFlat().length">
        <h3 class="card-title table-title">Библиотека Steam — все игры</h3>
        <table class="games-table">
          <thead>
            <tr>
              <th>Игра</th>
              <th>Часы всего</th>
              <th>За неделю</th>
              <th>За месяц</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in steamGamesFlat()" :key="row.appid">
              <td class="game-cell">{{ row.game_name }}</td>
              <td class="hours-cell">{{ Math.round(row.playtime_forever / 60) }}ч</td>
              <td class="today-cell">
                <span v-if="row.week_minutes != null && row.week_minutes > 0">
                  +{{ Math.round(row.week_minutes / 60) }}ч
                </span>
                <span v-else class="muted">—</span>
              </td>
              <td class="today-cell">
                <span v-if="row.month_minutes != null && row.month_minutes > 0">
                  +{{ Math.round(row.month_minutes / 60) }}ч
                </span>
                <span v-else class="muted">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <ConnectAccountModal
      v-if="showConnectModal"
      @close="showConnectModal = false"
      @created="onAccountCreated"
    />

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
  gap: 22px;
  animation: fadeInUp 0.35s var(--ease) both;
}
.profile-header {
  display: flex;
  align-items: flex-start;
  gap: 18px;
  padding: 22px 24px !important;
}
.avatar-big {
  width: 76px;
  height: 76px;
  border-radius: 50%;
  background: var(--accent-dim);
  background-size: cover;
  background-position: center;
  border: 2px solid rgba(230, 57, 70, 0.55);
  box-shadow: 0 0 0 4px rgba(230, 57, 70, 0.12);
  flex-shrink: 0;
}
.header-main { min-width: 0; flex: 1; }
.profile-header h1 {
  margin: 0 0 4px;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.03em;
}
.steam-id {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
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
  font-size: 12px;
  font-weight: 800;
  color: var(--accent);
  background: var(--accent-dim);
  padding: 3px 10px;
  border-radius: 999px;
}
.gh-bar {
  flex: 1;
  min-width: 100px;
  max-width: 200px;
  height: 8px;
  border-radius: 99px;
  background: var(--bg-primary);
  overflow: hidden;
}
.gh-bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--accent), #ff6b7a);
  border-radius: 99px;
  transition: width 0.3s ease;
}
.gh-xp {
  font-size: 11px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.gh-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.gh-tag,
.gh-boost {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--bg-card-hover);
  color: var(--text-secondary);
}
.gh-ref {
  font-size: 12px;
  color: var(--text-secondary);
  display: flex;
  gap: 8px;
  align-items: center;
}
.ref-code {
  font-weight: 800;
  color: var(--accent);
  cursor: pointer;
  background: var(--accent-dim);
  padding: 2px 8px;
  border-radius: 6px;
}
.gh-ref-claim {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.gh-ref-claim input {
  width: 130px;
  font-size: 12px;
  padding: 7px 10px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
}
.btn-ref {
  background: var(--bg-card-hover);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 7px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.btn-ref:disabled { opacity: 0.5; }

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.section-header h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}
.btn-primary {
  background: var(--accent);
  color: #fff;
  border: none;
  padding: 10px 16px;
  border-radius: var(--radius-sm);
  font-weight: 600;
  cursor: pointer;
  font-size: 13px;
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
  border-radius: 999px;
  padding: 6px 10px 6px 12px;
}
.platform-label { font-weight: 700; font-size: 12px; }
.chip-nick {
  font-size: 11px;
  color: var(--text-secondary);
  max-width: 100px;
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
.verified-dot.ok {
  background: var(--success);
  box-shadow: 0 0 0 2px rgba(74, 222, 128, 0.2);
}
.icon-btn {
  background: var(--bg-card-hover);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  width: 26px;
  height: 26px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.icon-btn:disabled { opacity: 0.5; }
.icon-btn.danger:hover:not(:disabled) {
  color: var(--danger);
  border-color: var(--danger);
}

.stats-switcher-card {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 18px 20px !important;
}
.stats-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 14px;
  flex-wrap: wrap;
}
.stats-tab {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
  padding: 7px 14px;
  border-radius: 999px;
  cursor: pointer;
}
.stats-tab:hover {
  color: var(--text-primary);
  background: var(--bg-card-hover);
}
.stats-tab.active {
  background: var(--accent-dim);
  color: var(--accent);
  box-shadow: inset 0 0 0 1px rgba(230, 57, 70, 0.25);
}
.empty-hint {
  color: var(--text-secondary);
  font-size: 13px;
  text-align: center;
  padding: 28px 12px;
}

.card-title { margin: 0 0 14px; font-size: 14px; font-weight: 700; }
.table-title { padding: 16px 16px 0; }
.games-table-card { padding: 0 !important; overflow: hidden; }
.games-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.games-table th {
  text-align: left;
  padding: 12px 16px;
  color: var(--text-muted);
  font-weight: 700;
  border-bottom: 1px solid var(--border-color);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.games-table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}
.games-table tr:last-child td { border-bottom: none; }
.games-table tbody tr:hover { background: var(--bg-card-hover); }
.game-cell { font-weight: 600; }
.hours-cell { font-weight: 700; font-variant-numeric: tabular-nums; }
.today-cell { color: var(--success); font-size: 12px; }
.muted { color: var(--text-muted); }

.state-message {
  padding: 56px 20px;
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
  gap: 16px;
}
.error-state { color: var(--danger); }
</style>