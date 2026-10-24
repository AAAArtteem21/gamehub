<script setup>
import { ref, watch, onMounted, onUnmounted, computed, inject } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import IconSearch from '../icons/IconSearch.vue'
import api from '../../api/axios'
import { useTheme } from '../../composables/useTheme'
import logo from '../../assets/images/logo.png'
import FriendsButton from '../components/friends/FriendsButton.vue'
const authStore = useAuthStore()
const router = useRouter()
const toggleSidebar = inject('toggleSidebar', () => {})

const { theme, themes, setTheme } = useTheme()
const themeOpen = ref(false)
const themeRef = ref(null)

const menuOpen = ref(false)
const menuRef = ref(null)
const notifOpen = ref(false)
const notifRef = ref(null)

const searchQuery = ref('')
const suggestions = ref([])
const suggestOpen = ref(false)
let searchTimer = null
let notifTimer = null

const notifications = ref([])
const unread = computed(() => notifications.value.filter((n) => !n.read).length)

async function loadNotifications() {
  try {
    const res = await api.get('notifications/')
    notifications.value = res.data || []
  } catch {
    notifications.value = []
  }
}

async function markRead(ids = null) {
  try {
    await api.post('notifications/read/', ids ? { ids } : {})
    if (ids) {
      notifications.value = notifications.value.map((n) =>
        ids.includes(n.id) ? { ...n, read: true } : n
      )
    } else {
      notifications.value = notifications.value.map((n) => ({ ...n, read: true }))
    }
  } catch {
    /* */
  }
}

async function openNotifItem(n) {
  notifOpen.value = false
  if (!n.read) await markRead([n.id])
  if (n.link) router.push(n.link)
}

function toggleNotif() {
  notifOpen.value = !notifOpen.value
  menuOpen.value = false
  themeOpen.value = false
  if (notifOpen.value) loadNotifications()
}

function toggleMenu() {
  menuOpen.value = !menuOpen.value
  notifOpen.value = false
  themeOpen.value = false
}

function toggleThemeMenu() {
  themeOpen.value = !themeOpen.value
  menuOpen.value = false
  notifOpen.value = false
}

function pickTheme(id) {
  setTheme(id)
  themeOpen.value = false
}

async function handleLogout() {
  try {
    await api.post('logout/')
  } catch {
    /* */
  }
  authStore.logout()
  menuOpen.value = false
  router.push('/')
}

function handleClickOutside(e) {
  if (menuRef.value && !menuRef.value.contains(e.target)) menuOpen.value = false
  if (notifRef.value && !notifRef.value.contains(e.target)) notifOpen.value = false
  if (themeRef.value && !themeRef.value.contains(e.target)) themeOpen.value = false
}

function handleSearch() {
  if (suggestions.value.length) {
    pickPlayer(suggestions.value[0])
    return
  }
  if (!searchQuery.value.trim()) return
  router.push({ path: '/lfg', query: { search: searchQuery.value.trim() } })
}

watch(searchQuery, (val) => {
  clearTimeout(searchTimer)
  const q = val.trim()
  if (q.length < 1) {
    suggestions.value = []
    suggestOpen.value = false
    return
  }
  searchTimer = setTimeout(async () => {
    try {
      const res = await api.get('players/search/', { params: { q } })
      suggestions.value = res.data || []
      suggestOpen.value = suggestions.value.length > 0
    } catch {
      suggestions.value = []
      suggestOpen.value = false
    }
  }, 200)
})

function pickPlayer(u) {
  searchQuery.value = u.display_name || u.username
  suggestOpen.value = false
  router.push(`/players/${u.id}`)
}

function onSearchBlur() {
  setTimeout(() => {
    suggestOpen.value = false
  }, 150)
}

function timeAgo(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const sec = Math.floor((Date.now() - d.getTime()) / 1000)
  if (sec < 60) return 'только что'
  if (sec < 3600) return `${Math.floor(sec / 60)} мин`
  if (sec < 86400) return `${Math.floor(sec / 3600)} ч`
  return `${Math.floor(sec / 86400)} д`
}

function startNotifications() {
  loadNotifications()
  clearInterval(notifTimer)
  notifTimer = setInterval(loadNotifications, 60000)
}

function stopNotifications() {
  clearInterval(notifTimer)
  notifications.value = []
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  if (authStore.isAuthenticated) startNotifications()
})

watch(
  () => authStore.isAuthenticated,
  (v) => (v ? startNotifications() : stopNotifications())
)

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  clearTimeout(searchTimer)
  if (notifTimer) clearInterval(notifTimer)
})
</script>

<template>
  <header class="topbar">
    <button type="button" class="burger" aria-label="Меню" @click.stop="toggleSidebar()">
      <span /><span /><span />
    </button>

    <RouterLink to="/" class="brand">
      <img :src="logo" alt="GameEyes" class="brand-mark" />
      <div class="brand-text">
        <span class="brand-name">GAME<span class="accent-text">EYES</span></span>
        <span class="brand-tag">find · play · win</span>
      </div>
    </RouterLink>

    <form class="search" @submit.prevent="handleSearch">
      <span class="search-icon"><IconSearch /></span>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Найти игроков, кланы, заявки..."
        autocomplete="off"
        @focus="suggestOpen = suggestions.length > 0"
        @blur="onSearchBlur"
      />
      <div v-if="suggestOpen" class="suggest-box">
        <button
          v-for="u in suggestions"
          :key="u.id"
          type="button"
          class="suggest-item"
          @mousedown.prevent="pickPlayer(u)"
        >
          <div
            class="suggest-av"
            :style="u.avatar_url ? { backgroundImage: `url(${u.avatar_url})` } : {}"
          >
            <span v-if="!u.avatar_url">
              {{ (u.display_name || u.username || '?')[0]?.toUpperCase() }}
            </span>
          </div>
          <div class="suggest-text">
            <span class="suggest-name">{{ u.display_name }}</span>
            <span class="suggest-user">@{{ u.username }}</span>
          </div>
        </button>
      </div>
    </form>

    <div class="top-right">
      <!-- Смена темы -->
      <div class="theme-wrap" ref="themeRef">
        <button
          type="button"
          class="icon-pill"
          :class="{ active: themeOpen }"
          title="Тема оформления"
          aria-label="Тема оформления"
          @click.stop="toggleThemeMenu"
        >
          <svg class="pill-ico" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="13.5" cy="6.5" r="1" />
            <circle cx="17.5" cy="10.5" r="1" />
            <circle cx="8.5" cy="7.5" r="1" />
            <circle cx="6.5" cy="12.5" r="1" />
            <path
              d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.93 0 1.5-.75 1.5-1.5 0-.39-.15-.74-.39-1.01-.23-.26-.38-.61-.38-.99 0-.83.67-1.5 1.5-1.5H16c3.31 0 6-2.69 6-6 0-4.96-4.48-9-10-9z"
            />
          </svg>
        </button>
        <transition name="menu-fade">
          <div class="theme-menu" v-if="themeOpen">
            <div class="menu-title">Тема оформления</div>
            <button
              v-for="t in themes"
              :key="t.id"
              type="button"
              class="theme-item"
              :class="{ active: theme === t.id }"
              @click="pickTheme(t.id)"
            >
              <span class="theme-dot" :data-t="t.id" />
              <span class="theme-meta">
                <b>{{ t.label }}</b>
                <small>{{ t.hint }}</small>
              </span>
              <svg v-if="theme === t.id" class="theme-check" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M20 6 9 17l-5-5" />
              </svg>
            </button>
          </div>
        </transition>
      </div>

      <template v-if="authStore.isAuthenticated">
        <!-- Друзья -->
        <FriendsButton />

        <!-- Уведомления -->
        <div class="notif-wrap" ref="notifRef">
          <button
            type="button"
            class="icon-pill"
            :class="{ active: notifOpen, ring: unread > 0 }"
            title="Уведомления"
            aria-label="Уведомления"
            @click.stop="toggleNotif"
          >
            <svg class="pill-ico bell" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
              <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
            </svg>
            <span v-if="unread" class="bell-badge">{{ unread > 9 ? '9+' : unread }}</span>
          </button>

          <transition name="menu-fade">
            <div class="notif-panel" v-if="notifOpen">
              <div class="notif-head">
                <span class="notif-title">
                  Уведомления
                  <em v-if="unread" class="notif-count">{{ unread }}</em>
                </span>
                <button v-if="unread" type="button" class="mark-all" @click="markRead()">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M18 7 9.5 17 6 13.5" />
                    <path d="m22 7-8.5 10" />
                  </svg>
                  Прочитать все
                </button>
              </div>
              <div class="notif-list">
                <button
                  v-for="n in notifications"
                  :key="n.id"
                  type="button"
                  class="notif-item"
                  :class="{ unread: !n.read }"
                  @click="openNotifItem(n)"
                >
                  <span class="notif-dot" />
                  <div class="notif-body">
                    <b>{{ n.title }}</b>
                    <span v-if="n.body">{{ n.body }}</span>
                  </div>
                  <span class="notif-time">{{ timeAgo(n.created_at) }}</span>
                </button>
                <div v-if="!notifications.length" class="notif-empty">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
                    <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
                  </svg>
                  Пока тихо
                </div>
              </div>
            </div>
          </transition>
        </div>

        <!-- Пользователь -->
        <div class="user-block" ref="menuRef">
          <button type="button" class="user-trigger" :class="{ active: menuOpen }" @click.stop="toggleMenu">
            <div
              class="avatar"
              :style="
                authStore.user?.avatar_url
                  ? { backgroundImage: `url(${authStore.user.avatar_url})` }
                  : {}
              "
            >
              <span v-if="!authStore.user?.avatar_url" class="avatar-fallback">
                {{
                  (authStore.user?.display_name || authStore.user?.username || '?')[0]?.toUpperCase()
                }}
              </span>
            </div>
            <span class="username">
              {{ authStore.user?.display_name || authStore.user?.username || '...' }}
            </span>
            <svg class="chevron" :class="{ open: menuOpen }" viewBox="0 0 24 24" aria-hidden="true">
              <path d="m6 9 6 6 6-6" />
            </svg>
          </button>

          <transition name="menu-fade">
            <div class="dropdown" v-if="menuOpen">
              <RouterLink to="/profile" class="dropdown-item" @click="menuOpen = false">
                <svg class="dd-ico" viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="12" cy="8" r="4" />
                  <path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1" />
                </svg>
                Мой профиль
              </RouterLink>
              <div class="dropdown-divider"></div>
              <button type="button" class="dropdown-item danger" @click="handleLogout">
                <svg class="dd-ico" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <path d="m16 17 5-5-5-5" />
                  <path d="M21 12H9" />
                </svg>
                Выйти
              </button>
            </div>
          </transition>
        </div>
      </template>

      <button v-else type="button" class="login-btn" @click="authStore.loginWithSteam()">
        Войти через Steam
      </button>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--topbar-h);
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 20px;
  background: color-mix(in srgb, var(--bg-sunken) 88%, transparent);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--panel-border);
  box-shadow: 0 6px 24px -14px var(--glow);
  z-index: 60;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  width: calc(var(--sidebar-w) - 24px);
  text-decoration: none;
  flex-shrink: 0;
}
.brand-mark {
  width: 40px;
  height: 40px;
  object-fit: contain;
  flex-shrink: 0;
  filter: drop-shadow(0 0 8px var(--glow));
}
.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
  min-width: 0;
}
.brand-name {
  font-weight: 800;
  letter-spacing: 0.05em;
  font-size: 18px;
  color: var(--text-primary);
}
.accent-text {
  color: var(--accent);
}
.brand-tag {
  font-size: 9px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--accent);
  font-weight: 700;
}

.burger {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 38px;
  height: 38px;
  padding: 9px;
  background: var(--bg-card);
  border: 1px solid var(--panel-border);
  border-radius: 10px;
  cursor: pointer;
  flex-shrink: 0;
}
.burger span {
  display: block;
  height: 2px;
  width: 100%;
  background: var(--text-primary);
  border-radius: 1px;
}

/* —— Поиск —— */
.search {
  position: relative;
  display: flex;
  align-items: center;
  flex: 1;
  max-width: 460px;
}
.search-icon {
  position: absolute;
  left: 14px;
  color: var(--accent);
  pointer-events: none;
  z-index: 1;
  display: flex;
}
.search-icon svg {
  width: 16px;
  height: 16px;
}
.search input {
  width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--panel-border);
  border-radius: 999px;
  padding: 10px 16px 10px 40px;
  color: var(--text-primary);
  font-size: 13px;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.search input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-dim);
}

.suggest-box {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  z-index: 70;
  background: var(--bg-card);
  border: 1px solid var(--panel-border);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: var(--shadow-md);
}
.suggest-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  background: none;
  border: none;
  cursor: pointer;
  color: inherit;
  text-align: left;
}
.suggest-item:hover {
  background: var(--bg-card-hover);
}
.suggest-av {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  flex-shrink: 0;
  background-color: var(--accent-dim);
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
}
.suggest-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.suggest-name {
  font-size: 13px;
  font-weight: 600;
}
.suggest-user {
  font-size: 11px;
  color: var(--text-secondary);
}

/* —— Правая часть —— */
.top-right {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
  flex-shrink: 0;
}

.icon-pill {
  position: relative;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  border: 1px solid var(--panel-border);
  background: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.15s, border-color 0.15s, box-shadow 0.15s, background 0.15s;
}
.icon-pill:hover,
.icon-pill.active {
  border-color: var(--accent);
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, var(--bg-card));
  box-shadow: 0 0 16px var(--glow-soft);
}
.pill-ico {
  width: 19px;
  height: 19px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
/* точки палитры — залитые */
.pill-ico circle {
  fill: currentColor;
  stroke: none;
}

/* лёгкое покачивание колокольчика при непрочитанных */
.icon-pill.ring .bell {
  transform-origin: 50% 3px;
  animation: bell-ring 4s ease-in-out infinite;
}
@keyframes bell-ring {
  0%, 88%, 100% { transform: rotate(0); }
  90% { transform: rotate(14deg); }
  93% { transform: rotate(-12deg); }
  96% { transform: rotate(8deg); }
  98% { transform: rotate(-4deg); }
}
@media (prefers-reduced-motion: reduce) {
  .icon-pill.ring .bell { animation: none; }
}

.bell-badge {
  position: absolute;
  top: -5px;
  right: -5px;
  min-width: 17px;
  height: 17px;
  padding: 0 4px;
  border-radius: 999px;
  background: var(--accent);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 0 2px var(--bg-primary), 0 0 10px var(--glow);
}

.theme-wrap,
.notif-wrap,
.user-block {
  position: relative;
}

/* —— Меню темы —— */
.menu-title {
  padding: 6px 10px 8px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}
.theme-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  min-width: 230px;
  background: var(--bg-card);
  border: 1px solid var(--panel-border);
  border-radius: 14px;
  box-shadow: var(--shadow-md);
  padding: 6px;
  z-index: 70;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.theme-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: none;
  background: none;
  color: var(--text-primary);
  border-radius: 10px;
  cursor: pointer;
  text-align: left;
  width: 100%;
}
.theme-item:hover {
  background: var(--bg-card-hover);
}
.theme-item.active {
  background: var(--accent-dim);
}
.theme-meta {
  display: flex;
  flex-direction: column;
  gap: 1px;
  flex: 1;
  min-width: 0;
}
.theme-meta b {
  font-size: 13px;
  font-weight: 600;
}
.theme-meta small {
  font-size: 11px;
  color: var(--text-muted);
}
.theme-check {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: var(--accent);
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
  flex-shrink: 0;
}
.theme-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 2px solid var(--border-color);
}
.theme-dot[data-t='crimson'] { background: #e63946; }
.theme-dot[data-t='slate'] { background: #d97b3f; }
.theme-dot[data-t='mono'] { background: #ff2d2d; box-shadow: inset 0 0 0 3px #111; }
.theme-dot[data-t='ivory'] { background: #f2f2f2; box-shadow: inset 0 0 0 2px #111; }

/* —— Уведомления —— */
.notif-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: min(360px, 92vw);
  max-height: 440px;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--panel-border);
  border-radius: 14px;
  box-shadow: var(--shadow-md);
  overflow: hidden;
  z-index: 70;
}
.notif-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-color);
}
.notif-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
}
.notif-count {
  font-style: normal;
  font-size: 10px;
  font-weight: 700;
  color: var(--accent);
  background: var(--accent-dim);
  padding: 2px 7px;
  border-radius: 999px;
}
.mark-all {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: none;
  background: none;
  color: var(--accent);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}
.mark-all svg {
  width: 14px;
  height: 14px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.notif-list {
  overflow-y: auto;
  max-height: 380px;
}
.notif-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  padding: 12px 14px;
  border: none;
  border-bottom: 1px solid var(--border-color);
  background: none;
  color: inherit;
  text-align: left;
  cursor: pointer;
}
.notif-item:last-child { border-bottom: none; }
.notif-item:hover { background: var(--bg-card-hover); }
.notif-item.unread { background: color-mix(in srgb, var(--accent) 7%, transparent); }
.notif-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
  background: transparent;
}
.notif-item.unread .notif-dot {
  background: var(--accent);
  box-shadow: 0 0 8px var(--glow);
}
.notif-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.notif-body b { font-size: 13px; font-weight: 600; }
.notif-body span { font-size: 12px; color: var(--text-secondary); line-height: 1.35; }
.notif-time { font-size: 10px; color: var(--text-muted); flex-shrink: 0; white-space: nowrap; margin-top: 2px; }
.notif-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 32px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--text-muted);
}
.notif-empty svg {
  width: 32px;
  height: 32px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.7;
}

/* —— Пользователь —— */
.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 40px;
  background: var(--bg-card);
  border: 1px solid var(--panel-border);
  cursor: pointer;
  padding: 4px 10px 4px 4px;
  border-radius: 12px;
  color: var(--text-primary);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.user-trigger:hover,
.user-trigger.active {
  border-color: var(--accent);
  box-shadow: 0 0 16px var(--glow-soft);
}
.avatar {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background-color: var(--accent-dim);
  background-size: cover;
  background-position: center;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.avatar-fallback { font-weight: 700; font-size: 13px; color: var(--accent); }
.username {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chevron {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: var(--text-secondary);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: transform 0.15s;
}
.chevron.open { transform: rotate(180deg); }

.dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 190px;
  background: var(--bg-card);
  border: 1px solid var(--panel-border);
  border-radius: 14px;
  box-shadow: var(--shadow-md);
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  z-index: 70;
}
.dropdown-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 10px;
  color: var(--text-primary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  background: none;
  border: none;
  cursor: pointer;
  width: 100%;
  text-align: left;
}
.dropdown-item:hover { background: var(--bg-card-hover); }
.dropdown-item.danger:hover { background: rgba(230, 57, 70, 0.12); color: var(--danger); }
.dropdown-item.danger:hover .dd-ico { stroke: var(--danger); }
.dd-ico {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  fill: none;
  stroke: var(--text-secondary);
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.dropdown-divider { height: 1px; background: var(--border-color); margin: 4px 2px; }

.login-btn {
  background: #1b2838;
  color: #fff;
  border: 1px solid #2a3f5a;
  padding: 10px 16px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.login-btn:hover {
  border-color: #3d5a80;
  box-shadow: 0 0 14px rgba(61, 90, 128, 0.4);
}

.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 0.15s var(--ease), transform 0.15s var(--ease);
}
.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (max-width: 900px) {
  .burger { display: flex; }
  .topbar { padding: 0 12px; gap: 10px; }
  .brand { width: auto; }
  .brand-text { display: none; }
  .search { max-width: none; }
  .username,
  .chevron { display: none; }
  .user-trigger { padding: 4px; }
}

@media (max-width: 480px) {
  .search input { font-size: 12px; padding-left: 36px; }
  .login-btn { padding: 8px 10px; font-size: 11px; }
  .icon-pill { width: 36px; height: 36px; }
}
</style>