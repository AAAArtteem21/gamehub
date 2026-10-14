<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/axios'
import MatchParticipantsModal from '../components/profiles/MatchParticipantsModal.vue'
import ValorantMatchModal from '../components/profiles/ValorantMatchModal.vue'
import UniversalStatsCard from '../components/profiles/UniversalStatsCard.vue'

const route = useRoute()
const router = useRouter()
const profile = ref(null)
const loading = ref(true)
const error = ref(null)
const historyLimit = ref(8)
const openMatchId = ref(null)
const openMatchGame = ref(null)
const isFav = ref(false)

const game = computed(() => String(route.params.game || 'dota2').toLowerCase())
const externalId = computed(() => String(route.params.externalId || ''))

const platform = computed(() => {
  if (game.value === 'dota2' || game.value === 'opendota') return 'opendota'
  return game.value
})

const sourceLabel = computed(() => {
  if (game.value === 'valorant') return 'Данные Valorant (открытый API)'
  if (game.value === 'faceit') return 'Данные Faceit (открытый API)'
  if (game.value === 'deadlock') return 'Данные Deadlock API'
  return 'Данные из открытого источника (OpenDota)'
})

const hasDisplayStats = computed(() => !!profile.value?.display_stats)

const fallbackWinrate = computed(() => {
  if (!profile.value) return null
  const w = profile.value.wins || 0
  const l = profile.value.losses || 0
  const t = w + l
  if (!t) return profile.value.winrate ?? null
  return Math.round((w / t) * 1000) / 10
})

const visibleHistory = computed(() =>
  (profile.value?.match_history || []).slice(0, historyLimit.value)
)
const canExpand = computed(() =>
  (profile.value?.match_history || []).length > historyLimit.value
)

/* ===== Неделя ===== */
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
  if (m.won === true) return true
  if (m.won === false) return false
  const r = String(m.result ?? '').toLowerCase()
  if (r === 'w' || r === 'win') return true
  if (r === 'l' || r === 'loss') return false
  return null
}

const historyRows = computed(() => {
  const p = profile.value
  if (!p) return []
  const src = p.match_history?.length
    ? p.match_history
    : p.display_stats?.match_history || []
  return src
    .map((m) => ({
      won: parseWon(m),
      title: String(m.title || m.hero || m.hero_name || '').trim(),
      date: parsePlayedAt(m.played_at ?? m.date ?? m.started_at ?? m.start_time),
    }))
    .filter((r) => r.date && r.won !== null)
})

const weekly = computed(() => {
  const p = profile.value
  if (!p) return null
  if (p.weekly && typeof p.weekly === 'object') return p.weekly

  const rows = historyRows.value
  if (!rows.length) return null

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

function gPlatform() {
  return platform.value
}

async function load() {
  loading.value = true
  error.value = null
  profile.value = null
  historyLimit.value = 8
  openMatchId.value = null
  openMatchGame.value = null

  const g = game.value
  const eid = externalId.value
  if (!g || !eid || eid === 'undefined') {
    error.value = 'Некорректная ссылка на профиль'
    loading.value = false
    return
  }

  try {
    const res = await api.get(`guest-profile/${g}/${encodeURIComponent(eid)}/`)
    profile.value = res.data
    await loadFavStatus()
  } catch (e) {
    error.value =
      e.response?.data?.detail ||
      `Ошибка ${e.response?.status || ''} — не удалось загрузить профиль`
  } finally {
    loading.value = false
  }
}

async function loadFavStatus() {
  try {
    const res = await api.get('favorites/status/', {
      params: { platform: gPlatform(), external_id: externalId.value },
    })
    isFav.value = !!res.data.favorited
  } catch {
    isFav.value = false
  }
}

async function toggleFav() {
  try {
    const res = await api.post('favorites/toggle/', {
      platform: gPlatform(),
      external_id: externalId.value,
      display_name: profile.value?.display_name || externalId.value,
      avatar_url: profile.value?.avatar_url || '',
    })
    isFav.value = !!res.data.favorited
  } catch (e) {
    alert(e.response?.data?.detail || 'Не удалось изменить избранное')
  }
}

function goToFullProfile() {
  const id = profile.value?.gamehub_user_id
  if (id) router.push(`/players/${id}`)
}

function goCompare() {
  router.push({
    path: '/compare',
    query: {
      platform: gPlatform(),
      external_id: externalId.value,
    },
  })
}

function openRelated(g) {
  if (g?.path) {
    router.push(g.path)
    return
  }
  if (g?.game === 'gamehub' && g.external_id) {
    router.push(`/players/${g.external_id}`)
    return
  }
  const gameName = g?.game || 'dota2'
  const id = encodeURIComponent(g?.external_id || '')
  if (!id) return
  router.push(`/players/guest/${gameName}/${id}`)
}

const isProfileEmpty = computed(() => {
  if (!profile.value) return false
  if (profile.value.is_empty) return true
  if (profile.value.detail_hint) return true
  const w = profile.value.wins || 0
  const l = profile.value.losses || 0
  const hist = profile.value.match_history || []
  const ds = profile.value.display_stats
  if (w === 0 && l === 0 && !hist.length) {
    if (ds?.match_history?.length) return false
    if (game.value === 'deadlock' && (ds || profile.value.tier)) return false
    return true
  }
  return false
})

function showMoreHistory() {
  historyLimit.value = Math.min(
    historyLimit.value + 10,
    (profile.value?.match_history || []).length
  )
}

function openMatch(m) {
  const matchId = typeof m === 'object' ? m?.match_id : m
  if (!matchId) return
  const g = game.value
  if (g === 'valorant') openMatchGame.value = 'valorant'
  else if (g === 'faceit') openMatchGame.value = 'faceit'
  else if (g === 'deadlock') openMatchGame.value = 'deadlock'
  else openMatchGame.value = 'dota2'
  openMatchId.value = matchId
}

function closeMatch() {
  openMatchId.value = null
  openMatchGame.value = null
}

onMounted(load)
watch(() => [route.params.game, route.params.externalId], () => load())
</script>

<template>
  <div class="guest-profile">
    <div v-if="loading" class="state-message">Загружаем профиль...</div>
    <div v-else-if="error" class="state-message error-state">{{ error }}</div>

    <template v-else-if="profile">
      <div class="profile-header hero-grid card" :class="{ single: !weekly }">
        <div class="header-left">
          <div
            class="avatar-big"
            :style="
              profile.avatar_url ? { backgroundImage: `url(${profile.avatar_url})` } : {}
            "
          >
            <span v-if="!profile.avatar_url">?</span>
          </div>
          <div class="header-info">
            <h1 v-if="profile.display_name">{{ profile.display_name }}</h1>
            <h1 v-else class="anon-name">Скрытый профиль</h1>
            <span class="external-badge">{{ sourceLabel }}</span>
            <div class="header-actions">
              <button type="button" class="btn-secondary" @click="router.back()">
                ← Назад
              </button>
              <button type="button" class="btn-secondary" @click="toggleFav">
                {{ isFav ? '★ В избранном' : '☆ В избранное' }}
              </button>
              <button type="button" class="btn-secondary" @click="goCompare">
                Сравнить с собой
              </button>
              <button
                v-if="profile.is_gamehub_user || profile.gamehub_user_id"
                type="button"
                class="gh-link-btn"
                @click="goToFullProfile"
              >
                Полный профиль GameEyes →
              </button>
            </div>
          </div>
        </div>

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
          </div>

          <template v-if="weeklyTotal > 0">
            <div class="week-body">
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
                      <span class="sc-val sc-text" :title="weekly.best_hero">{{
                        weekly.best_hero
                      }}</span>
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

          <div v-else class="week-empty">Нет матчей за неделю.</div>
        </div>
      </div>

      <div class="related-row" v-if="profile.related_games?.length">
        <span class="related-label">Другие игры</span>
        <button
          v-for="(g, i) in profile.related_games"
          :key="(g.path || g.game || '') + '-' + i"
          type="button"
          class="btn-secondary"
          @click="openRelated(g)"
        >
          {{ g.label }}
        </button>
      </div>

      <div v-if="isProfileEmpty" class="card empty-hint-card">
        Статистика недоступна: профиль скрыт в Steam/OpenDota, нет публичных матчей
        или игрок не найден. Это не ошибка сайта.
      </div>

      <div class="card stats-card" v-else-if="hasDisplayStats">
        <UniversalStatsCard :stats="profile.display_stats" :platform="platform" />
      </div>

      <div class="card" v-else>
        <div class="stats-row">
          <div class="stat-box" v-if="profile.wins != null">
            <span class="stat-value win">{{ profile.wins ?? 0 }}</span>
            <span class="stat-label">побед</span>
          </div>
          <div class="stat-box" v-if="profile.losses != null">
            <span class="stat-value loss">{{ profile.losses ?? 0 }}</span>
            <span class="stat-label">поражений</span>
          </div>
          <div class="stat-box" v-if="fallbackWinrate != null">
            <span class="stat-value accent">{{ fallbackWinrate }}%</span>
            <span class="stat-label">винрейт</span>
          </div>
          <div class="stat-box" v-if="profile.mmr_estimate">
            <span class="stat-value accent">{{ profile.mmr_estimate }}</span>
            <span class="stat-label">MMR</span>
          </div>
          <div class="stat-box" v-if="profile.tier && game !== 'faceit'">
            <span class="stat-value accent">{{ profile.tier }}</span>
            <span class="stat-label">ранг</span>
          </div>
          <div
            class="stat-box"
            v-if="game === 'valorant' && profile.rr != null && profile.rr !== ''"
          >
            <span class="stat-value accent">{{ profile.rr }}</span>
            <span class="stat-label">RR</span>
          </div>
          <div class="stat-box" v-if="game === 'faceit' && profile.faceit_elo != null">
            <span class="stat-value accent">{{ profile.faceit_elo }}</span>
            <span class="stat-label">ELO</span>
          </div>
          <div class="stat-box" v-if="game === 'faceit' && profile.skill_level != null">
            <span class="stat-value accent">{{ profile.skill_level }}</span>
            <span class="stat-label">LVL</span>
          </div>
        </div>

        <div class="heroes-section" v-if="profile.top_heroes?.length">
          <h4>{{ game === 'valorant' ? 'Любимые агенты' : 'Любимые герои' }}</h4>
          <div class="hero-row" v-for="h in profile.top_heroes" :key="h.name">
            <span class="hero-name">{{ h.name }}</span>
            <span class="hero-games">{{ h.games }} игр</span>
            <span
              v-if="h.winrate"
              class="hero-winrate"
              :class="{ good: h.winrate >= 50 }"
            >{{ h.winrate }}%</span>
          </div>
        </div>

        <template v-if="profile.match_history?.length">
          <h4 class="section-title">История матчей</h4>
          <div
            v-for="(m, i) in visibleHistory"
            :key="m.match_id || i"
            class="match-row"
            :class="{
              win: m.won === true,
              loss: m.won === false,
              clickable: !!m.match_id,
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
            <span v-if="m.match_id" class="match-chevron">›</span>
          </div>
          <button
            v-if="canExpand"
            type="button"
            class="show-more"
            @click="showMoreHistory"
          >
            Показать ещё
          </button>
        </template>
      </div>
    </template>

    <MatchParticipantsModal
      v-if="openMatchId && openMatchGame === 'dota2'"
      game="dota2"
      :match-id="openMatchId"
      @close="closeMatch"
    />
    <MatchParticipantsModal
      v-if="openMatchId && openMatchGame === 'faceit'"
      game="faceit"
      :match-id="openMatchId"
      @close="closeMatch"
    />
    <ValorantMatchModal
      v-if="openMatchId && openMatchGame === 'valorant'"
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
.guest-profile {
  display: flex;
  flex-direction: column;
  gap: 18px;
  width: 100%;
  animation: fadeInUp 0.25s var(--ease) both;
}

.profile-header {
  padding: 16px 20px !important;
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
  align-items: center;
  gap: 16px;
  min-width: 0;
}
.avatar-big {
  width: 72px;
  height: 72px;
  border-radius: 8px;
  background-color: var(--accent-dim);
  background-size: cover;
  background-position: center;
  border: 1px solid var(--border-color);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 800;
  color: var(--text-muted);
}
.header-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.header-info h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
}
.anon-name {
  color: var(--text-muted);
  font-style: italic;
}
.external-badge {
  font-size: 11px;
  color: var(--text-secondary);
}
.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}
.btn-secondary {
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.btn-secondary:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.gh-link-btn {
  background: var(--accent-dim);
  color: var(--accent);
  border: 1px solid rgba(196, 165, 116, 0.3);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

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
  .week-side {
    width: 100%;
  }
}

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
.ring-track {
  stroke: var(--bg-sunken);
}
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
.stat-card.win {
  --c: var(--success);
}
.stat-card.loss {
  --c: var(--danger);
}
.stat-card.top {
  --c: var(--accent);
}
.stat-card.streak {
  --c: var(--accent);
}

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
.hcell.win {
  --c: var(--success);
}
.hcell.loss {
  --c: var(--danger);
}
.hcell.mix {
  --c: var(--accent);
}
.heat-day:hover .hcell {
  transform: translateY(-2px);
}
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
.hs-dot.win {
  background: var(--success);
}
.hs-dot.loss {
  background: var(--danger);
}
.hs-dot.mix {
  background: var(--accent);
}

.week-empty {
  font-size: 13px;
  color: var(--text-secondary);
  padding: 16px 0;
  line-height: 1.4;
}

.stats-card {
  padding: 16px 18px !important;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  gap: 8px;
  margin-bottom: 16px;
}
.stat-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 6px;
}
.stat-value {
  font-size: 18px;
  font-weight: 800;
  font-family: var(--font-mono);
}
.stat-value.win {
  color: var(--success);
}
.stat-value.loss {
  color: var(--danger);
}
.stat-value.accent {
  color: var(--accent);
}
.stat-label {
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
}

.heroes-section h4,
.section-title {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.hero-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
}
.hero-row:last-child {
  border-bottom: none;
}
.hero-name {
  flex: 1;
  font-weight: 600;
}
.hero-games {
  color: var(--text-secondary);
  font-size: 12px;
}
.hero-winrate {
  font-weight: 700;
  color: var(--danger);
}
.hero-winrate.good {
  color: var(--success);
}

.match-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 8px;
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
  border-radius: 8px;
}
.match-row.clickable {
  cursor: pointer;
}
.match-row.clickable:hover {
  background: var(--bg-card-hover);
}
.match-result {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
  flex-shrink: 0;
}
.match-row.win .match-result {
  background: rgba(74, 222, 128, 0.15);
  color: var(--success);
}
.match-row.loss .match-result {
  background: rgba(248, 113, 113, 0.15);
  color: var(--danger);
}
.match-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.match-title {
  font-weight: 700;
}
.match-meta {
  font-size: 11px;
  color: var(--text-secondary);
}
.match-kda {
  font-family: var(--font-mono);
  color: var(--text-secondary);
}
.match-chevron {
  color: var(--text-muted);
  font-size: 18px;
}
.show-more {
  width: 100%;
  margin-top: 8px;
  padding: 10px;
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--accent);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
}
.show-more:hover {
  border-color: var(--accent);
}

.related-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.related-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-right: 4px;
}
.empty-hint-card {
  padding: 20px 18px !important;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.45;
  border: 1px dashed var(--border-color);
}

.state-message {
  padding: 40px 20px;
  text-align: center;
  color: var(--text-secondary);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}
.error-state {
  color: var(--danger);
}

@media (max-width: 900px) {
  .header-left {
    flex-direction: column;
    align-items: stretch;
  }
  .avatar-big {
    width: 56px;
    height: 56px;
  }
}
</style>