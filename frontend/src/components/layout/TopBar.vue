<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import IconSearch from '../icons/IconSearch.vue'
import api from '../../api/axios'

const authStore = useAuthStore()
const router = useRouter()

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
  } catch { /* */ }
}

async function openNotifItem(n) {
  notifOpen.value = false
  if (!n.read) await markRead([n.id])
  if (n.link) router.push(n.link)
}

function toggleNotif() {
  notifOpen.value = !notifOpen.value
  menuOpen.value = false
  if (notifOpen.value) loadNotifications()
}

function toggleMenu() {
  menuOpen.value = !menuOpen.value
  notifOpen.value = false
}

async function handleLogout() {
  try { await api.post('logout/') } catch { /* */ }
  authStore.logout()
  menuOpen.value = false
  router.push('/')
}

function handleClickOutside(e) {
  if (menuRef.value && !menuRef.value.contains(e.target)) menuOpen.value = false
  if (notifRef.value && !notifRef.value.contains(e.target)) notifOpen.value = false
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
  setTimeout(() => { suggestOpen.value = false }, 150)
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

watch(() => authStore.isAuthenticated, (v) => (v ? startNotifications() : stopNotifications()))

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  clearTimeout(searchTimer)
  if (notifTimer) clearInterval(notifTimer)
})
</script>

<template>
  <header class="topbar">
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
            <span v-if="!u.avatar_url">{{ (u.display_name || u.username || '?')[0]?.toUpperCase() }}</span>
          </div>
          <div class="suggest-text">
            <span class="suggest-name">{{ u.display_name }}</span>
            <span class="suggest-user">@{{ u.username }}</span>
          </div>
        </button>
      </div>
    </form>

    <div class="top-right">
      <template v-if="authStore.isAuthenticated">
        <div class="notif-wrap" ref="notifRef">
        <button type="button" class="bell-btn" @click.stop="toggleNotif" title="Уведомления">
          <span class="bell-icon">🔔</span>
          <span v-if="unread" class="bell-badge">{{ unread > 9 ? '9+' : unread }}</span>
        </button>

        <transition name="menu-fade">
          <div class="notif-panel" v-if="notifOpen">
            <div class="notif-head">
              <span>Уведомления</span>
              <button v-if="unread" type="button" class="mark-all" @click="markRead()">
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
                <div class="notif-body">
                  <b>{{ n.title }}</b>
                  <span v-if="n.body">{{ n.body }}</span>
                </div>
                <span class="notif-time">{{ timeAgo(n.created_at) }}</span>
              </button>
              <div v-if="!notifications.length" class="notif-empty">Пока тихо</div>
            </div>
          </div>
        </transition>
      </div>

      <div class="user-block" ref="menuRef">
        <button type="button" class="user-trigger" @click.stop="toggleMenu">
          <div
            class="avatar"
            :style="authStore.user?.avatar_url ? { backgroundImage: `url(${authStore.user.avatar_url})` } : {}"
          >
            <span v-if="!authStore.user?.avatar_url" class="avatar-fallback">
              {{ (authStore.user?.display_name || authStore.user?.username || '?')[0]?.toUpperCase() }}
            </span>
          </div>
          <span class="username">{{ authStore.user?.display_name || authStore.user?.username || '...' }}</span>
          <span class="chevron" :class="{ open: menuOpen }">⌄</span>
        </button>

        <transition name="menu-fade">
          <div class="dropdown" v-if="menuOpen">
            <RouterLink to="/profile" class="dropdown-item" @click="menuOpen = false">
              <span class="dropdown-icon">◈</span> Мой профиль
            </RouterLink>
            <div class="dropdown-divider"></div>
            <button type="button" class="dropdown-item danger" @click="handleLogout">
              <span class="dropdown-icon">⏻</span> Выйти
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
.login-btn {
  background: #1b2838; color: #fff; border: 1px solid #2a3f5a;
  padding: 8px 14px; border-radius: var(--radius-sm);
  font-weight: 600; font-size: 12px; cursor: pointer;
}

.topbar {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-primary);
  position: sticky;
  top: 0;
  z-index: 50;
  gap: 16px;
}

.search {
  position: relative;
  display: flex;
  align-items: center;
  width: 360px;
  max-width: 46vw;
}
.search-icon {
  position: absolute;
  left: 12px;
  color: var(--text-muted);
  pointer-events: none;
  z-index: 1;
  display: flex;
}
.search-icon svg { width: 15px; height: 15px; }
.search input {
  width: 100%;
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 8px 12px 8px 36px;
  color: var(--text-primary);
  font-size: 13px;
}
.search input:focus {
  outline: none;
  border-color: var(--accent);
}

.suggest-box {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  z-index: 60;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
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
.suggest-item:hover { background: var(--bg-card-hover); }
.suggest-av {
  width: 28px;
  height: 28px;
  border-radius: 4px;
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
.suggest-text { display: flex; flex-direction: column; min-width: 0; }
.suggest-name { font-size: 13px; font-weight: 600; }
.suggest-user { font-size: 11px; color: var(--text-secondary); }

.top-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.notif-wrap { position: relative; }
.bell-btn {
  position: relative;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.bell-btn:hover {
  border-color: var(--border-hover);
  background: var(--bg-card-hover);
}
.bell-icon { font-size: 15px; line-height: 1; }
.bell-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 999px;
  background: var(--accent);
  color: #12100c;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 0 2px var(--bg-primary);
}

.notif-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: min(340px, 92vw);
  max-height: 420px;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
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
  font-size: 13px;
  font-weight: 600;
}
.mark-all {
  border: none;
  background: none;
  color: var(--accent);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}
.notif-list {
  overflow-y: auto;
  max-height: 360px;
}
.notif-item {
  display: flex;
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
.notif-item:hover { background: var(--bg-card-hover); }
.notif-item.unread { background: var(--accent-dim); }
.notif-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.notif-body b { font-size: 13px; font-weight: 600; }
.notif-body span {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.35;
}
.notif-time {
  font-size: 10px;
  color: var(--text-muted);
  flex-shrink: 0;
  white-space: nowrap;
}
.notif-empty {
  padding: 28px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--text-muted);
}

.user-block { position: relative; }
.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px 8px 4px 4px;
  border-radius: var(--radius-sm);
}
.user-trigger:hover { background: var(--bg-card-hover); }
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background-color: var(--accent-dim);
  background-size: cover;
  background-position: center;
  border: 1px solid var(--border-color);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.avatar-fallback {
  font-weight: 700;
  font-size: 13px;
  color: var(--accent);
}
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
  color: var(--text-secondary);
  font-size: 12px;
  transition: transform 0.15s;
}
.chevron.open { transform: rotate(180deg); }

.dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 180px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
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
  padding: 8px 10px;
  border-radius: var(--radius-sm);
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
.dropdown-item.danger:hover {
  background: rgba(201, 122, 114, 0.12);
  color: var(--danger);
}
.dropdown-icon {
  width: 16px;
  text-align: center;
  color: var(--text-secondary);
}
.dropdown-divider {
  height: 1px;
  background: var(--border-color);
  margin: 4px 2px;
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
</style>