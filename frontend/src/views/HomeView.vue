<script setup>
import { ref, onMounted, watch, computed } from 'vue'
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
const accountsCount = ref(0)

const worldGames = [
  { value: 'dota2', label: 'Dota 2' },
  { value: 'lol', label: 'League of Legends' },
  { value: 'cs2', label: 'CS2' },
  { value: 'valorant', label: 'Valorant' },
]

const weekWins = computed(() => Number(weekly.value?.wins) || 0)
const weekLosses = computed(() => Number(weekly.value?.losses) || 0)
const weekTotal = computed(() => weekWins.value + weekLosses.value)
const weekPct = computed(() =>
  weekTotal.value ? Math.round((weekWins.value / weekTotal.value) * 100) : 0
)

const hasAccounts = computed(() => accountsCount.value > 0)
const emptyMatchesHint = computed(() => {
  if (!auth.isAuthenticated) return 'Войди, чтобы видеть свои матчи'
  if (!hasAccounts.value) return 'Подключи Steam / Faceit / Dota — появятся матчи'
  return 'Синкни аккаунт на профиле — история подтянется'
})

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
    leaderboard.value = Array.isArray(res.data) ? res.data : []
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
    const [w, r, acc] = await Promise.all([
      api.get('me/weekly-report/').catch(() => ({ data: null })),
      api.get('recommendations/teammates/').catch(() => ({ data: [] })),
      api.get('game-accounts/').catch(() => ({ data: [] })),
    ])
    weekly.value = w.data
    recs.value = r.data || []
    const list = acc.data?.results || acc.data || []
    accountsCount.value = Array.isArray(list) ? list.length : 0
  } catch {
    weekly.value = null
    recs.value = []
  }
}

function formatHours(min) {
  if (!min) return '0ч'
  const h = min / 60
  return h >= 10 ? `${Math.round(h)}ч` : `${(Math.round(h * 10) / 10).toFixed(1)}ч`
}

function leaderboardTo(entry) {
  if (entry.guest_link) return entry.guest_link
  if (entry.gamehub_user_id) return `/players/${entry.gamehub_user_id}`
  return null
}

function openMatchRow(m) {
  if (!m?.match_id) return
  const p = String(m.platform || '').toLowerCase()
  // детали матча живут на профиле; с дашборда ведём туда
  router.push('/profile')
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
      <div class="hero-text">
        <h1>Команда под твой ранг и стиль</h1>
        <p class="hero-sub">
          LFG, кланы и статистика с привязанных аккаунтов — без выдуманных профилей.
        </p>
        <div class="hero-actions">
          <button type="button" class="btn-primary" @click="router.push('/lfg')">
            Найти тиммейтов
          </button>
          <button type="button" class="btn-ghost" @click="router.push('/profile')">
            Мой профиль
          </button>
        </div>
      </div>

      <!-- Мини-неделя -->
      <div
        v-if="auth.isAuthenticated && weekly && weekTotal > 0"
        class="week-snap card"
        @click="router.push({ path: '/profile', hash: '#weekly' })"
      >
        <span class="snap-label">Эта неделя</span>
        <div class="snap-row">
          <span class="snap-pct">{{ weekPct }}%</span>
          <div class="snap-wl">
            <span class="w">{{ weekWins }}W</span>
            <span class="l">{{ weekLosses }}L</span>
          </div>
        </div>
        <span class="snap-meta" v-if="weekly.best_hero">{{ weekly.best_hero }}</span>
        <span class="snap-link">Подробнее →</span>
      </div>
      <div
        v-else-if="auth.isAuthenticated"
        class="week-snap card empty"
        @click="router.push('/profile')"
      >
        <span class="snap-label">Эта неделя</span>
        <p class="snap-empty-text">Нет матчей за 7 дней. Синкни аккаунт или сыграй.</p>
        <span class="snap-link">Профиль →</span>
      </div>
    </div>

    <div class="home-grid">
      <div class="col-main">
        <!-- LFG -->
        <div class="card section-card">
          <div class="section-head">
            <h3>Последние заявки LFG</h3>
            <RouterLink to="/lfg" class="link-all">Все →</RouterLink>
          </div>
          <div v-if="!lfgPosts.length" class="empty-block">
            <p>Пока нет открытых заявок.</p>
            <button type="button" class="btn-primary" @click="router.push('/lfg')">
              Создать заявку
            </button>
          </div>
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

        <!-- Матчи -->
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
          <div v-if="!recentMatches.length" class="empty-block">
            <p>{{ emptyMatchesHint }}</p>
            <button
              v-if="auth.isAuthenticated"
              type="button"
              class="btn-ghost"
              @click="router.push('/profile')"
            >
              К аккаунтам
            </button>
          </div>
          <div class="match-feed" v-else>
            <div
              v-for="(m, i) in recentMatches"
              :key="i"
              class="match-feed-item"
              :class="{
                win: m.won === true,
                loss: m.won === false,
                clickable: !!m.match_id,
              }"
              @click="openMatchRow(m)"
            >
              <span class="feed-result">
                {{ m.won === true ? 'W' : m.won === false ? 'L' : '·' }}
              </span>
              <div class="feed-info">
                <span class="feed-title">{{ m.title || 'Матч' }}</span>
                <span class="feed-game">{{ m.game_label || m.platform }}</span>
              </div>
              <span class="feed-kda">{{ m.subtitle }}</span>
            </div>
          </div>
        </div>

        <!-- Кланы -->
        <div class="card section-card">
          <div class="section-head">
            <h3>Топ кланов</h3>
            <RouterLink to="/clans" class="link-all">Все →</RouterLink>
          </div>
          <div v-if="clanLeaderboardLoading" class="empty-hint">Загрузка...</div>
          <div v-else-if="!clanLeaderboard.length" class="empty-block">
            <p>Пока нет активности кланов за период.</p>
            <button type="button" class="btn-ghost" @click="router.push('/clans')">
              К кланам
            </button>
          </div>
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
              <span class="clan-lb-sub">
                {{ c.members_count }} уч. ·
                {{ formatHours(c.total_two_weeks_minutes ?? c.total_minutes ?? 0) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="col-side">
        <div class="card section-card lb-card">
          <div class="section-head">
            <div>
              <h3>Мировой лидерборд</h3>
              <p class="lb-caption">Топ из открытых API</p>
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
          <div v-else-if="!leaderboard.length" class="empty-block compact">
            <p>Нет данных — API недоступен или пустой ответ.</p>
          </div>
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
                <span v-if="!entry.avatar">{{ entry.name?.[0]?.toUpperCase() || '?' }}</span>
              </div>
              <div class="lb-info">
                <span class="lb-name">{{ entry.name || 'Игрок' }}</span>
                <span class="lb-subtitle">{{ entry.subtitle || entry.team || '' }}</span>
              </div>
              <span class="lb-value" v-if="entry.value">{{ entry.value }}</span>
            </component>
          </div>
        </div>

        <div class="card social-card" v-if="auth.isAuthenticated">
          <h3>Кого взять в команду</h3>
          <div v-if="!recs.length" class="empty-block compact">
            <p>Пока некого предложить. Подключи игру и зайди позже.</p>
          </div>
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
  display: flex;
  justify-content: space-between;
  align-items: stretch;
  gap: 16px;
  flex-wrap: wrap;
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

.week-snap {
  min-width: 160px;
  max-width: 220px;
  padding: 14px 16px !important;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: border-color 0.15s;
}
.week-snap:hover { border-color: var(--accent); }
.week-snap.empty { opacity: 0.9; }
.snap-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
}
.snap-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.snap-pct {
  font-size: 28px;
  font-weight: 800;
  font-family: var(--font-mono);
  color: var(--accent);
  line-height: 1;
}
.snap-wl {
  display: flex;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  font-family: var(--font-mono);
}
.snap-wl .w { color: var(--success); }
.snap-wl .l { color: var(--danger); }
.snap-meta { font-size: 12px; color: var(--text-secondary); }
.snap-link { font-size: 11px; font-weight: 600; color: var(--accent); margin-top: auto; }
.snap-empty-text {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
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
  .week-snap { max-width: none; flex: 1; }
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
.empty-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 20px 12px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.45;
}
.empty-block.compact { padding: 14px 8px; }
.empty-block p { margin: 0; }
.lb-caption {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
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
.match-feed-item.clickable { cursor: pointer; }
.match-feed-item.clickable:hover { background: var(--bg-card-hover); }
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
  background: var(--bg-sunken);
  color: var(--text-muted);
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

@media (max-width: 900px) {
  .home-grid { grid-template-columns: 1fr; }
  .hero h1 { font-size: 18px; }
}
</style>