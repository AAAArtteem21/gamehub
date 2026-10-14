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
const weeklyGame = ref('all')

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
      ['opendota', 'faceit', 'deadlock', 'lol', 'valorant', 'fortnite', 'pubg', 'roblox'].includes(a.platform)
  )
)

const activeAccount = computed(
  () =>
    statsAccounts.value.find((a) => a.id === activeTab.value) ||
    statsAccounts.value[0] ||
    null
)

/* =====================================================================
   НЕДЕЛЯ (та же статистика, что на своём профиле)
   Если бэк отдаёт profile.weekly в формате me/weekly-report/ — берём его.
   Иначе считаем из display_stats.match_history всех аккаунтов за 7 дней.
   ===================================================================== */

const RING_R = 42
const RING_C = 2 * Math.PI * RING_R

function pad2(n) {
  return String(n).padStart(2, '0')
}

function isoLocal(d) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

function last7Dates() {
  const out = []
  const end = new Date()
  for (let i = 6; i >= 0; i--) {
    const d = new Date(end)
    d.setDate(end.getDate() - i)
    out.push(isoLocal(d))
  }
  return out
}

/** Парсит дату матча: dd.mm.yyyy [hh:mm], ISO, unix-секунды/миллисекунды */
function parsePlayedAt(v) {
  if (v == null || v === '') return null
  if (v instanceof Date) return isNaN(v.getTime()) ? null : v
  if (typeof v === 'number') {
    const d = new Date(v < 1e12 ? v * 1000 : v)
    return isNaN(d.getTime()) ? null : d
  }
  const s = String(v).trim()
  let m = s.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})(?:\D+(\d{1,2}):(\d{2}))?/)
  if (m) return new Date(+m[3], +m[2] - 1, +m[1], +(m[4] || 12), +(m[5] || 0))
  m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (m) return new Date(+m[1], +m[2] - 1, +m[3], 12, 0)
  if (/^\d{9,13}$/.test(s)) {
    const n = Number(s)
    const d = new Date(n < 1e12 ? n * 1000 : n)
    return isNaN(d.getTime()) ? null : d
  }
  const d = new Date(s)
  return isNaN(d.getTime()) ? null : d
}

function parseWon(m) {
  if (m.won === true || m.win === true || m.is_win === true) return true
  if (m.won === false || m.win === false || m.is_win === false) return false
  const r = String(m.result ?? '').toLowerCase()
  if (r === 'w' || r === 'win') return true
  if (r === 'l' || r === 'loss') return false
  return null
}

/** Все матчи всех аккаунтов в нормализованном виде */
const historyRows = computed(() => {
  const rows = []
  for (const acc of statsAccounts.value) {
    const src = acc.display_stats?.match_history || []
    for (const m of src) {
      const won = parseWon(m)
      const date = parsePlayedAt(m.played_at ?? m.date ?? m.started_at ?? m.start_time)
      if (won === null || !date) continue
      rows.push({
        accId: acc.id,
        won,
        date,
        title: String(m.title || m.hero || m.hero_name || '').trim(),
      })
    }
  }
  return rows
})

/** Табы игр для недели (только если больше одной игры) */
const weeklyGames = computed(() => {
  const ids = new Set(historyRows.value.map((r) => r.accId))
  return statsAccounts.value
    .filter((a) => ids.has(a.id))
    .map((a) => ({
      value: a.id,
      label: a.display_stats?.game_label || platformLabels[a.platform] || a.platform,
    }))
})

const weekly = computed(() => {
  const p = profile.value
  if (!p) return null

  // бэк уже отдал готовую неделю
  if (p.weekly && typeof p.weekly === 'object') return p.weekly

  if (!historyRows.value.length) return null

  const rows =
    weeklyGame.value === 'all'
      ? historyRows.value
      : historyRows.value.filter((r) => r.accId === weeklyGame.value)

  const days = last7Dates()
  const buckets = Object.fromEntries(days.map((d) => [d, { wins: 0, losses: 0 }]))
  const weekRows = []

  for (const r of rows) {
    const key = isoLocal(r.date)
    if (!buckets[key]) continue
    if (r.won) buckets[key].wins++
    else buckets[key].losses++
    weekRows.push(r)
  }

  weekRows.sort((a, b) => a.date - b.date)

  const wins = weekRows.filter((r) => r.won).length
  const losses = weekRows.length - wins

  // топ — самый частый победный заголовок (герой/агент/карта)
  const winCount = {}
  for (const r of weekRows) {
    if (r.won && r.title) winCount[r.title] = (winCount[r.title] || 0) + 1
  }
  let bestHero = null
  let bestN = 0
  for (const [name, n] of Object.entries(winCount)) {
    if (n > bestN) {
      bestHero = name
      bestN = n
    }
  }

  // текущая серия побед (с самого свежего матча)
  let streak = 0
  for (let i = weekRows.length - 1; i >= 0; i--) {
    if (weekRows[i].won) streak++
    else break
  }

  const fmt = (iso) => `${iso.slice(8, 10)}.${iso.slice(5, 7)}`

  return {
    period: `${fmt(days[0])} – ${fmt(days[6])}`,
    wins,
    losses,
    best_hero: bestHero,
    streak_wins: streak,
    recent_form: weekRows.map((r) => (r.won ? 'W' : 'L')),
    daily: days.map((d) => ({
      date: d,
      wins: buckets[d].wins,
      losses: buckets[d].losses,
      matches: buckets[d].wins + buckets[d].losses,
    })),
  }
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

  if (form.length) {
    let dayIdx = days.length - 1
    for (let i = form.length - 1; i >= 0; i--) {
      if (form[i] === 'W') buckets[dayIdx].wins++
      else buckets[dayIdx].losses++
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

function setWeeklyGame(g) {
  weeklyGame.value = g
}

/* ===================================================================== */

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
  weeklyGame.value = 'all'

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
  if (p === 'valorant') openMatchGame.value = 'valorant'
  else if (p === 'faceit') openMatchGame.value = 'faceit'
  else if (p === 'opendota' || p === 'dota2') openMatchGame.value = 'dota2'
  else if (p === 'deadlock') {
    openMatchGame.value = 'deadlock'
    openMatchId.value = matchId
  }
  else return
  openMatchId.value = matchId
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
      <div class="profile-header hero-grid card" :class="{ single: !weekly }">
        <!-- Слева: профиль -->
        <div class="header-left">
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

        <!-- Справа: неделя -->
        <div class="hero-right" v-if="weekly">
          <div class="week-top">
            <div class="week-title">
              <svg class="week-ico" viewBox="0 0 24 24" aria-hidden="true">
                <rect width="18" height="18" x="3" y="4" rx="2" />
                <path d="M16 2v4M8 2v4M3 10h18" />
              </svg>
              <span class="week-kicker">Неделя</span>
              <span class="week-period" v-if="weekly.period">{{ weekly.period }}</span>
            </div>
            <div class="weekly-tabs" v-if="!profile.weekly && weeklyGames.length > 1">
              <button
                type="button"
                class="wtab"
                :class="{ active: weeklyGame === 'all' }"
                @click="setWeeklyGame('all')"
              >Все</button>
              <button
                v-for="g in weeklyGames"
                :key="g.value"
                type="button"
                class="wtab"
                :class="{ active: weeklyGame === g.value }"
                @click="setWeeklyGame(g.value)"
              >{{ g.label }}</button>
            </div>
          </div>

          <template v-if="weeklyTotal > 0">
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
                    v-for="(f, i) in formList.slice(-8)"
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
            Нет матчей за неделю.
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
    <MatchParticipantsModal
      v-if="openMatchId && openMatchGame === 'faceit'"
      game="faceit"
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

/* —— Шапка: профиль | неделя (одна высота) —— */
.profile-header {
  padding: 16px 20px !important;
  width: 100%;
}
.hero-grid {
  display: grid;
  grid-template-columns: minmax(280px, 0.9fr) minmax(400px, 1.5fr);
  gap: 20px 24px;
  align-items: stretch;
}
.hero-grid.single {
  grid-template-columns: 1fr;
}
@media (max-width: 1100px) {
  .hero-grid {
    grid-template-columns: 1fr;
  }
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 16px;
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

/* —— Правая колонка: неделя —— */
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

/* Кольцо винрейта (SVG) */
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

.week-side {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

/* Карточки */
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

/* Дни недели */
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

/* —— Остальное —— */
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
  .header-left { flex-direction: column; align-items: stretch; }
  .avatar-big { width: 56px; height: 56px; }
  .games-table-card { overflow-x: auto; }
  .games-table { min-width: 420px; }
  .gh-bar { max-width: none; }
}
</style>