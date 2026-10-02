<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/axios'
import ClanIcon from '../components/clans/ClanIcon.vue'
import { useAuthStore } from '../stores/auth'


const auth = useAuthStore()
const router = useRouter()

const lfgPosts = ref([])
const leaderboard = ref([])
const leaderboardLoading = ref(true)
const selectedGame = ref('dota2')

const clanLeaderboard = ref([])
const clanLeaderboardLoading = ref(true)

const recentMatches = ref([])
const availablePlatforms = ref([])
const recentMatchesPlatform = ref('')

const weekly = ref(null)
const recs = ref([])

const worldGames = [
  { value: 'dota2', label: 'Dota 2' },
  { value: 'lol', label: 'League of Legends' },
  { value: 'cs2', label: 'CS2' },
  { value: 'valorant', label: 'Valorant' },
]

async function loadLfg() {
  try {
    const res = await api.get('lfg-posts/', { params: { page_size: 5 } })
    lfgPosts.value = res.data.results || res.data || []
  } catch {
    lfgPosts.value = []
  }
}

async function loadLeaderboard() {
  leaderboardLoading.value = true
  try {
    const res = await api.get('world-leaderboard/', { params: { game: selectedGame.value } })
    leaderboard.value = res.data || []
  } catch {
    leaderboard.value = []
  } finally {
    leaderboardLoading.value = false
  }
}

async function loadClanLeaderboard() {
  clanLeaderboardLoading.value = true
  try {
    const res = await api.get('clans/leaderboard/')
    clanLeaderboard.value = res.data || []
  } catch {
    clanLeaderboard.value = []
  } finally {
    clanLeaderboardLoading.value = false
  }
}

async function loadRecentMatches() {
  try {
    const params = {}
    if (recentMatchesPlatform.value) params.platform = recentMatchesPlatform.value
    const res = await api.get('me/recent-matches/', { params })
    recentMatches.value = res.data.matches || []
    availablePlatforms.value = res.data.available_platforms || []
  } catch {
    recentMatches.value = []
  }
}

async function loadSocialBlocks() {
  try {
    const [w, r] = await Promise.all([
      api.get('me/weekly-report/'),
      api.get('recommendations/teammates/'),
    ])
    weekly.value = w.data
    recs.value = r.data || []
  } catch {
    weekly.value = null
    recs.value = []
  }
}

function formatMinutes(min) {
  if (!min) return '0м'
  if (min < 60) return `${min}м`
  const h = Math.floor(min / 60)
  const m = min % 60
  return m ? `${h}ч ${m}м` : `${h}ч`
}

function leaderboardTo(entry) {
  if (entry.guest_link) return entry.guest_link
  if (entry.gamehub_user_id) return `/players/${entry.gamehub_user_id}`
  return null
}

watch(selectedGame, loadLeaderboard)
watch(recentMatchesPlatform, () => {
  if (auth.isAuthenticated) loadRecentMatches()
})

onMounted(() => {
  loadLfg()
  loadLeaderboard()
  loadClanLeaderboard()
  if (auth.isAuthenticated) {
    loadRecentMatches()
    loadSocialBlocks()
  }
})
</script>

<template>
  <div class="home">
    <div class="hero">
      <h1>Команда под твой ранг и стиль</h1>
      <p class="hero-sub">
        LFG, кланы и статистика с привязанных аккаунтов — без выдуманных профилей.
      </p>
      <div class="hero-actions">
        <button type="button" class="btn-primary" @click="router.push('/lfg')">
          Найти тиммейтов
        </button>
        <button type="button" class="btn-ghost" @click="router.push('/lfg?create=1')">
          Создать заявку
        </button>
      </div>
    </div>

    <div class="home-grid">
      <div class="col-main">
        <div v-if="auth.isAuthenticated" class="card section-card">
          <div class="section-head">
            <h3>Последние заявки LFG</h3>
            <RouterLink to="/lfg" class="link-all">Все →</RouterLink>
          </div>
          <div v-if="!lfgPosts.length" class="empty-hint">Пока нет заявок</div>
          <div
            v-for="post in lfgPosts"
            :key="post.id"
            class="lfg-row"
            @click="router.push(`/lfg/${post.id}`)"
          >
            <div class="lfg-left">
              <span class="lfg-game">{{ post.game || post.game_label || 'Игра' }}</span>
              <span class="lfg-title">{{ post.title || post.description?.slice(0, 60) }}</span>
            </div>
            <span class="lfg-meta">{{ post.responses_count ?? 0 }} откликов</span>
          </div>
        </div>
        <div v-else class="card section-card">
          <div class="section-head"><h3>Твоя статистика</h3></div>
          <div class="empty-hint">Войди, чтобы видеть свои матчи и рекомендации</div>
          <button type="button" class="btn-primary" @click="auth.loginWithSteam()">
            Войти через Steam
          </button>
        </div>

        <div class="card section-card">
          <div class="section-head">
            <h3>Последние матчи</h3>
            <select
              v-if="availablePlatforms.length > 1"
              v-model="recentMatchesPlatform"
              class="platform-select-mini"
            >
              <option value="">Все игры</option>
              <option
                v-for="p in availablePlatforms"
                :key="p.value || p"
                :value="p.value || p"
              >
                {{ p.label || p }}
              </option>
            </select>
          </div>
          <div v-if="!recentMatches.length" class="empty-hint">Синкни аккаунт — появятся матчи</div>
          <div class="match-feed">
            <div
              v-for="(m, i) in recentMatches"
              :key="i"
              class="match-feed-item"
              :class="{ win: m.won === true, loss: m.won === false }"
            >
              <span class="feed-result">{{ m.won ? 'W' : 'L' }}</span>
              <div class="feed-info">
                <span class="feed-title">{{ m.title }}</span>
                <span class="feed-game">{{ m.game_label || m.platform }}</span>
              </div>
              <span class="feed-kda">{{ m.subtitle }}</span>
            </div>
          </div>
        </div>

        <div class="card section-card">
          <div class="section-head">
            <h3>Топ кланов за месяц</h3>
            <RouterLink to="/clans" class="link-all">Все →</RouterLink>
          </div>
          <div v-if="clanLeaderboardLoading" class="empty-hint">Загрузка...</div>
          <div v-else-if="!clanLeaderboard.length" class="empty-hint">Пока нет данных</div>
          <div
            v-for="(c, i) in clanLeaderboard"
            :key="c.id"
            class="clan-lb-row"
            @click="router.push('/clans')"
          >
            <span class="rank" :class="{ gold: i === 0, silver: i === 1, bronze: i === 2 }">
              {{ i + 1 }}
            </span>
            <ClanIcon :clan="c" :size="32" />
            <div class="clan-lb-info">
              <span class="clan-lb-name">{{ c.name }}</span>
              <span class="clan-lb-sub">{{ c.members_count }} участников</span>
            </div>
            <span class="clan-lb-val">{{ formatMinutes(c.total_month_minutes) }}</span>
          </div>
        </div>
      </div>

      <div class="col-side">
        <div class="card section-card lb-card">
          <div class="section-head">
            <div>
              <h3>Мировой лидерборд</h3>
              <p class="lb-caption">Топ игроков — не только с GameEyes</p>
            </div>
          </div>
          <div class="game-tabs">
            <button
              v-for="g in worldGames"
              :key="g.value"
              type="button"
              class="game-tab"
              :class="{ active: selectedGame === g.value }"
              @click="selectedGame = g.value"
            >
              {{ g.label }}
            </button>
          </div>
          <div v-if="leaderboardLoading" class="empty-hint">Загрузка...</div>
          <div v-else-if="!leaderboard.length" class="empty-hint">Нет данных</div>
          <div v-else class="leaderboard-list">
            <component
              :is="leaderboardTo(entry) ? 'RouterLink' : 'div'"
              v-for="(entry, i) in leaderboard"
              :key="entry.external_id || entry.name || i"
              :to="leaderboardTo(entry) || undefined"
              class="leaderboard-item"
              :class="{ clickable: !!leaderboardTo(entry) }"
            >
              <span
                class="rank"
                :class="{ gold: i === 0, silver: i === 1, bronze: i === 2 }"
              >{{ i + 1 }}</span>
              <div
                class="lb-avatar"
                :style="entry.avatar ? { backgroundImage: `url(${entry.avatar})` } : {}"
              >
                <span v-if="!entry.avatar">{{ entry.name?.[0]?.toUpperCase() }}</span>
              </div>
              <div class="lb-info">
                <span class="lb-name">{{ entry.name }}</span>
                <span class="lb-subtitle">{{ entry.subtitle || entry.team || '' }}</span>
              </div>
              <span class="lb-value" v-if="entry.value">{{ entry.value }}</span>
            </component>
          </div>
        </div>

        <div class="card social-card" v-if="recs.length">
          <h3>Кого взять в команду</h3>
          <RouterLink
            v-for="u in recs"
            :key="u.user_id"
            :to="`/players/${u.user_id}`"
            class="rec-row"
          >
            <div
              class="rec-avatar"
              :style="u.avatar_url ? { backgroundImage: `url(${u.avatar_url})` } : {}"
            >
              <span v-if="!u.avatar_url">{{ (u.display_name || '?')[0]?.toUpperCase() }}</span>
            </div>
            <div class="rec-info">
              <span class="rec-name">{{ u.display_name }}</span>
              <span class="rec-meta">{{ u.game_label || u.platform }}</span>
            </div>
            <span v-if="u.has_open_lfg" class="lfg-tag">LFG</span>
          </RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
}

.hero {
  padding: 4px 0 8px;
}
.hero h1 {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 600;
}
.hero-sub {
  margin: 0 0 14px;
  color: var(--text-secondary);
  max-width: 440px;
  font-size: 13px;
}
.hero-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.home-grid {
  display: grid;
  grid-template-columns: 1fr minmax(280px, 340px);
  gap: 16px;
  align-items: start;
  width: 100%;
}
@media (max-width: 960px) {
  .home-grid { grid-template-columns: 1fr; }
}

.section-card,
.social-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.section-head h3,
.social-card h3 {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
}
.link-all {
  font-size: 12px;
  color: var(--accent);
  text-decoration: none;
  font-weight: 600;
}
.empty-hint {
  color: var(--text-secondary);
  font-size: 13px;
  padding: 12px 0;
  text-align: center;
}
.lb-caption {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--text-muted);
  text-transform: none;
  letter-spacing: 0;
  font-weight: 400;
}

.lfg-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 8px 6px;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.lfg-row:hover { background: var(--bg-card-hover); }
.lfg-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.lfg-game {
  font-size: 11px;
  color: var(--accent);
  font-weight: 600;
}
.lfg-title {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.lfg-meta {
  font-size: 12px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.match-feed {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.match-feed-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 6px;
  border-radius: var(--radius-sm);
}
.feed-result {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
  font-family: var(--font-mono);
}
.match-feed-item.win .feed-result {
  background: rgba(106, 170, 124, 0.15);
  color: var(--success);
}
.match-feed-item.loss .feed-result {
  background: rgba(201, 122, 114, 0.15);
  color: var(--danger);
}
.feed-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.feed-title { font-size: 13px; font-weight: 600; }
.feed-game { font-size: 11px; color: var(--text-secondary); }
.feed-kda {
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--text-secondary);
}

.platform-select-mini {
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 11px;
  padding: 4px 8px;
  cursor: pointer;
}

.clan-lb-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 4px;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.clan-lb-row:hover { background: var(--bg-card-hover); }
.clan-lb-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.clan-lb-name { font-weight: 600; font-size: 13px; }
.clan-lb-sub { font-size: 11px; color: var(--text-secondary); }
.clan-lb-val {
  font-weight: 600;
  color: var(--accent);
  font-size: 12px;
  font-family: var(--font-mono);
}

.rank {
  width: 20px;
  text-align: center;
  font-weight: 700;
  font-size: 12px;
  color: var(--text-secondary);
  font-family: var(--font-mono);
}
.rank.gold { color: #c4a574; }
.rank.silver { color: #a8aeb8; }
.rank.bronze { color: #a67c52; }

.game-tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}
.game-tab {
  background: none;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.game-tab.active {
  background: var(--accent-dim);
  color: var(--accent);
  border-color: var(--accent);
}

.leaderboard-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 520px;
  overflow-y: auto;
}
.leaderboard-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 4px;
  border-radius: var(--radius-sm);
  text-decoration: none;
  color: inherit;
}
.leaderboard-item.clickable { cursor: pointer; }
.leaderboard-item.clickable:hover { background: var(--bg-card-hover); }
.lb-avatar {
  width: 28px;
  height: 28px;
  border-radius: 4px;
  flex-shrink: 0;
  background-color: var(--bg-card-hover);
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
}
.lb-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.lb-name {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.lb-subtitle {
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.lb-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
  flex-shrink: 0;
  font-family: var(--font-mono);
}

.rec-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
  text-decoration: none;
  color: inherit;
}
.rec-row:last-child { border-bottom: none; }
.rec-avatar {
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
.rec-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.rec-name { font-weight: 600; font-size: 13px; }
.rec-meta { font-size: 11px; color: var(--text-secondary); }
.lfg-tag {
  font-size: 10px;
  font-weight: 700;
  color: var(--accent);
  background: var(--accent-dim);
  padding: 2px 7px;
  border-radius: var(--radius-sm);
}
</style>