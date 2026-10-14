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

const weekly = ref(null)
const weeklyGame = ref('all')

const platformLabels = {
  steam: 'Steam',
  faceit: 'Faceit',
  opendota: 'OpenDota',
  lol: 'League of Legends',
  valorant: 'Valorant',
  fortnite: 'Fortnite',
  deadlock: 'Deadlock',
  pubg: 'PUBG',
  roblox: 'Roblox',
  manual: 'Ручной',
}

const statsAccounts = computed(() =>
  accounts.value.filter(
    (a) =>
      ['opendota', 'faceit', 'deadlock', 'lol', 'valorant', 'fortnite', 'pubg', 'roblox'].includes(
        a.platform
      ) || (a.platform === 'steam' && a.display_stats)
  )
)

const activeAccount = computed(
  () => statsAccounts.value.find((a) => a.id === activeStatsTab.value) || statsAccounts.value[0]
)

const steamLibraryRows = computed(() => {
  const steam = accounts.value.find((a) => a.platform === 'steam')
  const lib = steam?.summary?.library
  if (!Array.isArray(lib)) return []
  return lib.map((g) => ({
    appid: g.appid,
    game_name: g.name,
    hours_total: Number(g.hours_total) || 0,
    hours_2weeks: g.hours_2weeks == null ? null : Number(g.hours_2weeks),
  }))
})

const weeklyWinPct = computed(() => {
  if (!weekly.value) return 0
  const t = (weekly.value.wins || 0) + (weekly.value.losses || 0)
  if (!t) return 0
  return Math.round((weekly.value.wins / t) * 100)
})

const weeklyTotal = computed(() => {
  if (!weekly.value) return 0
  return (weekly.value.wins || 0) + (weekly.value.losses || 0)
})

async function loadWeekly() {
  try {
    const params = {}
    if (weeklyGame.value && weeklyGame.value !== 'all') {
      params.game = weeklyGame.value
    }
    const res = await api.get('me/weekly-report/', { params })
    weekly.value = res.data
  } catch {
    weekly.value = null
  }
}

function setWeeklyGame(g) {
  weeklyGame.value = g
  loadWeekly()
}

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

function onAccountCreated(payload) {
  const newAccount = payload?.account || payload
  const linked = payload?.linked || []

  if (newAccount?.id) {
    accounts.value.unshift(newAccount)
    activeStatsTab.value = newAccount.id
  }
  showConnectModal.value = false

  if (linked.length) {
    const names = linked.map((l) => platformLabels[l.platform] || l.platform).join(', ')
    toast.success(`По Steam также подключили: ${names}`)
    setTimeout(loadAccounts, 4000)
    setTimeout(loadAccounts, 14000)
  }

  if (newAccount?.platform !== 'steam' && newAccount?.id) {
    handleSync(newAccount.id)
  } else {
    loadAccounts()
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
        loadWeekly()
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

function openMatch(matchId) {
  if (!matchId || !activeAccount.value) return
  const p = String(activeAccount.value.platform || '').toLowerCase()
  if (p === 'valorant') openMatchGame.value = 'valorant'
  else if (p === 'faceit') openMatchGame.value = 'faceit'
  else if (p === 'opendota' || p === 'dota2') openMatchGame.value = 'dota2'
  else if (p === 'deadlock') openMatchGame.value = 'deadlock'
  else return
  openMatchId.value = matchId
}

function closeMatch() {
  openMatchId.value = null
  openMatchGame.value = null
}

onMounted(() => {
  loadAccounts()
  loadProgress()
  loadWeekly()
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

    <!-- Недельный отчёт -->
    <section id="weekly" class="card weekly-card">
      <div class="weekly-head">
        <div>
          <h2 class="weekly-title">Эта неделя</h2>
          <p class="weekly-period" v-if="weekly?.period">{{ weekly.period }}</p>
        </div>
        <div class="weekly-tabs" v-if="(weekly?.available_games || []).length">
          <button
            type="button"
            class="wtab"
            :class="{ active: weeklyGame === 'all' }"
            @click="setWeeklyGame('all')"
          >Все</button>
          <button
            v-for="g in weekly.available_games"
            :key="g.value"
            type="button"
            class="wtab"
            :class="{ active: weeklyGame === g.value }"
            @click="setWeeklyGame(g.value)"
          >{{ g.label }}</button>
        </div>
      </div>

      <template v-if="weekly && weeklyTotal > 0">
        <div class="weekly-stats">
          <div class="wstat">
            <span class="wstat-val accent">{{ weeklyWinPct }}%</span>
            <span class="wstat-lbl">винрейт</span>
          </div>
          <div class="wstat">
            <span class="wstat-val win">{{ weekly.wins }}</span>
            <span class="wstat-lbl">побед</span>
          </div>
          <div class="wstat">
            <span class="wstat-val loss">{{ weekly.losses }}</span>
            <span class="wstat-lbl">поражений</span>
          </div>
          <div class="wstat">
            <span class="wstat-val">{{ weeklyTotal }}</span>
            <span class="wstat-lbl">матчей</span>
          </div>
          <div class="wstat" v-if="weekly.streak_wins > 1">
            <span class="wstat-val win">{{ weekly.streak_wins }}</span>
            <span class="wstat-lbl">серия W</span>
          </div>
        </div>

        <div class="weekly-extra" v-if="weekly.best_hero || (weekly.recent_form || []).length">
          <div class="weekly-best" v-if="weekly.best_hero">
            <span class="extra-lbl">Лучший</span>
            <span class="extra-val">{{ weekly.best_hero }}</span>
          </div>
          <div class="weekly-form" v-if="(weekly.recent_form || []).length">
            <span class="extra-lbl">Форма</span>
            <div class="form-pills">
              <span
                v-for="(f, i) in weekly.recent_form.slice(0, 12)"
                :key="i"
                class="fp"
                :class="f === 'W' || f === true ? 'w' : 'l'"
              >{{ f === true ? 'W' : f === false ? 'L' : f }}</span>
            </div>
          </div>
        </div>
      </template>

      <div v-else class="weekly-empty">
        Пока нет матчей за эту неделю — сыграй или нажми ↻ на игровом аккаунте.
      </div>
    </section>

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

      <div class="card games-table-card" v-if="steamLibraryRows.length">
        <h3 class="card-title table-title">Библиотека Steam — все игры</h3>
        <table class="games-table">
          <thead>
            <tr>
              <th>Игра</th>
              <th>Часы всего</th>
              <th>За 2 недели</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in steamLibraryRows" :key="row.appid">
              <td class="game-cell">{{ row.game_name }}</td>
              <td class="hours-cell">{{ Math.round(row.hours_total) }}ч</td>
              <td class="today-cell">
                <template v-if="row.hours_2weeks != null">
                  <span v-if="row.hours_2weeks > 0">{{ row.hours_2weeks }}ч</span>
                  <span v-else class="muted">0ч</span>
                </template>
                <span v-else class="muted" title="Нажми ↻ на Steam, чтобы обновить">—</span>
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
    <MatchParticipantsModal
      v-if="openMatchId && openMatchGame === 'faceit'"
      game="faceit"
      :match-id="openMatchId"
      @close="closeMatch"
    />
    <MatchParticipantsModal
      v-if="openMatchId && openMatchGame === 'deadlock'"
      game="deadlock"
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
.btn-ref:disabled {
  opacity: 0.5;
}

/* Weekly */
.weekly-card {
  padding: 18px 20px !important;
  scroll-margin-top: 72px;
}
.weekly-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.weekly-title {
  margin: 0 0 4px;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
}
.weekly-period {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}
.weekly-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.wtab {
  font-size: 11px;
  font-weight: 600;
  padding: 5px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
}
.wtab.active {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-dim);
}
.weekly-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(72px, 1fr));
  gap: 10px;
}
.wstat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 8px;
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}
.wstat-val {
  font-size: 20px;
  font-weight: 700;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.wstat-val.accent { color: var(--accent); }
.wstat-val.win { color: var(--success); }
.wstat-val.loss { color: var(--danger); }
.wstat-lbl {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}
.weekly-extra {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 16px 24px;
  align-items: center;
}
.extra-lbl {
  display: block;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 4px;
}
.extra-val {
  font-size: 14px;
  font-weight: 600;
}
.form-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.fp {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}
.fp.w {
  background: rgba(74, 222, 128, 0.15);
  color: var(--success);
}
.fp.l {
  background: rgba(230, 57, 70, 0.15);
  color: var(--danger);
}
.weekly-empty {
  padding: 20px 8px;
  text-align: center;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.45;
}

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
.platform-label {
  font-weight: 600;
  font-size: 12px;
}
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
.icon-btn:disabled {
  opacity: 0.5;
}
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
.table-title {
  padding: 14px 16px 0;
}
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
.games-table tr:last-child td {
  border-bottom: none;
}
.games-table tbody tr:hover {
  background: var(--bg-card-hover);
}
.game-cell {
  font-weight: 500;
}
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
.muted {
  color: var(--text-muted);
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
}

@media (max-width: 900px) {
  .profile-header {
    flex-direction: column;
    align-items: stretch;
  }
  .avatar-big {
    width: 56px;
    height: 56px;
  }
  .section-header {
    flex-direction: column;
    align-items: stretch;
  }
  .games-table-card {
    overflow-x: auto;
  }
  .games-table {
    min-width: 480px;
  }
  .gh-bar {
    max-width: none;
  }
}
</style>