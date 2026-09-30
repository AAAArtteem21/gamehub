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
        await loadAccounts()
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
      const day = String(s.date).slice(0, 10)
      if (!map[s.appid]) map[s.appid] = { name: s.game_name, byDate: {} }
      map[s.appid].byDate[day] = Number(s.playtime_forever) || 0
      if (!map[s.appid].latestDate || day > map[s.appid].latestDate) {
        map[s.appid].latestDate = day
        map[s.appid].name = s.game_name || map[s.appid].name
        map[s.appid].latestMinutes = Number(s.playtime_forever) || 0
      }
    }
  }

  const pad = (n) => String(n).padStart(2, '0')
  const isoLocal = (d) =>
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

  const today = new Date()
  const weekAgo = new Date(today)
  weekAgo.setDate(weekAgo.getDate() - 7)
  const monthAgo = new Date(today)
  monthAgo.setDate(monthAgo.getDate() - 30)

  function deltaSince(byDate, sinceDate) {
    const dates = Object.keys(byDate).sort()
    if (dates.length < 2) return null

    const since = isoLocal(sinceDate)
    const latest = dates[dates.length - 1]
    const latestVal = byDate[latest] || 0

    let baseVal = null
    for (const d of dates) {
      if (d < since) baseVal = byDate[d]
    }

    if (baseVal == null) {
      const inWindow = dates.filter((d) => d >= since)
      if (inWindow.length < 2) return null
      baseVal = byDate[inWindow[0]]
    }

    const delta = latestVal - baseVal
    return delta > 0 ? delta : 0
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
        <p class="steam-id" v-if="authStore.user?.steam_id">
          Steam ID: {{ authStore.user.steam_id }}
        </p>

        <div class="gh-block" v-if="progress">
          <div class="gh-row">
            <span class="gh-lvl">GH {{ progress.level }}</span>
            <div class="gh-bar"><i :style="{ width: (progress.pct || 0) + '%' }" /></div>
            <span class="gh-xp">
              {{ progress.xp_into_level ?? 0 }}/{{ progress.xp_per_level ?? 100 }} XP
            </span>
          </div>
          <div class="gh-meta">
            <span class="gh-tag" v-for="t in (progress.tags || [])" :key="t">{{ t }}</span>
            <span class="gh-boost" v-if="progress.boost_credits">
              Бусты: {{ progress.boost_credits }}
            </span>
          </div>
          <div class="gh-ref" v-if="progress.referral_code">
            <span>Твой код:</span>
            <code class="ref-code" @click="copyRefCode" title="Скопировать">
              {{ progress.referral_code }}
            </code>
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
      <button class="btn-primary" type="button" @click="showConnectModal = true">
        + Подключить аккаунт
      </button>
    </div>

    <div v-if="loading" class="state-message">Загружаем аккаунты...</div>
    <div v-else-if="error" class="state-message error-state">{{ error }}</div>
    <div v-else-if="accounts.length === 0" class="state-message empty-state">
      <p>Пока нет подключённых аккаунтов.</p>
      <button class="btn-primary" type="button" @click="showConnectModal = true">
        Подключить первый аккаунт
      </button>
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
          <button
            class="icon-btn danger"
            type="button"
            @click="handleRemove(acc.id)"
            title="Отключить"
          >
            ✕
          </button>
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
          @open-match="openMatch"
        />
        <div v-else class="empty-hint">
          Нажми ↻ на
          {{ platformLabels[activeAccount?.platform] || 'аккаунт' }}, чтобы
          подтянуть статистику
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
              <td class="hours-cell">
                {{ Math.round(row.playtime_forever / 60) }}ч
              </td>
              <td class="today-cell">
                <span v-if="row.week_minutes != null && row.week_minutes > 0">
                  +{{ Math.round(row.week_minutes / 60) }}ч
                </span>
                <span v-else class="muted" title="Нужно минимум 2 дня синка Steam"
                  >—</span
                >
              </td>
              <td class="today-cell">
                <span v-if="row.month_minutes != null && row.month_minutes > 0">
                  +{{ Math.round(row.month_minutes / 60) }}ч
                </span>
                <span v-else class="muted" title="Нужно минимум 2 дня синка Steam"
                  >—</span
                >
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
}
.header-main {
  min-width: 0;
  flex: 1;
}
.profile-header h1 {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 600;
}
.steam-id {
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
  transition: width 0.25s ease;
}
.gh-xp {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}
.gh-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.gh-tag,
.gh-boost {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
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
  font-weight: 700;
  color: var(--accent);
  cursor: pointer;
  background: var(--accent-dim);
  padding: 2px 8px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 12px;
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
  padding: 6px 10px;
}
.btn-ref {
  background: var(--bg-card-hover);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
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
}
.icon-btn {
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  width: 26px;
  height: 26px;
  border-radius: var(--radius-sm);
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
  letter-spacing: 0.05em;
}
.games-table td {
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-color);
}
.games-table tr:last-child td { border-bottom: none; }
.games-table tbody tr:hover { background: var(--bg-card-hover); }
.game-cell { font-weight: 500; }
.hours-cell {
  font-weight: 600;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.today-cell {
  color: var(--success);
  font-size: 12px;
  font-family: var(--font-mono);
}
.muted { color: var(--text-muted); }

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
.error-state { color: var(--danger); }
</style>