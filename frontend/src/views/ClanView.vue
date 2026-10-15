<script setup>
import { ref, computed, onMounted } from 'vue'
import { clansApi } from '../api/clans'
import api from '../api/axios'
import CreateClanModal from '../components/clans/CreateClanModal.vue'
import JoinClanModal from '../components/clans/JoinClanModal.vue'
import ClanDashboardTable from '../components/clans/ClanDashboardTable.vue'
import ClanIcon from '../components/clans/ClanIcon.vue'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../composables/useToast'

const auth = useAuthStore()
const toast = useToast()

const clans = ref([])
const loading = ref(true)
const error = ref(null)
const showCreateModal = ref(false)
const showJoinModal = ref(false)

const searchQuery = ref('')
const filter = ref('all') // all | mine | open | closed
const gameFilter = ref('')
const sortBy = ref('members') // members | name | new

const leaderboard = ref([])
const leaderboardLoading = ref(true)

const selectedClan = ref(null)
const dashboard = ref([])
const dashboardLoading = ref(false)
const dashboardError = ref(null)

const logoUploading = ref(false)
const logoInput = ref(null)

const roleLabels = { leader: 'Лидер', officer: 'Офицер', member: 'Участник' }

/* ---------- Сводка ---------- */
const stats = computed(() => {
  const list = clans.value
  return {
    total: list.length,
    members: list.reduce((s, c) => s + (Number(c.members_count) || 0), 0),
    mine: list.filter((c) => c.is_member).length,
    open: list.filter((c) => c.is_open).length,
  }
})

const games = computed(() => {
  const map = new Map()
  for (const c of clans.value) {
    const key = c.game || c.game_label
    if (key && !map.has(key)) map.set(key, c.game_label || c.game)
  }
  return [...map.entries()].map(([value, label]) => ({ value, label }))
})

const filters = computed(() => [
  { id: 'all', label: 'Все', count: stats.value.total },
  { id: 'mine', label: 'Мои', count: stats.value.mine },
  { id: 'open', label: 'Открытые', count: stats.value.open },
  { id: 'closed', label: 'Закрытые', count: stats.value.total - stats.value.open },
])

const filteredClans = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  let list = clans.value.filter((c) => {
    if (q && !String(c.name || '').toLowerCase().includes(q)) return false
    if (filter.value === 'mine' && !c.is_member) return false
    if (filter.value === 'open' && !c.is_open) return false
    if (filter.value === 'closed' && c.is_open) return false
    if (gameFilter.value && (c.game || c.game_label) !== gameFilter.value) return false
    return true
  })
  list = [...list]
  if (sortBy.value === 'members') {
    list.sort((a, b) => (b.members_count || 0) - (a.members_count || 0))
  } else if (sortBy.value === 'name') {
    list.sort((a, b) => String(a.name).localeCompare(String(b.name), 'ru'))
  } else if (sortBy.value === 'new') {
    list.sort((a, b) => (b.id || 0) - (a.id || 0))
  }
  // свои кланы всегда выше при сортировке по участникам
  if (sortBy.value === 'members') {
    list.sort((a, b) => Number(!!b.is_member) - Number(!!a.is_member))
  }
  return list
})

/* ---------- Хелперы ---------- */
function isLeader(clan) {
  return clan?.my_role === 'leader'
}

function hasLogo(c) {
  return !!(c?.logo_url || c?.logo)
}

function hue(name) {
  let h = 0
  for (const ch of String(name || '')) h = (h * 31 + ch.charCodeAt(0)) % 360
  return h
}

function initials(name) {
  const parts = String(name || '?').trim().split(/\s+/)
  const s = parts.length > 1 ? parts[0][0] + parts[1][0] : parts[0].slice(0, 2)
  return s.toUpperCase()
}

function avatarStyle(name) {
  const h = hue(name)
  return {
    background: `linear-gradient(135deg, hsl(${h} 65% 52%), hsl(${(h + 35) % 360} 65% 36%))`,
  }
}

function capacity(clan) {
  if (!clan.max_members) return null
  return Math.min(100, Math.round(((clan.members_count || 0) / clan.max_members) * 100))
}

function formatHours(min) {
  if (!min) return '0ч'
  const h = min / 60
  return h >= 10 ? `${Math.round(h)}ч` : `${(Math.round(h * 10) / 10).toFixed(1)}ч`
}

function lbSub(c) {
  if (c.wins != null && c.losses != null) return `${c.wins}W · ${c.losses}L`
  return `${c.members_count} уч. · ${formatHours(c.total_two_weeks_minutes ?? c.total_minutes ?? 0)}`
}

function openCreate() {
  if (auth.requireAuth('Войди через Steam, чтобы создать клан.')) showCreateModal.value = true
}
function openJoin() {
  if (auth.requireAuth('Войди через Steam, чтобы вступить в клан.')) showJoinModal.value = true
}

function resetFilters() {
  searchQuery.value = ''
  filter.value = 'all'
  gameFilter.value = ''
}

/* ---------- Загрузка ---------- */
async function loadClans() {
  loading.value = true
  error.value = null
  try {
    const res = await clansApi.list()
    clans.value = res.data.results || res.data || []
  } catch {
    error.value = 'Не удалось загрузить кланы'
  } finally {
    loading.value = false
  }
}

async function loadLeaderboard() {
  leaderboardLoading.value = true
  try {
    const res = await api.get('clans/leaderboard/')
    leaderboard.value = res.data || []
  } catch {
    leaderboard.value = []
  } finally {
    leaderboardLoading.value = false
  }
}

async function openClan(clan) {
  if (!auth.requireAuth('Войди через Steam, чтобы смотреть активность клана.')) return
  selectedClan.value = clan
  dashboard.value = []
  dashboardError.value = null
  dashboardLoading.value = true
  try {
    const res = await clansApi.dashboard(clan.id)
    dashboard.value = res.data
  } catch (e) {
    dashboardError.value =
      e.response?.data?.detail || 'Дашборд доступен только участникам клана'
  } finally {
    dashboardLoading.value = false
  }
}

function openFromLeaderboard(c) {
  const full = clans.value.find((x) => x.id === c.id)
  openClan(full || c)
}

function closeDashboard() {
  selectedClan.value = null
}
function onClanCreated(newClan) {
  clans.value.unshift(newClan)
  loadLeaderboard()
}
function onJoined() {
  loadClans()
  loadLeaderboard()
}
function onDashboardUpdated() {
  if (selectedClan.value) openClan(selectedClan.value)
}
function copyInviteCode(code) {
  if (!code) return
  navigator.clipboard.writeText(code)
  toast.success('Код скопирован')
}
function triggerLogoPick() {
  logoInput.value?.click()
}

async function onLogoSelected(e) {
  const file = e.target.files?.[0]
  if (!file || !selectedClan.value) return
  if (file.size > 2 * 1024 * 1024) {
    toast.error('Максимум 2 МБ')
    e.target.value = ''
    return
  }
  logoUploading.value = true
  try {
    const fd = new FormData()
    fd.append('logo', file)
    const res = await api.post(`clans/${selectedClan.value.id}/upload_logo/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const url = res.data.logo_url || res.data.logo
    selectedClan.value = { ...selectedClan.value, logo_url: url, logo: url }
    const idx = clans.value.findIndex((c) => c.id === selectedClan.value.id)
    if (idx !== -1) {
      clans.value[idx] = { ...clans.value[idx], logo_url: url, logo: url }
    }
    toast.success('Логотип обновлён')
  } catch (err) {
    toast.error(err.response?.data?.detail || 'Не удалось загрузить логотип')
  } finally {
    logoUploading.value = false
    e.target.value = ''
  }
}

async function joinOpen(clan) {
  if (!auth.requireAuth('Войди, чтобы вступить')) return
  try {
    await clansApi.joinOpen(clan.id)
    toast.success('Ты в клане')
    await loadClans()
    loadLeaderboard()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Не удалось вступить')
  }
}

async function leaveClan(clan) {
  if (!clan) return
  if (!confirm(`Покинуть «${clan.name}»?`)) return
  try {
    await clansApi.leave(clan.id)
    toast.success('Ты вышел из клана')
    selectedClan.value = null
    await loadClans()
    loadLeaderboard()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Нельзя выйти')
  }
}

onMounted(() => {
  loadClans()
  loadLeaderboard()
})
</script>

<template>
  <div class="clans-page">
    <!-- Шапка -->
    <div class="page-header">
      <div class="title-block">
        <h1>
          <svg class="h-ico" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          Кланы
        </h1>
        <p class="subtitle">Все кланы видны всем — создавай, вступай, следи за активностью</p>
      </div>
      <div class="header-actions">
        <button type="button" class="btn-secondary" @click="openJoin">
          <svg class="btn-ico" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="7.5" cy="15.5" r="4.5" />
            <path d="m10.7 12.3 9.3-9.3M17 6l3 3M14 9l2 2" />
          </svg>
          Вступить по коду
        </button>
        <button type="button" class="btn-primary" @click="openCreate">+ Создать клан</button>
      </div>
    </div>

    <!-- Сводка -->
    <div class="stat-strip" v-if="!loading && clans.length">
      <div class="stat-tile">
        <span class="st-ico">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>
        </span>
        <div class="st-body">
          <span class="st-val">{{ stats.total }}</span>
          <span class="st-lbl">Кланов</span>
        </div>
      </div>
      <div class="stat-tile">
        <span class="st-ico">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
        </span>
        <div class="st-body">
          <span class="st-val">{{ stats.members }}</span>
          <span class="st-lbl">Игроков</span>
        </div>
      </div>
      <div class="stat-tile">
        <span class="st-ico">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
        </span>
        <div class="st-body">
          <span class="st-val">{{ stats.mine }}</span>
          <span class="st-lbl">Мои кланы</span>
        </div>
      </div>
      <div class="stat-tile">
        <span class="st-ico">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="11" width="18" height="11" rx="2" />
            <path d="M7 11V7a5 5 0 0 1 9.9-1" />
          </svg>
        </span>
        <div class="st-body">
          <span class="st-val">{{ stats.open }}</span>
          <span class="st-lbl">Открытых</span>
        </div>
      </div>
    </div>

    <!-- Панель фильтров -->
    <div class="toolbar" v-if="clans.length > 0">
      <div class="search-wrap">
        <svg class="search-ico" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <input v-model="searchQuery" class="clan-search" placeholder="Поиск клана по названию..." />
      </div>

      <div class="chips">
        <button
          v-for="f in filters"
          :key="f.id"
          type="button"
          class="filter-chip"
          :class="{ active: filter === f.id }"
          @click="filter = f.id"
        >
          {{ f.label }}
          <em>{{ f.count }}</em>
        </button>
      </div>

      <div class="toolbar-right">
        <select v-if="games.length > 1" v-model="gameFilter" class="mini-select">
          <option value="">Все игры</option>
          <option v-for="g in games" :key="g.value" :value="g.value">{{ g.label }}</option>
        </select>
        <select v-model="sortBy" class="mini-select">
          <option value="members">Сначала крупные</option>
          <option value="new">Сначала новые</option>
          <option value="name">По названию</option>
        </select>
      </div>
    </div>

    <div class="clans-layout">
      <!-- ============ Список кланов ============ -->
      <div class="clans-main">
        <div v-if="loading" class="clans-grid">
          <div v-for="n in 4" :key="n" class="clan-card card skeleton">
            <div class="sk-row">
              <span class="sk sk-avatar" />
              <span class="sk sk-line w60" />
            </div>
            <span class="sk sk-line w90" />
            <span class="sk sk-line w40" />
          </div>
        </div>

        <div v-else-if="error" class="state-message error-state">{{ error }}</div>

        <div v-else-if="clans.length === 0" class="state-message empty-state">
          <svg class="empty-ico" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          <p>Пока нет ни одного клана. Создай первый или вступи по коду.</p>
          <div class="header-actions">
            <button type="button" class="btn-secondary" @click="openJoin">Вступить по коду</button>
            <button type="button" class="btn-primary" @click="openCreate">Создать первый клан</button>
          </div>
        </div>

        <div v-else-if="filteredClans.length === 0" class="state-message empty-state">
          <svg class="empty-ico" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <p>Ничего не найдено. Попробуй изменить фильтры или запрос.</p>
          <button type="button" class="btn-secondary" @click="resetFilters">Сбросить фильтры</button>
        </div>

        <div v-else class="clans-grid">
          <div
            v-for="clan in filteredClans"
            :key="clan.id"
            class="clan-card clickable-card card"
            :class="{ mine: clan.is_member }"
            @click="openClan(clan)"
          >
            <div class="clan-card-top">
              <ClanIcon v-if="hasLogo(clan)" :clan="clan" :size="48" />
              <div v-else class="clan-avatar" :style="avatarStyle(clan.name)">
                {{ initials(clan.name) }}
              </div>

              <div class="clan-card-title-block">
                <h3>{{ clan.name }}</h3>
                <div class="title-meta">
                  <span class="my-role-badge" :class="clan.my_role" v-if="clan.my_role">
                    {{ roleLabels[clan.my_role] || clan.my_role }}
                  </span>
                  <span class="game-text">{{ clan.game_label || clan.game || '—' }}</span>
                </div>
              </div>

              <span class="members-badge" title="Участники">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                </svg>
                <template v-if="clan.max_members">{{ clan.members_count }}/{{ clan.max_members }}</template>
                <template v-else>{{ clan.members_count }}</template>
              </span>
            </div>

            <p class="clan-description">{{ clan.description || 'Без описания' }}</p>

            <div class="clan-meta">
              <span class="chip" :class="clan.is_open ? 'open' : 'closed'">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <template v-if="clan.is_open">
                    <rect x="3" y="11" width="18" height="11" rx="2" />
                    <path d="M7 11V7a5 5 0 0 1 9.9-1" />
                  </template>
                  <template v-else>
                    <rect x="3" y="11" width="18" height="11" rx="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </template>
                </svg>
                {{ clan.is_open ? 'Открытый' : 'Закрытый' }}
              </span>
              <span class="chip" v-if="clan.min_playtime_hours">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="12" cy="12" r="9" />
                  <path d="M12 7v5l3 2" />
                </svg>
                от {{ clan.min_playtime_hours }} ч.
              </span>
            </div>

            <p class="req" v-if="clan.join_requirements">
              <b>Требования:</b> {{ clan.join_requirements }}
            </p>

            <div class="capacity" v-if="capacity(clan) !== null">
              <div class="capacity-bar">
                <div
                  class="capacity-fill"
                  :class="{ full: capacity(clan) >= 100 }"
                  :style="{ width: capacity(clan) + '%' }"
                />
              </div>
              <span class="capacity-txt">{{ capacity(clan) }}% заполнен</span>
            </div>

            <div class="card-foot" @click.stop>
              <button
                v-if="clan.invite_code"
                type="button"
                class="code-btn"
                title="Скопировать код приглашения"
                @click="copyInviteCode(clan.invite_code)"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="9" y="9" width="13" height="13" rx="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
                <span class="code-val">{{ clan.invite_code }}</span>
              </button>

              <span v-else-if="clan.is_member" class="in-clan">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
                Ты в клане
              </span>

              <div class="foot-actions">
                <button
                  v-if="clan.can_join_open && !clan.is_member"
                  type="button"
                  class="btn-primary btn-sm"
                  @click="joinOpen(clan)"
                >
                  Вступить
                </button>
                <button
                  v-if="clan.is_member && clan.my_role !== 'leader'"
                  type="button"
                  class="btn-secondary btn-sm"
                  @click="leaveClan(clan)"
                >
                  Выйти
                </button>
                <button
                  v-if="!(clan.can_join_open && !clan.is_member)"
                  type="button"
                  class="btn-ghost btn-sm"
                  @click="openClan(clan)"
                >
                  Активность →
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ============ Правая колонка ============ -->
      <aside class="clans-side">
        <div class="card side-card">
          <div class="side-head">
            <h3>
              <svg class="sh-ico" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6M18 9h1.5a2.5 2.5 0 0 0 0-5H18M4 22h16" />
                <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" />
                <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
              </svg>
              Топ кланов
            </h3>
            <span class="side-caption">по активности</span>
          </div>

          <div v-if="leaderboardLoading" class="side-empty">Загрузка...</div>
          <div v-else-if="!leaderboard.length" class="side-empty">
            Пока нет активности кланов за период.
          </div>

          <div v-else class="lb-list">
            <button
              v-for="(c, i) in leaderboard"
              :key="c.id"
              type="button"
              class="lb-row"
              @click="openFromLeaderboard(c)"
            >
              <span class="rank" :class="{ gold: i === 0, silver: i === 1, bronze: i === 2 }">
                {{ i + 1 }}
              </span>
              <ClanIcon v-if="hasLogo(c)" :clan="c" :size="32" />
              <div v-else class="clan-avatar sm" :style="avatarStyle(c.name)">
                {{ initials(c.name) }}
              </div>
              <div class="lb-info">
                <span class="lb-name">{{ c.name }}</span>
                <span class="lb-sub">{{ lbSub(c) }}</span>
              </div>
            </button>
          </div>
        </div>

        <div class="card side-card promo">
          <h3>Нет своей команды?</h3>
          <p>Создай клан, пригласи друзей по коду и следи, кто сколько играет.</p>
          <div class="promo-actions">
            <button type="button" class="btn-primary btn-sm" @click="openCreate">Создать клан</button>
            <button type="button" class="btn-secondary btn-sm" @click="openJoin">Есть код</button>
          </div>
        </div>
      </aside>
    </div>

    <!-- Дашборд клана -->
    <div class="overlay" v-if="selectedClan" @click.self="closeDashboard">
      <div class="dashboard-modal card">
        <div class="modal-header">
          <div class="modal-header-title">
            <div class="logo-wrap">
              <ClanIcon v-if="hasLogo(selectedClan)" :clan="selectedClan" :size="44" />
              <div v-else class="clan-avatar" :style="avatarStyle(selectedClan.name)">
                {{ initials(selectedClan.name) }}
              </div>
              <template v-if="isLeader(selectedClan)">
                <input
                  ref="logoInput"
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  class="logo-file-input"
                  @change="onLogoSelected"
                />
                <button
                  type="button"
                  class="logo-edit-btn"
                  :disabled="logoUploading"
                  title="Сменить аватар"
                  @click="triggerLogoPick"
                >
                  {{ logoUploading ? '…' : '✎' }}
                </button>
              </template>
            </div>
            <div class="modal-title-col">
              <h2>{{ selectedClan.name }} — активность</h2>
              <div class="clan-meta">
                <span class="chip" :class="selectedClan.is_open ? 'open' : 'closed'">
                  {{ selectedClan.is_open ? 'Открытый' : 'Закрытый' }}
                </span>
                <span class="chip game">{{ selectedClan.game_label || selectedClan.game }}</span>
                <span class="chip" v-if="selectedClan.min_playtime_hours">
                  от {{ selectedClan.min_playtime_hours }} ч.
                </span>
              </div>
            </div>
          </div>
          <div class="modal-header-right">
            <button
              v-if="selectedClan.is_member && selectedClan.my_role !== 'leader'"
              type="button"
              class="btn-secondary btn-sm"
              @click="leaveClan(selectedClan)"
            >
              Выйти из клана
            </button>
            <button type="button" class="close-btn" @click="closeDashboard">✕</button>
          </div>
        </div>

        <p class="req modal-req" v-if="selectedClan.join_requirements">
          <b>Требования:</b> {{ selectedClan.join_requirements }}
        </p>

        <button
          type="button"
          class="code-btn modal-invite"
          v-if="selectedClan.invite_code"
          @click="copyInviteCode(selectedClan.invite_code)"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="9" y="9" width="13" height="13" rx="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
          Код приглашения:
          <span class="code-val">{{ selectedClan.invite_code }}</span>
        </button>

        <div v-if="dashboardLoading" class="state-message">Считаем активность...</div>
        <div v-else-if="dashboardError" class="state-message error-state">{{ dashboardError }}</div>
        <ClanDashboardTable
          v-else
          :entries="dashboard"
          :clan-id="selectedClan.id"
          :is-leader="isLeader(selectedClan)"
          @updated="onDashboardUpdated"
        />
      </div>
    </div>

    <CreateClanModal v-if="showCreateModal" @close="showCreateModal = false" @created="onClanCreated" />
    <JoinClanModal v-if="showJoinModal" @close="showJoinModal = false" @joined="onJoined" />
  </div>
</template>

<style scoped>
.clans-page { display: flex; flex-direction: column; gap: 16px; width: 100%; }

/* —— Шапка —— */
.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 12px; flex-wrap: wrap;
}
.page-header h1 {
  margin: 0 0 4px; font-size: 22px; font-weight: 700;
  display: flex; align-items: center; gap: 10px;
}
.h-ico {
  width: 24px; height: 24px; fill: none; stroke: var(--accent);
  stroke-width: 1.9; stroke-linecap: round; stroke-linejoin: round;
}
.subtitle { margin: 0; color: var(--text-secondary); font-size: 13px; }
.header-actions { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.btn-ico {
  width: 15px; height: 15px; fill: none; stroke: currentColor; stroke-width: 1.9;
  stroke-linecap: round; stroke-linejoin: round; margin-right: 6px; vertical-align: -3px;
}

/* —— Сводка —— */
.stat-strip {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;
}
.stat-tile {
  display: flex; align-items: center; gap: 12px; padding: 12px 14px;
  background: var(--bg-card); border: 1px solid var(--border-color);
  border-radius: 12px; position: relative; overflow: hidden;
}
.stat-tile::after {
  content: ''; position: absolute; left: 14px; right: 14px; bottom: 0; height: 2px;
  background: linear-gradient(90deg, var(--accent), transparent); opacity: 0.6; border-radius: 2px;
}
.st-ico {
  width: 36px; height: 36px; flex-shrink: 0; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: var(--accent-dim);
  border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent);
}
.st-ico svg {
  width: 17px; height: 17px; fill: none; stroke: var(--accent);
  stroke-width: 1.9; stroke-linecap: round; stroke-linejoin: round;
}
.st-body { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.st-val { font-size: 20px; font-weight: 800; font-family: var(--font-mono); line-height: 1.1; }
.st-lbl {
  font-size: 10px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--text-muted);
}

/* —— Панель фильтров —— */
.toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.search-wrap { position: relative; flex: 1; min-width: 200px; max-width: 320px; }
.search-ico {
  position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
  width: 15px; height: 15px; fill: none; stroke: var(--text-muted);
  stroke-width: 2; stroke-linecap: round; pointer-events: none;
}
.clan-search {
  background: var(--bg-sunken); border: 1px solid var(--border-color);
  border-radius: var(--radius-sm); padding: 9px 12px 9px 34px; color: var(--text-primary);
  font-size: 13px; width: 100%; box-sizing: border-box;
}
.clan-search:focus { outline: none; border-color: var(--accent); }
.chips { display: flex; gap: 6px; flex-wrap: wrap; }
.filter-chip {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-sunken); border: 1px solid transparent; color: var(--text-secondary);
  font-size: 12px; font-weight: 600; padding: 7px 12px; border-radius: var(--radius-sm); cursor: pointer;
}
.filter-chip em {
  font-style: normal; font-size: 10px; font-family: var(--font-mono);
  color: var(--text-muted);
}
.filter-chip:hover { color: var(--text-primary); }
.filter-chip.active {
  background: var(--accent-dim); color: var(--accent); border-color: var(--accent);
}
.filter-chip.active em { color: var(--accent); }
.toolbar-right { margin-left: auto; display: flex; gap: 8px; }
.mini-select {
  background: var(--bg-sunken); border: 1px solid var(--border-color);
  border-radius: var(--radius-sm); color: var(--text-secondary);
  font-size: 12px; padding: 7px 10px; cursor: pointer;
}

/* —— Раскладка —— */
.clans-layout {
  display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 16px; align-items: start;
}
.clans-main { min-width: 0; }
.clans-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px;
}

/* —— Карточка клана —— */
.clan-card {
  display: flex; flex-direction: column; gap: 10px; position: relative; overflow: hidden;
  transition: border-color 0.15s, transform 0.15s, box-shadow 0.15s;
  cursor: pointer;
}
.clan-card:hover {
  border-color: var(--accent); transform: translateY(-2px);
  box-shadow: 0 10px 28px -16px var(--glow);
}
.clan-card.mine { border-color: color-mix(in srgb, var(--accent) 45%, var(--border-color)); }
.clan-card.mine::before {
  content: ''; position: absolute; left: 0; right: 0; top: 0; height: 2px;
  background: linear-gradient(90deg, var(--accent), transparent);
}
.clan-card-top { display: flex; align-items: center; gap: 12px; }
.clan-avatar {
  width: 48px; height: 48px; flex-shrink: 0; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 800; color: #fff; letter-spacing: 0.02em;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14);
}
.clan-avatar.sm { width: 32px; height: 32px; border-radius: 8px; font-size: 11px; }
.clan-card-title-block { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.clan-card-title-block h3 {
  margin: 0; font-size: 15px; font-weight: 700;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.title-meta { display: flex; align-items: center; gap: 8px; min-width: 0; }
.game-text {
  font-size: 11px; color: var(--accent); font-weight: 600;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.my-role-badge {
  font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: var(--radius-sm);
  text-transform: uppercase; letter-spacing: 0.04em; flex-shrink: 0;
}
.my-role-badge.leader { background: var(--accent-dim); color: var(--accent); }
.my-role-badge.officer { background: rgba(74, 222, 128, 0.12); color: var(--success); }
.my-role-badge.member { background: var(--bg-card-hover); color: var(--text-secondary); }
.members-badge {
  display: inline-flex; align-items: center; gap: 5px; align-self: flex-start;
  font-size: 12px; font-weight: 700; color: var(--text-secondary);
  background: var(--bg-sunken); padding: 4px 9px; border-radius: 999px;
  font-family: var(--font-mono);
}
.members-badge svg {
  width: 12px; height: 12px; fill: none; stroke: currentColor;
  stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
}
.clan-description {
  font-size: 13px; color: var(--text-secondary); margin: 0; line-height: 1.45;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  min-height: 38px;
}
.clan-meta { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 10px; font-weight: 700; padding: 3px 9px; border-radius: 999px;
  background: var(--bg-sunken); color: var(--text-secondary);
}
.chip svg {
  width: 11px; height: 11px; fill: none; stroke: currentColor;
  stroke-width: 2.2; stroke-linecap: round; stroke-linejoin: round;
}
.chip.open { color: var(--success); background: rgba(74, 222, 128, 0.12); }
.chip.closed { color: var(--warning, #e0a63c); background: rgba(224, 166, 60, 0.12); }
.chip.game { color: var(--accent); background: var(--accent-dim); }
.req {
  margin: 0; font-size: 12px; color: var(--text-secondary); line-height: 1.4;
  padding: 8px 10px; background: var(--bg-sunken); border-left: 2px solid var(--accent);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.req b { color: var(--text-primary); font-weight: 600; }

.capacity { display: flex; align-items: center; gap: 10px; }
.capacity-bar { flex: 1; height: 4px; background: var(--bg-sunken); border-radius: 2px; overflow: hidden; }
.capacity-fill { height: 100%; background: var(--accent); border-radius: 2px; transition: width 0.4s; }
.capacity-fill.full { background: var(--danger); }
.capacity-txt { font-size: 10px; color: var(--text-muted); white-space: nowrap; font-family: var(--font-mono); }

.card-foot {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  margin-top: auto; padding-top: 10px; border-top: 1px solid var(--border-color); flex-wrap: wrap;
}
.foot-actions { display: flex; gap: 6px; margin-left: auto; }
.btn-sm { padding: 7px 12px; font-size: 12px; }
.code-btn {
  display: inline-flex; align-items: center; gap: 7px; padding: 6px 10px;
  background: var(--bg-sunken); border: 1px dashed var(--border-color);
  border-radius: var(--radius-sm); color: var(--text-secondary); font-size: 12px; cursor: pointer;
}
.code-btn:hover { border-color: var(--accent); color: var(--accent); }
.code-btn svg {
  width: 13px; height: 13px; fill: none; stroke: currentColor;
  stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
}
.code-val { font-family: var(--font-mono); font-weight: 700; color: var(--accent); }
.in-clan {
  display: inline-flex; align-items: center; gap: 6px; font-size: 12px;
  font-weight: 600; color: var(--accent);
}
.in-clan svg {
  width: 14px; height: 14px; fill: none; stroke: currentColor;
  stroke-width: 2.6; stroke-linecap: round; stroke-linejoin: round;
}

/* —— Скелетоны —— */
.skeleton { cursor: default; pointer-events: none; }
.sk-row { display: flex; align-items: center; gap: 12px; }
.sk {
  display: block; background: linear-gradient(90deg, var(--bg-sunken), var(--bg-card-hover), var(--bg-sunken));
  background-size: 200% 100%; animation: sk 1.3s linear infinite; border-radius: 6px;
}
.sk-avatar { width: 48px; height: 48px; border-radius: 12px; }
.sk-line { height: 12px; }
.w90 { width: 90%; } .w60 { width: 60%; } .w40 { width: 40%; }
@keyframes sk { to { background-position: -200% 0; } }

/* —— Правая колонка —— */
.clans-side { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.side-card { display: flex; flex-direction: column; gap: 10px; }
.side-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.side-head h3, .promo h3 {
  margin: 0; display: flex; align-items: center; gap: 10px; font-size: 12px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary);
}
.sh-ico {
  width: 18px; height: 18px; fill: none; stroke: var(--accent);
  stroke-width: 1.9; stroke-linecap: round; stroke-linejoin: round;
}
.side-caption { font-size: 11px; color: var(--text-muted); }
.side-empty { padding: 14px 6px; font-size: 13px; color: var(--text-secondary); text-align: center; }
.lb-list { display: flex; flex-direction: column; gap: 2px; }
.lb-row {
  display: flex; align-items: center; gap: 10px; padding: 7px 6px; width: 100%;
  background: none; border: none; border-radius: var(--radius-sm);
  cursor: pointer; color: inherit; text-align: left;
}
.lb-row:hover { background: var(--bg-card-hover); }
.lb-info { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.lb-name { font-size: 13px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lb-sub { font-size: 11px; color: var(--text-secondary); }
.rank {
  width: 22px; text-align: center; font-weight: 700; font-size: 12px;
  color: var(--text-secondary); font-family: var(--font-mono); flex-shrink: 0;
}
.rank.gold { color: #c4a574; }
.rank.silver { color: #a8aeb8; }
.rank.bronze { color: #a67c52; }

.promo {
  background:
    radial-gradient(ellipse 80% 120% at 100% 0%, rgba(230, 57, 70, 0.22), transparent 60%),
    var(--bg-card);
}
.promo p { margin: 0; font-size: 13px; color: var(--text-secondary); line-height: 1.5; }
.promo-actions { display: flex; gap: 8px; flex-wrap: wrap; }

/* —— Состояния —— */
.state-message {
  padding: 48px 20px; text-align: center; color: var(--text-secondary);
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md);
}
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 14px; }
.empty-state p { margin: 0; }
.empty-ico {
  width: 40px; height: 40px; fill: none; stroke: var(--text-muted);
  stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round;
}
.error-state { color: var(--danger); }

/* —— Модалка дашборда —— */
.overlay {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.7);
  display: flex; align-items: center; justify-content: center; z-index: 100; padding: 16px;
}
.dashboard-modal { width: 820px; max-width: 92vw; max-height: 80vh; overflow-y: auto; }
.modal-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 12px; margin-bottom: 16px;
}
.modal-header-title { display: flex; align-items: center; gap: 14px; min-width: 0; }
.modal-title-col { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.modal-header h2 { margin: 0; font-size: 16px; font-weight: 600; }
.modal-header-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.close-btn { background: none; border: none; color: var(--text-secondary); font-size: 16px; cursor: pointer; }
.modal-req { margin-bottom: 12px; }
.modal-invite { margin-bottom: 14px; }
.logo-wrap { position: relative; display: inline-flex; flex-shrink: 0; }
.logo-file-input { display: none; }
.logo-edit-btn {
  position: absolute; right: -6px; bottom: -6px; width: 22px; height: 22px;
  border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-card);
  cursor: pointer; font-size: 11px; display: flex; align-items: center; justify-content: center;
  color: var(--text-secondary);
}
.logo-edit-btn:hover { border-color: var(--accent); color: var(--accent); }

@media (max-width: 1100px) {
  .clans-layout { grid-template-columns: 1fr; }
}
@media (max-width: 900px) {
  .clans-grid { grid-template-columns: 1fr; }
  .dashboard-modal { width: 100%; max-height: 90vh; }
  .toolbar-right { margin-left: 0; }
}
</style>