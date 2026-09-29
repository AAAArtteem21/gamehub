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
  loadQuickStats()
  loadSocial()
  loadClanPanel()
})
</script>

<template>
  <aside class="sidebar">
    <div class="logo">
      <img :src="logo" alt="GameEyes" class="logo-mark" />
      <div class="logo-text-group">
        <span class="logo-text">GAME<span class="accent-text">EYES</span></span>
        <span class="logo-tagline">FIND. PLAY. WIN.</span>
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
            background: `conic-gradient(var(--success) 0 ${winPct}%, rgba(248,113,113,0.28) ${winPct}% 100%)`,
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

    <div class="sidebar-widget">
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
  width: 248px;
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  background: rgba(20, 23, 30, 0.94);
  backdrop-filter: blur(14px);
  border-right: 1px solid var(--border-color);
  padding: 18px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  box-sizing: border-box;
  z-index: 40;
}
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 8px 8px;
  flex-shrink: 0;
}
.logo-mark {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  object-fit: cover;
  flex-shrink: 0;
}
.logo-text-group {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}
.logo-text {
  font-weight: 800;
  letter-spacing: 0.4px;
  font-size: 15px;
  color: var(--text-primary);
}
.accent-text { color: var(--accent); }
.logo-tagline {
  font-size: 9px;
  letter-spacing: 1.2px;
  color: var(--text-muted);
  font-weight: 600;
}
.nav {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex-shrink: 0;
  padding: 0 2px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 10px 12px;
  border-radius: 10px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  transition: background 0.15s var(--ease), color 0.15s var(--ease);
}
.nav-item:hover {
  background: var(--bg-card-hover);
  color: var(--text-primary);
  text-decoration: none;
}
.nav-item.active {
  background: var(--accent-dim);
  color: var(--accent);
  box-shadow: inset 0 0 0 1px rgba(230, 57, 70, 0.22);
}
.nav-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.9;
}
.nav-icon svg { width: 18px; height: 18px; }
.sidebar-widget {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}
.foot-widget { margin-top: auto; }
.widget-title {
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 800;
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
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.widget-value.accent { color: var(--accent); }
.week-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.week-ring {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.week-ring-inner {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.week-nums {
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
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
.period {
  font-size: 11px;
  color: var(--text-muted);
}
.week-games {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.week-game-btn {
  font-size: 10px;
  font-weight: 700;
  padding: 4px 9px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: none;
  color: var(--text-secondary);
  cursor: pointer;
}
.week-game-btn.active {
  background: var(--accent-dim);
  color: var(--accent);
  border-color: rgba(230, 57, 70, 0.4);
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
  padding: 5px 4px;
  cursor: pointer;
  text-align: left;
  border-radius: 8px;
}
.fav-item:hover { background: var(--bg-card-hover); }
.fav-av {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--accent-dim) center/cover no-repeat;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 800;
  color: var(--accent);
}
.fav-name {
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.clan-tabs { display: flex; flex-wrap: wrap; gap: 4px; }
.clan-tab {
  font-size: 10px;
  font-weight: 700;
  padding: 4px 9px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: none;
  color: var(--text-secondary);
  cursor: pointer;
}
.clan-tab.active {
  background: var(--accent-dim);
  color: var(--accent);
  border-color: rgba(230, 57, 70, 0.4);
}
.clan-one-name {
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.my-role {
  font-size: 10px;
  font-weight: 700;
  color: var(--accent);
  background: var(--accent-dim);
  padding: 2px 7px;
  border-radius: 8px;
}
.clan-sub {
  font-size: 10px;
  font-weight: 800;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 2px;
}
.clan-feed,
.clan-chat {
  max-height: 120px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.feed-line,
.chat-line {
  font-size: 11px;
  line-height: 1.35;
  color: var(--text-secondary);
}
.feed-line b,
.chat-line b {
  color: var(--text-primary);
  font-weight: 700;
}
.chat-role {
  font-size: 9px;
  font-weight: 800;
  padding: 1px 5px;
  border-radius: 6px;
  margin-right: 3px;
}
.chat-role.leader {
  background: rgba(240, 199, 94, 0.2);
  color: #f0c75e;
}
.chat-role.officer {
  background: var(--accent-dim);
  color: var(--accent);
}
.chat-role.member {
  background: var(--bg-card-hover);
  color: var(--text-muted);
}
.chat-form {
  display: flex;
  gap: 6px;
  margin-top: 2px;
}
.chat-form input {
  flex: 1;
  min-width: 0;
  font-size: 11px;
  padding: 7px 9px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
}
.chat-form button {
  border: none;
  background: var(--accent);
  color: #fff;
  border-radius: 8px;
  padding: 0 12px;
  cursor: pointer;
  font-weight: 800;
}
.chat-form button:disabled { opacity: 0.5; }
</style>