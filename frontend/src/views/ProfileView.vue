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

const weeklyWins = computed(() => Number(weekly.value?.wins) || 0)
const weeklyLosses = computed(() => Number(weekly.value?.losses) || 0)
const weeklyTotal = computed(() => weeklyWins.value + weeklyLosses.value)

const weeklyWinPct = computed(() => {
  if (!weeklyTotal.value) return 0
  return Math.round((weeklyWins.value / weeklyTotal.value) * 100)
})

const donutWin = computed(() => {
  if (!weeklyTotal.value) return 0
  return (weeklyWins.value / weeklyTotal.value) * 100
})

/* SVG-кольцо */
const RING_R = 42
const RING_C = 2 * Math.PI * RING_R
const winArc = computed(() => (donutWin.value / 100) * RING_C)

/** Нормализованная форма W/L */
const formList = computed(() => {
  const raw = weekly.value?.recent_form || weekly.value?.form || []
  if (raw.length) {
    return raw.map((f) => {
      if (f === true || f === 'W' || f === 'w') return 'W'
      if (f === false || f === 'L' || f === 'l') return 'L'
      return String(f).toUpperCase().startsWith('W') ? 'W' : 'L'
    })
  }
  // нет form — синтетика из wins/losses (чтобы heatmap не был пустым)
  const list = []
  for (let i = 0; i < weeklyWins.value; i++) list.push('W')
  for (let i = 0; i < weeklyLosses.value; i++) list.push('L')
  return list
})

const weekDays = computed(() => {
  const apiDays = weekly.value?.daily
  if (Array.isArray(apiDays) && apiDays.length) {
    return apiDays.map((d) => {
      const w = Number(d.wins) || 0
      const l = Number(d.losses) || 0
      const m = Number(d.matches) || w + l
      return {
        date: d.date,
        label: formatDayLabel(d.date),
        short: formatDayShort(d.date),
        wins: w,
        losses: l,
        matches: m,
        level: intensity(m),
      }
    })
  }

  const days = last7Dates()
  const form = formList.value
  const buckets = days.map(() => ({ wins: 0, losses: 0 }))

  // Катки с конца недели назад по дням (детерминированно)
  if (form.length) {
    let dayIdx = days.length - 1
    for (let i = form.length - 1; i >= 0; i--) {
      if (form[i] === 'W') buckets[dayIdx].wins++
      else buckets[dayIdx].losses++
      // несколько каток в день, потом шаг
      const inDay = buckets[dayIdx].wins + buckets[dayIdx].losses
      if (inDay >= 2 || i % 2 === 0) {
        dayIdx = Math.max(0, dayIdx - 1)
      }
    }
  }

  return days.map((iso, i) => {
    const w = buckets[i].wins
    const l = buckets[i].losses
    const m = w + l
    return {
      date: iso,
      label: formatDayLabel(iso),
      short: formatDayShort(iso),
      wins: w,
      losses: l,
      matches: m,
      level: intensity(m),
    }
  })
})

/** Доп. инфо по неделе */
const activeDays = computed(() => weekDays.value.filter((d) => d.matches > 0).length)

const bestDay = computed(() => {
  let best = null
  for (const d of weekDays.value) {
    if (d.wins > 0 && (!best || d.wins > best.wins)) best = d
  }
  return best
})

function intensity(matches) {
  if (!matches) return 0
  if (matches === 1) return 1
  if (matches === 2) return 2
  if (matches <= 4) return 3
  return 4
}

/** Цвет дня: win / loss / mix / none */
function dayState(day) {
  if (!day.matches) return 'none'
  if (day.wins > day.losses) return 'win'
  if (day.losses > day.wins) return 'loss'
  return 'mix'
}

function last7Dates() {
  const out = []
  const end = new Date()
  for (let i = 6; i >= 0; i--) {
    const d = new Date(end)
    d.setDate(end.getDate() - i)
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    out.push(`${y}-${m}-${day}`)
  }
  return out
}

function formatDayLabel(iso) {
  try {
    const d = new Date(iso + 'T12:00:00')
    return d.toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric' })
  } catch {
    return iso
  }
}

function formatDayShort(iso) {
  try {
    const d = new Date(iso + 'T12:00:00')
    return String(d.getDate())
  } catch {
    return ''
  }
}

function dayTitle(day) {
  if (!day.matches) return `${day.label}: нет матчей`
  return `${day.label}: ${day.wins}W ${day.losses}L (${day.matches})`
}

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
    <!-- Шапка: слева профиль, справа неделя -->
    <div class="hero card" id="weekly">
      <div class="hero-left">
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

      <div class="hero-right">
        <!-- Заголовок + табы игр -->
        <div class="week-top">
          <div class="week-title">
            <svg class="week-ico" viewBox="0 0 24 24" aria-hidden="true">
              <rect width="18" height="18" x="3" y="4" rx="2" />
              <path d="M16 2v4M8 2v4M3 10h18" />
            </svg>
            <span class="week-kicker">Неделя</span>
            <span class="week-period" v-if="weekly?.period">{{ weekly.period }}</span>
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
          <div class="week-body">
            <!-- Кольцо + форма -->
            <div class="ring-block">
              <div class="ring">
                <svg viewBox="0 0 100 100" class="ring-svg" aria-hidden="true">
                  <circle
                    cx="50"
                    cy="50"
                    :r="RING_R"
                    class="ring-track"
                    :class="{ loss: weeklyLosses > 0 }"
                  />
                  <circle
                    v-if="weeklyWins > 0"
                    cx="50"
                    cy="50"
                    :r="RING_R"
                    class="ring-win"
                    :stroke-dasharray="`${winArc} ${RING_C}`"
                  />
                </svg>
                <div class="ring-center">
                  <span class="ring-pct">{{ weeklyWinPct }}<small>%</small></span>
                  <span class="ring-sub">winrate</span>
                </div>
              </div>
              <div class="form-row" v-if="formList.length">
                <span
                  v-for="(f, i) in formList.slice(0, 8)"
                  :key="i"
                  class="fp"
                  :class="f === 'W' ? 'w' : 'l'"
                >{{ f }}</span>
              </div>
            </div>

            <!-- Справа: карточки, под ними дни недели -->
            <div class="week-side">
              <div class="week-panels">
                <div class="stat-card win">
                  <span class="sc-icon">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
                      <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
                      <path d="M4 22h16" />
                      <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" />
                      <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" />
                      <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
                    </svg>
                  </span>
                  <div class="sc-body">
                    <span class="sc-val">{{ weeklyWins }}</span>
                    <span class="sc-lbl">Побед</span>
                  </div>
                </div>

                <div class="stat-card loss">
                  <span class="sc-icon">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="m12.5 17-.5-1-.5 1h1z" />
                      <path
                        d="M15 22a1 1 0 0 0 1-1v-1a2 2 0 0 0 1.56-3.25 8 8 0 1 0-11.12 0A2 2 0 0 0 8 20v1a1 1 0 0 0 1 1z"
                      />
                      <circle cx="15" cy="12" r="1" />
                      <circle cx="9" cy="12" r="1" />
                    </svg>
                  </span>
                  <div class="sc-body">
                    <span class="sc-val">{{ weeklyLosses }}</span>
                    <span class="sc-lbl">Поражений</span>
                  </div>
                </div>

                <div class="stat-card top" v-if="weekly.best_hero">
                  <span class="sc-icon">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14" />
                    </svg>
                  </span>
                  <div class="sc-body">
                    <span class="sc-val sc-text" :title="weekly.best_hero">{{ weekly.best_hero }}</span>
                    <span class="sc-lbl">Топ</span>
                  </div>
                </div>

                <div class="stat-card streak" v-if="weekly.streak_wins > 1">
                  <span class="sc-icon">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path
                        d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"
                      />
                    </svg>
                  </span>
                  <div class="sc-body">
                    <span class="sc-val">{{ weekly.streak_wins }}</span>
                    <span class="sc-lbl">Серия</span>
                  </div>
                </div>
              </div>

              <div class="heat-block">
                <div class="heat-row">
                  <div
                    v-for="day in weekDays"
                    :key="day.date"
                    class="heat-day"
                    :title="dayTitle(day)"
                  >
                    <span
                      class="hcell"
                      :class="dayState(day)"
                      :style="{ '--k': day.level }"
                    >{{ day.matches || '' }}</span>
                    <span class="heat-label">{{ day.short }}</span>
                  </div>
                </div>

                <div class="heat-foot">
                  <div class="insights">
                    <span class="ins">
                      Дней в игре <b>{{ activeDays }}/{{ weekDays.length }}</b>
                    </span>
                    <span class="ins" v-if="bestDay">
                      Лучший день <b>{{ bestDay.short }}</b> · {{ bestDay.wins }}W
                    </span>
                    <span class="ins">
                      Матчей <b>{{ weeklyTotal }}</b>
                    </span>
                  </div>
                  <div class="heat-scale">
                    <span class="hs-item"><i class="hs-dot win" />W</span>
                    <span class="hs-item"><i class="hs-dot mix" />=</span>
                    <span class="hs-item"><i class="hs-dot loss" />L</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <div v-else class="week-empty">
          Нет матчей за неделю — сыграй или синкни аккаунт.
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

/* —— Hero: профиль | неделя (одна высота) —— */
.hero {
  display: grid;
  grid-template-columns: minmax(260px, 0.8fr) minmax(400px, 1.5fr);
  gap: 20px 24px;
  padding: 16px 20px !important;
  align-items: stretch;
  scroll-margin-top: 72px;
}
@media (max-width: 1100px) {
  .hero {
    grid-template-columns: 1fr;
  }
}

.hero-left {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  min-width: 0;
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
.header-main { min-width: 0; flex: 1; }
.hero h1 {
  margin: 0 0 4px;
  font-size: 20px;
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
  min-width: 80px;
  max-width: 180px;
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
  width: 120px;
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

/* Правая колонка — неделя */
.hero-right {
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding-left: 22px;
  border-left: 1px solid var(--border-color);
}
@media (max-width: 1100px) {
  .hero-right {
    padding-left: 0;
    border-left: none;
    padding-top: 12px;
    border-top: 1px solid var(--border-color);
  }
}

.week-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.week-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.week-ico {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: var(--text-secondary);
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
  flex-shrink: 0;
}
.week-kicker {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-primary);
}
.week-period {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--text-muted);
}
.weekly-tabs { display: flex; flex-wrap: wrap; gap: 4px; }
.wtab {
  font-size: 10px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.wtab:hover { color: var(--text-primary); }
.wtab.active {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-dim);
}

/* Основное тело: кольцо | (карточки + дни) */
.week-body {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 18px;
  align-items: center;
  flex: 1;
}
@media (max-width: 640px) {
  .week-body {
    grid-template-columns: 1fr;
    justify-items: center;
  }
  .week-side { width: 100%; }
}

/* —— Кольцо винрейта (SVG) —— */
.ring-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.ring {
  position: relative;
  width: 100px;
  height: 100px;
}
.ring-svg {
  display: block;
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}
.ring-track,
.ring-win {
  fill: none;
  stroke-width: 9;
}
.ring-track { stroke: var(--bg-sunken); }
.ring-track.loss {
  stroke: var(--danger);
  opacity: 0.85;
}
.ring-win {
  stroke: var(--success);
  stroke-linecap: round;
  transition: stroke-dasharray 0.7s var(--ease, ease);
}
.ring-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  pointer-events: none;
}
.ring-pct {
  font-size: 22px;
  font-weight: 800;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.04em;
  line-height: 1;
  color: var(--text-primary);
}
.ring-pct small {
  font-size: 11px;
  font-weight: 700;
  margin-left: 1px;
  color: var(--text-secondary);
}
.ring-sub {
  font-size: 8px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}

.form-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 3px;
  max-width: 112px;
}
.fp {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  font-size: 9px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}
.fp.w {
  background: rgba(74, 222, 128, 0.18);
  color: var(--success);
}
.fp.l {
  background: rgba(230, 57, 70, 0.16);
  color: var(--danger);
}

/* —— Правая часть —— */
.week-side {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

/* Карточки (компактные) */
.week-panels {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(104px, 1fr));
  gap: 8px;
}
.stat-card {
  --c: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 11px;
  min-width: 0;
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  position: relative;
  overflow: hidden;
}
.stat-card::after {
  content: '';
  position: absolute;
  left: 11px;
  right: 11px;
  bottom: 0;
  height: 2px;
  border-radius: 2px;
  background: linear-gradient(90deg, var(--c), transparent);
  opacity: 0.7;
}
.stat-card.win { --c: var(--success); }
.stat-card.loss { --c: var(--danger); }
.stat-card.top { --c: var(--accent); }
.stat-card.streak { --c: var(--accent); }

.sc-icon {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: color-mix(in srgb, var(--c) 14%, transparent);
  border: 1px solid color-mix(in srgb, var(--c) 35%, transparent);
}
.sc-icon svg {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: var(--c);
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.sc-body {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.sc-val {
  font-size: 18px;
  font-weight: 700;
  font-family: var(--font-mono);
  line-height: 1.1;
  color: var(--c);
}
.sc-val.sc-text {
  font-family: var(--font);
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sc-lbl {
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
}

/* —— Дни недели —— */
.heat-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 6px;
}
.heat-day {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.hcell {
  --k: 0;
  --c: transparent;
  width: 100%;
  max-width: 34px;
  aspect-ratio: 1;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-sunken);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--text-primary);
  box-sizing: border-box;
  margin: 0 auto;
  transition: transform 0.15s;
}
.hcell.win,
.hcell.loss,
.hcell.mix {
  background: color-mix(in srgb, var(--c) calc(14% + var(--k) * 9%), transparent);
  border-color: color-mix(in srgb, var(--c) calc(35% + var(--k) * 10%), transparent);
  box-shadow: 0 0 calc(var(--k) * 4px) color-mix(in srgb, var(--c) 45%, transparent);
}
.hcell.win { --c: var(--success); }
.hcell.loss { --c: var(--danger); }
.hcell.mix { --c: var(--accent); }
.heat-day:hover .hcell { transform: translateY(-2px); }
.heat-label {
  font-size: 9px;
  font-family: var(--font-mono);
  color: var(--text-muted);
}

/* Низ: инсайты слева, легенда справа */
.heat-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 6px 14px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--border-color);
  font-size: 10px;
  color: var(--text-muted);
}
.insights {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
}
.ins b {
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-weight: 700;
}
.heat-scale {
  display: flex;
  align-items: center;
  gap: 10px;
}
.hs-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: var(--font-mono);
}
.hs-dot {
  display: block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: none;
}
.hs-dot.win { background: var(--success); }
.hs-dot.loss { background: var(--danger); }
.hs-dot.mix { background: var(--accent); }

.week-empty {
  font-size: 13px;
  color: var(--text-secondary);
  padding: 16px 0;
  line-height: 1.4;
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
.verified-dot.ok { background: var(--success); }
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

@media (max-width: 900px) {
  .avatar-big { width: 56px; height: 56px; }
  .section-header { flex-direction: column; align-items: stretch; }
  .games-table-card { overflow-x: auto; }
  .games-table { min-width: 480px; }
  .gh-bar { max-width: none; }
}
</style>