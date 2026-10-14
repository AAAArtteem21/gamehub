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

/** Доля побед для conic-gradient (0–100) */
const donutWin = computed(() => {
  if (!weeklyTotal.value) return 0
  return (weeklyWins.value / weeklyTotal.value) * 100
})

const formList = computed(() => {
  const raw = weekly.value?.recent_form || weekly.value?.form || []
  return raw.map((f) => {
    if (f === true || f === 'W' || f === 'w') return 'W'
    if (f === false || f === 'L' || f === 'l') return 'L'
    return String(f).toUpperCase().startsWith('W') ? 'W' : 'L'
  })
})

/**
 * Дни недели для heatmap.
 * Приоритет: weekly.daily [{ date, wins, losses, matches }]
 * Иначе — 7 дней от period / сегодня, матчи раскидываем по recent_form с конца.
 */
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
        wins: w,
        losses: l,
        matches: m,
        level: intensity(m),
      }
    })
  }

  const days = last7Dates()
  const form = [...formList.value]
  // раскладываем форму с конца по дням (грубая визуализация, пока нет daily с бэка)
  const buckets = days.map(() => ({ wins: 0, losses: 0 }))
  let di = days.length - 1
  for (let i = form.length - 1; i >= 0 && di >= 0; i--) {
    if (form[i] === 'W') buckets[di].wins++
    else buckets[di].losses++
    // следующий матч — тот же день с вероятностью, иначе шаг назад
    if (Math.random() > 0.55) di = Math.max(0, di - 1)
  }
  // детерминированнее: равномерно по дням с конца
  const clean = days.map(() => ({ wins: 0, losses: 0 }))
  let idx = days.length - 1
  for (let i = form.length - 1; i >= 0; i--) {
    if (form[i] === 'W') clean[idx].wins++
    else clean[idx].losses++
    idx = idx <= 0 ? days.length - 1 : idx - 1
  }

  return days.map((iso, i) => {
    const w = clean[i].wins
    const l = clean[i].losses
    const m = w + l
    return {
      date: iso,
      label: formatDayLabel(iso),
      wins: w,
      losses: l,
      matches: m,
      level: intensity(m),
    }
  })
})

function intensity(matches) {
  if (!matches) return 0
  if (matches === 1) return 1
  if (matches === 2) return 2
  if (matches <= 4) return 3
  return 4
}

function last7Dates() {
  const out = []
  const end = new Date()
  for (let i = 6; i >= 0; i--) {
    const d = new Date(end)
    d.setDate(end.getDate() - i)
    out.push(d.toISOString().slice(0, 10))
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

    <!-- ========== НЕДЕЛЯ ========== -->
    <section id="weekly" class="card weekly-card">
      <div class="weekly-head">
        <div>
          <h2 class="weekly-title">Эта неделя</h2>
          <p class="weekly-period" v-if="weekly?.period">{{ weekly.period }}</p>
          <p class="weekly-period" v-else>Последние 7 дней</p>
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
        <div class="weekly-body">
          <!-- Кольцо -->
          <div class="donut-wrap">
            <div
              class="donut"
              :style="{
                background: `conic-gradient(
                  var(--success) 0 ${donutWin}%,
                  var(--danger) ${donutWin}% 100%
                )`,
              }"
            >
              <div class="donut-hole">
                <span class="donut-pct">{{ weeklyWinPct }}%</span>
                <span class="donut-sub">винрейт</span>
              </div>
            </div>
            <div class="donut-legend">
              <span class="leg win"><i />{{ weeklyWins }} побед</span>
              <span class="leg loss"><i />{{ weeklyLosses }} пораж.</span>
              <span class="leg mute">{{ weeklyTotal }} матчей</span>
            </div>
          </div>

          <!-- Цифры + форма -->
          <div class="weekly-side">
            <div class="weekly-stats">
              <div class="wstat">
                <span class="wstat-val win">{{ weeklyWins }}</span>
                <span class="wstat-lbl">W</span>
              </div>
              <div class="wstat">
                <span class="wstat-val loss">{{ weeklyLosses }}</span>
                <span class="wstat-lbl">L</span>
              </div>
              <div class="wstat" v-if="weekly.streak_wins > 1">
                <span class="wstat-val accent">{{ weekly.streak_wins }}</span>
                <span class="wstat-lbl">серия</span>
              </div>
              <div class="wstat" v-if="weekly.best_hero">
                <span class="wstat-val hero">{{ weekly.best_hero }}</span>
                <span class="wstat-lbl">топ</span>
              </div>
            </div>

            <div class="form-block" v-if="formList.length">
              <span class="extra-lbl">Последние катки</span>
              <div class="form-pills">
                <span
                  v-for="(f, i) in formList.slice(0, 16)"
                  :key="i"
                  class="fp"
                  :class="f === 'W' ? 'w' : 'l'"
                >{{ f }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Heatmap как commits -->
        <div class="heat-block">
          <div class="heat-head">
            <span class="extra-lbl">Активность по дням</span>
            <div class="heat-scale">
              <span>меньше</span>
              <i class="hcell l0" /><i class="hcell l1" /><i class="hcell l2" /><i class="hcell l3" /><i class="hcell l4" />
              <span>больше</span>
            </div>
          </div>
          <div class="heat-row">
            <button
              v-for="day in weekDays"
              :key="day.date"
              type="button"
              class="heat-day"
              :title="dayTitle(day)"
            >
              <span
                class="hcell"
                :class="'l' + day.level"
              />
              <span class="heat-label">{{ day.label }}</span>
              <span class="heat-count" v-if="day.matches">{{ day.matches }}</span>
            </button>
          </div>
        </div>
      </template>

      <div v-else class="weekly-empty">
        <div class="empty-visual" aria-hidden="true">
          <span class="hcell l0" /><span class="hcell l0" /><span class="hcell l1" /><span class="hcell l0" /><span class="hcell l0" /><span class="hcell l0" /><span class="hcell l0" />
        </div>
        <p>Пока нет матчей за эту неделю.</p>
        <p class="empty-hint-line">Сыграй или нажми ↻ на игровом аккаунте — здесь появится кольцо, форма и календарь каток.</p>
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
.header-main { min-width: 0; flex: 1; }
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

/* —— Weekly showcase —— */
.weekly-card {
  padding: 20px 22px !important;
  scroll-margin-top: 72px;
  background:
    radial-gradient(ellipse 80% 60% at 0% 0%, var(--accent-dim), transparent 55%),
    var(--bg-card);
}
.weekly-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}
.weekly-title {
  margin: 0 0 4px;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-secondary);
}
.weekly-period {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}
.weekly-tabs { display: flex; flex-wrap: wrap; gap: 4px; }
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

.weekly-body {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 28px;
  align-items: center;
}
@media (max-width: 700px) {
  .weekly-body { grid-template-columns: 1fr; justify-items: center; }
}

.donut-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}
.donut {
  width: 140px;
  height: 140px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 0 1px var(--border-color), 0 8px 32px rgba(0, 0, 0, 0.35);
}
.donut-hole {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: var(--bg-card);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  border: 1px solid var(--border-color);
}
.donut-pct {
  font-size: 28px;
  font-weight: 800;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em;
  line-height: 1;
}
.donut-sub {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
}
.donut-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  justify-content: center;
  font-size: 12px;
}
.leg {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
}
.leg i {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  display: inline-block;
}
.leg.win i { background: var(--success); }
.leg.loss i { background: var(--danger); }
.leg.mute { color: var(--text-muted); }

.weekly-side { width: 100%; min-width: 0; }
.weekly-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(70px, 1fr));
  gap: 8px;
  margin-bottom: 16px;
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
  font-size: 22px;
  font-weight: 700;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.wstat-val.win { color: var(--success); }
.wstat-val.loss { color: var(--danger); }
.wstat-val.accent { color: var(--accent); }
.wstat-val.hero {
  font-size: 13px;
  font-weight: 700;
  font-family: var(--font);
  text-align: center;
  line-height: 1.2;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wstat-lbl {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.extra-lbl {
  display: block;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 8px;
}
.form-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.fp {
  width: 24px;
  height: 24px;
  border-radius: 5px;
  font-size: 10px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}
.fp.w {
  background: rgba(74, 222, 128, 0.18);
  color: var(--success);
  box-shadow: inset 0 0 0 1px rgba(74, 222, 128, 0.25);
}
.fp.l {
  background: rgba(230, 57, 70, 0.15);
  color: var(--danger);
  box-shadow: inset 0 0 0 1px rgba(230, 57, 70, 0.25);
}

/* Heatmap */
.heat-block {
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid var(--border-color);
}
.heat-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.heat-scale {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: var(--text-muted);
}
.heat-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
}
.heat-day {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  padding: 0;
  cursor: default;
  color: inherit;
}
.hcell {
  width: 100%;
  aspect-ratio: 1;
  max-width: 44px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  display: block;
  margin: 0 auto;
  transition: transform 0.12s var(--ease);
}
.heat-day:hover .hcell {
  transform: scale(1.06);
}
.hcell.l0 { background: var(--bg-sunken); }
.hcell.l1 { background: rgba(230, 57, 70, 0.22); border-color: transparent; }
.hcell.l2 { background: rgba(230, 57, 70, 0.4); border-color: transparent; }
.hcell.l3 { background: rgba(230, 57, 70, 0.65); border-color: transparent; }
.hcell.l4 {
  background: var(--accent);
  border-color: transparent;
  box-shadow: 0 0 12px var(--accent-dim);
}
.heat-label {
  font-size: 10px;
  color: var(--text-muted);
  text-align: center;
  line-height: 1.2;
}
.heat-count {
  font-size: 10px;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--text-secondary);
}

.weekly-empty {
  text-align: center;
  padding: 28px 12px 12px;
  color: var(--text-secondary);
  font-size: 14px;
}
.empty-visual {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-bottom: 16px;
}
.empty-visual .hcell {
  width: 28px;
  height: 28px;
  max-width: none;
  aspect-ratio: auto;
}
.empty-hint-line {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--text-muted);
  max-width: 360px;
  margin-left: auto;
  margin-right: auto;
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
  .profile-header { flex-direction: column; align-items: stretch; }
  .avatar-big { width: 56px; height: 56px; }
  .section-header { flex-direction: column; align-items: stretch; }
  .games-table-card { overflow-x: auto; }
  .games-table { min-width: 480px; }
  .gh-bar { max-width: none; }
  .heat-row { gap: 4px; }
  .heat-label { font-size: 9px; }
}
</style>