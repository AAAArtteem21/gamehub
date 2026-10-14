<script setup>
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ref, onMounted, computed, watch, inject } from 'vue'
import api from '../../api/axios'
import IconHome from '../icons/IconHome.vue'
import IconSword from '../icons/IconSword.vue'
import IconShield from '../icons/IconShield.vue'
import IconTarget from '../icons/IconTarget.vue'
import { useToast } from '../../composables/useToast'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const toast = useToast()
const sidebarOpen = inject('sidebarOpen', ref(false))
const closeSidebar = inject('closeSidebar', () => {})

const navItems = [
  { name: 'Дашборд', path: '/', icon: IconHome },
  { name: 'Поиск тиммейтов', path: '/lfg', icon: IconSword },
  { name: 'Кланы', path: '/clans', icon: IconShield },
  { name: 'Профиль', path: '/profile', icon: IconTarget },
]

const route = useRoute()
const router = useRouter()

const quickStats = ref(null)
const weekly = ref(null)
const favorites = ref([])
const clanPanels = ref([])
const activeClanIdx = ref(0)
const chatText = ref('')
const chatSending = ref(false)

const roleLabel = { leader: 'Лидер', officer: 'Офицер', member: 'Участник' }

const winPct = computed(() => {
  if (!weekly.value) return 0
  const t = (weekly.value.wins || 0) + (weekly.value.losses || 0)
  if (!t) return 0
  return Math.round((weekly.value.wins / t) * 100)
})

const weekMatches = computed(() => {
  if (!weekly.value) return 0
  return (weekly.value.wins || 0) + (weekly.value.losses || 0)
})

const activeClan = computed(() => clanPanels.value[activeClanIdx.value] || null)

function loadPersonal() {
  loadQuickStats()
  loadSocial()
  loadClanPanel()
}
function resetPersonal() {
  quickStats.value = null
  weekly.value = null
  favorites.value = []
  clanPanels.value = []
}
function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(path + '/')
}
function onNavClick() { closeSidebar() }
function goWeekly() {
  closeSidebar()
  router.push({ path: '/profile', hash: '#weekly' })
}

async function loadQuickStats() {
  try {
    const res = await api.get('me/quick-stats/')
    quickStats.value = res.data
  } catch { quickStats.value = null }
}
async function loadWeekly() {
  try {
    const res = await api.get('me/weekly-report/')
    weekly.value = res.data
  } catch { weekly.value = null }
}
async function loadFavorites() {
  try {
    const res = await api.get('favorites/')
    favorites.value = res.data || []
  } catch { favorites.value = [] }
}
async function loadSocial() {
  await Promise.all([loadWeekly(), loadFavorites()])
}
async function loadClanPanel() {
  try {
    const res = await api.get('clans/my-panel/')
    clanPanels.value = res.data || []
    if (activeClanIdx.value >= clanPanels.value.length) activeClanIdx.value = 0
  } catch { clanPanels.value = [] }
}
async function sendClanMsg() {
  if (!activeClan.value || !chatText.value.trim() || chatSending.value) return
  chatSending.value = true
  try {
    const res = await api.post(`clans/${activeClan.value.clan_id}/messages/`, {
      text: chatText.value.trim(),
    })
    if (!activeClan.value.messages) activeClan.value.messages = []
    activeClan.value.messages.push(res.data)
    chatText.value = ''
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Не отправлено')
  } finally {
    chatSending.value = false
  }
}
function openFavorite(u) {
  closeSidebar()
  if (u.link) { router.push(u.link); return }
  if (u.user_id) { router.push(`/players/${u.user_id}`); return }
  if (u.platform && u.external_id) {
    const g = u.platform === 'opendota' ? 'dota2' : u.platform
    router.push(`/players/guest/${g}/${encodeURIComponent(u.external_id)}`)
  }
}

onMounted(() => { if (auth.isAuthenticated) loadPersonal() })
watch(() => auth.isAuthenticated, (v) => (v ? loadPersonal() : resetPersonal()))
</script>

<template>
  <aside class="sidebar" :class="{ open: sidebarOpen }">
    <nav class="nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: isActive(item.path) }"
        @click="onNavClick"
      >
        <span class="nav-icon"><component :is="item.icon" /></span>
        {{ item.name }}
      </RouterLink>
    </nav>

    <button
      v-if="weekly"
      type="button"
      class="sidebar-widget week-teaser"
      @click="goWeekly"
    >
      <span class="widget-title">Эта неделя</span>
      <div class="teaser-row">
        <span class="teaser-pct">{{ winPct }}%</span>
        <span class="teaser-wl">
          <b class="w">{{ weekly.wins || 0 }}</b>W ·
          <b class="l">{{ weekly.losses || 0 }}</b>L
        </span>
      </div>
      <div class="teaser-meta">
        <span v-if="weekly.best_hero">{{ weekly.best_hero }}</span>
        <span v-else-if="weekMatches">{{ weekMatches }} матч.</span>
        <span v-else>нет матчей</span>
        <span class="teaser-link">Подробнее →</span>
      </div>
    </button>

    <div class="sidebar-widget" v-if="!auth.isAuthenticated">
      <span class="widget-title">Аккаунт</span>
      <div class="fav-empty">Войди, чтобы видеть статистику, кланы и чаты</div>
      <button type="button" class="chat-form-btn" @click="auth.loginWithSteam()">
        Войти через Steam
      </button>
    </div>

    <div class="sidebar-widget" v-if="auth.isAuthenticated">
      <div class="widget-head">
        <span class="widget-title">Избранные</span>
        <span class="widget-star">★</span>
      </div>
      <div v-if="!favorites.length" class="fav-empty">На профиле нажми «★ в избранное»</div>
      <button
        v-for="(u, i) in favorites.slice(0, 5)"
        :key="u.user_id || u.external_id || i"
        type="button"
        class="fav-item"
        @click="openFavorite(u)"
      >
        <div
          class="fav-av"
          :style="u.avatar_url ? { backgroundImage: `url(${u.avatar_url})` } : {}"
        >
          <span v-if="!u.avatar_url">{{ (u.display_name || u.username || '?')[0] }}</span>
        </div>
        <span class="fav-name">{{ u.display_name || u.username }}</span>
      </button>
    </div>

    <div class="sidebar-widget clan-panel" v-if="clanPanels.length">
      <span class="widget-title">Кланы</span>
      <div class="clan-tabs" v-if="clanPanels.length > 1">
        <button
          v-for="(c, i) in clanPanels"
          :key="c.clan_id"
          type="button"
          class="pill-btn"
          :class="{ active: activeClanIdx === i }"
          @click="activeClanIdx = i"
        >{{ c.clan_name }}</button>
      </div>
      <div class="clan-one-name" v-else-if="activeClan">
        {{ activeClan.clan_name }}
        <span class="my-role">{{ roleLabel[activeClan.my_role] || activeClan.my_role }}</span>
      </div>
      <template v-if="activeClan">
        <div class="clan-sub">Лента</div>
        <div class="clan-feed" v-if="activeClan.feed?.length">
          <div v-for="a in activeClan.feed.slice(0, 6)" :key="a.id" class="feed-line">
            <b>{{ a.username }}</b> — {{ a.text }}
          </div>
        </div>
        <div v-else class="fav-empty">Пока нет событий</div>
        <div class="clan-sub">Чат</div>
        <div class="clan-chat">
          <div v-for="m in activeClan.messages" :key="m.id" class="chat-line">
            <span class="chat-role" :class="m.role">{{ roleLabel[m.role] || m.role }}</span>
            <b>{{ m.sender_username }}</b>
            <span class="chat-text">{{ m.text }}</span>
          </div>
          <div v-if="!activeClan.messages?.length" class="fav-empty">Напиши первым</div>
        </div>
        <form class="chat-form" @submit.prevent="sendClanMsg">
          <input v-model="chatText" maxlength="1000" placeholder="Сообщение в клан..." :disabled="chatSending" />
          <button type="submit" :disabled="chatSending">→</button>
        </form>
      </template>
    </div>

    <div class="sidebar-widget foot-widget" v-if="quickStats || weekly">
      <span class="widget-title">Сводка</span>
      <div class="widget-row" v-if="quickStats">
        <span class="widget-label">Активных заявок</span>
        <span class="widget-value">{{ quickStats.open_lfg }}</span>
      </div>
      <div class="widget-row" v-if="quickStats">
        <span class="widget-label">Непрочитано чатов</span>
        <span class="widget-value accent">{{ quickStats.unread_chats }}</span>
      </div>
      <div class="widget-row" v-if="quickStats">
        <span class="widget-label">Кланов</span>
        <span class="widget-value">{{ quickStats.clans_count }}</span>
      </div>
      <div class="widget-row" v-if="weekly">
        <span class="widget-label">Матчей за неделю</span>
        <span class="widget-value">{{ weekMatches }}</span>
      </div>
      <div class="widget-row">
        <span class="widget-label">Избранных</span>
        <span class="widget-value">{{ favorites.length }}</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-w);
  height: calc(100vh - var(--topbar-h));
  position: fixed;
  left: 0;
  top: var(--topbar-h);
  padding: 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  box-sizing: border-box;
  z-index: 40;
}
.nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
  padding: 8px;
  background: var(--panel-bg, var(--bg-card));
  border: 1px solid var(--panel-border, var(--border-color));
  border-radius: 14px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid transparent;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
}
.nav-item:hover { background: var(--bg-card-hover); color: var(--text-primary); }
.nav-item.active {
  background: var(--accent-dim);
  border-color: var(--accent);
  color: var(--text-primary);
}
.nav-icon {
  width: 20px; height: 20px;
  display: flex; align-items: center; justify-content: center;
  color: var(--accent);
}
.nav-icon :deep(svg) { width: 18px; height: 18px; }

.sidebar-widget {
  background: var(--panel-bg, var(--bg-card));
  border: 1px solid var(--panel-border, var(--border-color));
  border-radius: 14px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}
.foot-widget { margin-top: auto; }
.widget-head { display: flex; justify-content: space-between; align-items: center; }
.widget-star { color: var(--accent); font-size: 14px; }
.widget-title {
  font-size: 10px;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 700;
}
.widget-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  gap: 8px;
}
.widget-label { color: var(--text-secondary); }
.widget-value {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}
.widget-value.accent { color: var(--accent); }

.week-teaser {
  width: 100%;
  text-align: left;
  cursor: pointer;
  font: inherit;
  color: inherit;
}
.week-teaser:hover {
  border-color: var(--border-hover);
  background: var(--bg-card-hover);
}
.teaser-row { display: flex; align-items: baseline; gap: 10px; }
.teaser-pct {
  font-size: 20px;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--accent);
}
.teaser-wl { font-size: 12px; color: var(--text-secondary); }
.teaser-wl .w { color: var(--success); }
.teaser-wl .l { color: var(--danger); }
.teaser-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--text-muted);
}
.teaser-link { color: var(--accent); font-weight: 600; flex-shrink: 0; }

.pill-btn {
  font-size: 10px; font-weight: 600;
  padding: 3px 10px; border-radius: 999px;
  border: 1px solid var(--border-color);
  background: var(--bg-sunken); color: var(--text-secondary); cursor: pointer;
}
.pill-btn.active {
  border-color: var(--accent); color: var(--accent); background: var(--accent-dim);
}
.fav-empty { font-size: 11px; color: var(--text-muted); line-height: 1.4; }
.fav-item {
  display: flex; align-items: center; gap: 8px; width: 100%;
  background: none; border: none; color: inherit; padding: 4px;
  cursor: pointer; text-align: left; border-radius: 8px;
}
.fav-item:hover { background: var(--bg-card-hover); }
.fav-av {
  width: 26px; height: 26px; border-radius: 8px; flex-shrink: 0;
  background: var(--accent-dim) center/cover no-repeat;
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 700; color: var(--accent);
}
.fav-name {
  font-size: 12px; font-weight: 500;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.clan-tabs { display: flex; flex-wrap: wrap; gap: 4px; }
.clan-one-name {
  font-size: 12px; font-weight: 600;
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
}
.my-role {
  font-size: 10px; font-weight: 600; color: var(--accent);
  background: var(--accent-dim); padding: 1px 6px; border-radius: 4px;
}
.clan-sub {
  font-size: 10px; font-weight: 600; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.05em; margin-top: 2px;
}
.clan-feed, .clan-chat {
  max-height: 110px; overflow-y: auto;
  display: flex; flex-direction: column; gap: 4px;
}
.feed-line, .chat-line {
  font-size: 11px; line-height: 1.35; color: var(--text-secondary);
}
.feed-line b, .chat-line b { color: var(--text-primary); font-weight: 600; }
.chat-role {
  font-size: 9px; font-weight: 600; padding: 1px 4px;
  border-radius: 3px; margin-right: 3px;
}
.chat-role.leader { background: var(--accent-dim); color: var(--accent); }
.chat-role.officer { background: var(--accent-2-dim); color: var(--accent-2); }
.chat-role.member { background: var(--bg-card); color: var(--text-muted); }
.chat-form { display: flex; gap: 4px; margin-top: 2px; }
.chat-form input { flex: 1; min-width: 0; font-size: 11px; padding: 6px 8px; }
.chat-form button {
  border: 1px solid var(--accent); background: var(--accent); color: #fff;
  border-radius: 8px; padding: 0 10px; cursor: pointer; font-weight: 700;
}
.chat-form-btn {
  background: var(--accent); color: #fff; border: none;
  padding: 8px; border-radius: 10px; font-weight: 700; cursor: pointer;
}
.chat-form button:disabled { opacity: 0.5; }

@media (max-width: 900px) {
  .sidebar {
    transform: translateX(-100%);
    transition: transform 0.2s var(--ease);
    z-index: 50;
    width: min(var(--sidebar-w), 86vw);
    background: var(--bg-primary);
  }
  .sidebar.open {
    transform: translateX(0);
    box-shadow: 8px 0 32px rgba(0, 0, 0, 0.45);
  }
}
</style>