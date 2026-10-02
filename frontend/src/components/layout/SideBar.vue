<script setup>
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ref, onMounted, computed } from 'vue'
import logo from '../../assets/images/logo.png'
import api from '../../api/axios'
import IconHome from '../icons/IconHome.vue'
import IconSword from '../icons/IconSword.vue'
import IconShield from '../icons/IconShield.vue'
import IconTarget from '../icons/IconTarget.vue'
import { useToast } from '../../composables/useToast'
import { watch } from 'vue'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()

const toast = useToast()

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
const weeklyGame = ref('all')

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

async function loadQuickStats() {
  try {
    const res = await api.get('me/quick-stats/')
    quickStats.value = res.data
  } catch {
    quickStats.value = null
  }
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

async function loadFavorites() {
  try {
    const res = await api.get('favorites/')
    favorites.value = res.data || []
  } catch {
    favorites.value = []
  }
}

async function loadSocial() {
  await Promise.all([loadWeekly(), loadFavorites()])
}

function setWeeklyGame(g) {
  weeklyGame.value = g
  loadWeekly()
}

async function loadClanPanel() {
  try {
    const res = await api.get('clans/my-panel/')
    clanPanels.value = res.data || []
    if (activeClanIdx.value >= clanPanels.value.length) activeClanIdx.value = 0
  } catch {
    clanPanels.value = []
  }
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
  if (u.link) {
    router.push(u.link)
    return
  }
  if (u.user_id) {
    router.push(`/players/${u.user_id}`)
    return
  }
  if (u.platform && u.external_id) {
    const g = u.platform === 'opendota' ? 'dota2' : u.platform
    router.push(`/players/guest/${g}/${encodeURIComponent(u.external_id)}`)
  }
}

onMounted(() => {
  if (auth.isAuthenticated) loadPersonal()
})
watch(() => auth.isAuthenticated, (v) => (v ? loadPersonal() : resetPersonal()))
</script>

<template>
  <aside class="sidebar">
    <div class="logo">
      <img :src="logo" alt="GameEyes" class="logo-mark" />
      <div class="logo-text-group">
        <span class="logo-text">GAME<span class="accent-text">EYES</span></span>
        <span class="logo-tagline">find · play · win</span>
      </div>
    </div>

    <nav class="nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: isActive(item.path) }"
      >
        <span class="nav-icon"><component :is="item.icon" /></span>
        {{ item.name }}
      </RouterLink>
    </nav>

    <div class="sidebar-widget" v-if="weekly">
      <span class="widget-title">Эта неделя</span>
      <div class="week-games" v-if="(weekly.available_games || []).length">
        <button
          type="button"
          class="week-game-btn"
          :class="{ active: weeklyGame === 'all' }"
          @click="setWeeklyGame('all')"
        >Все</button>
        <button
          v-for="g in weekly.available_games"
          :key="g.value"
          type="button"
          class="week-game-btn"
          :class="{ active: weeklyGame === g.value }"
          @click="setWeeklyGame(g.value)"
        >{{ g.label }}</button>
      </div>
      <div class="week-row">
        <div
          class="week-ring"
          :style="{
            background: `conic-gradient(var(--success) 0 ${winPct}%, rgba(201,122,114,0.25) ${winPct}% 100%)`,
          }"
        >
          <div class="week-ring-inner">{{ winPct }}%</div>
        </div>
        <div class="week-nums">
          <div><b class="w">{{ weekly.wins }}</b> побед</div>
          <div><b class="l">{{ weekly.losses }}</b> пораж.</div>
          <div class="best" v-if="weekly.best_hero">{{ weekly.best_hero }}</div>
        </div>
      </div>
      <div class="period" v-if="weekly.period">{{ weekly.period }}</div>
      <div class="period" v-if="weekly.streak_wins > 1">
        Серия: <b class="w">{{ weekly.streak_wins }}</b>
      </div>
    </div>

    <div class="sidebar-widget" v-if="!auth.isAuthenticated">
      <span class="widget-title">Аккаунт</span>
      <div class="fav-empty">Войди, чтобы видеть статистику, кланы и чаты</div>
      <button type="button" class="chat-form-btn" @click="auth.loginWithSteam()">
        Войти через Steam
      </button>
    </div>

    <div class="sidebar-widget" v-if="auth.isAuthenticated">
      <span class="widget-title">Избранные</span>
      <div v-if="!favorites.length" class="fav-empty">
        На профиле нажми «☆ В избранное»
      </div>
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
          class="clan-tab"
          :class="{ active: activeClanIdx === i }"
          @click="activeClanIdx = i"
        >
          {{ c.clan_name }}
        </button>
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
          <input
            v-model="chatText"
            maxlength="1000"
            placeholder="Сообщение в клан..."
            :disabled="chatSending"
          />
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
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  background: var(--bg-sunken);
  border-right: 1px solid var(--border-color);
  padding: 14px 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  box-sizing: border-box;
  z-index: 40;
}
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 8px 12px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 2px;
  flex-shrink: 0;
}
.logo-mark {
  width: 28px;
  height: 28px;
  border-radius: 4px;
  object-fit: cover;
  flex-shrink: 0;
}
.logo-text-group {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
  min-width: 0;
}
.logo-text {
  font-weight: 700;
  letter-spacing: 0.04em;
  font-size: 13px;
  color: var(--text-primary);
}
.accent-text { color: var(--accent); }
.logo-tagline {
  font-size: 9px;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  font-weight: 500;
  text-transform: lowercase;
}
.nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex-shrink: 0;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  border-left: 2px solid transparent;
}
.nav-item:hover {
  background: var(--bg-card);
  color: var(--text-primary);
  text-decoration: none;
}
.nav-item.active {
  background: var(--bg-card);
  color: var(--text-primary);
  border-left-color: var(--accent);
}
.nav-icon {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.8;
}
.nav-icon svg { width: 16px; height: 16px; }

.sidebar-widget {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
  background: transparent;
}
.foot-widget { margin-top: auto; }
.widget-title {
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  font-weight: 600;
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

.week-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.week-ring {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.week-ring-inner {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  font-family: var(--font-mono);
}
.week-nums {
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.week-nums .w { color: var(--success); }
.week-nums .l { color: var(--danger); }
.best {
  font-size: 11px;
  color: var(--text-muted);
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.period { font-size: 11px; color: var(--text-muted); }

.week-games, .clan-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.week-game-btn, .clan-tab {
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background: none;
  color: var(--text-secondary);
  cursor: pointer;
}
.week-game-btn.active, .clan-tab.active {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-dim);
}

.fav-empty {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.4;
}
.fav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  background: none;
  border: none;
  color: inherit;
  padding: 4px;
  cursor: pointer;
  text-align: left;
  border-radius: var(--radius-sm);
}
.fav-item:hover { background: var(--bg-card); }
.fav-av {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  flex-shrink: 0;
  background: var(--accent-dim) center/cover no-repeat;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  color: var(--accent);
}
.fav-name {
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.clan-one-name {
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.my-role {
  font-size: 10px;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-dim);
  padding: 1px 6px;
  border-radius: 4px;
}
.clan-sub {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: 2px;
}
.clan-feed, .clan-chat {
  max-height: 110px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.feed-line, .chat-line {
  font-size: 11px;
  line-height: 1.35;
  color: var(--text-secondary);
}
.feed-line b, .chat-line b {
  color: var(--text-primary);
  font-weight: 600;
}
.chat-role {
  font-size: 9px;
  font-weight: 600;
  padding: 1px 4px;
  border-radius: 3px;
  margin-right: 3px;
}
.chat-role.leader {
  background: var(--accent-dim);
  color: var(--accent);
}
.chat-role.officer {
  background: var(--accent-2-dim);
  color: var(--accent-2);
}
.chat-role.member {
  background: var(--bg-card);
  color: var(--text-muted);
}
.chat-form {
  display: flex;
  gap: 4px;
  margin-top: 2px;
}
.chat-form input {
  flex: 1;
  min-width: 0;
  font-size: 11px;
  padding: 6px 8px;
}
.chat-form button {
  border: 1px solid var(--accent);
  background: var(--accent);
  color: #12100c;
  border-radius: var(--radius-sm);
  padding: 0 10px;
  cursor: pointer;
  font-weight: 700;
}
.chat-form-btn {
  background: var(--accent); color: #12100c; border: none;
  padding: 8px; border-radius: var(--radius-sm); font-weight: 700; cursor: pointer;
}
.chat-form button:disabled { opacity: 0.5; }
</style>