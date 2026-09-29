<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/axios'
import ClanIcon from '../components/clans/ClanIcon.vue'

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
watch(recentMatchesPlatform, loadRecentMatches)

onMounted(() => {
  loadLfg()
  loadLeaderboard()
  loadClanLeaderboard()
  loadRecentMatches()
  loadSocialBlocks()
})
</script>

<template>
  <div class="home">
    <!-- Hero -->
    <div class="hero card">
      <h1>
        Найди свою<br />
        <span class="accent">идеальную команду</span>
      </h1>
      <p class="hero-sub">
        Играй с теми, кто подходит по стилю и рангу. Никаких выдуманных профилей.
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
      <!-- Left column -->
      <div class="col-main">
        <!-- LFG -->
        <div class="card section-card">
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

        <!-- Recent matches -->
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

        <!-- Clan leaderboard -->
        <div class="card section-card">
          <div class="section-head">
            <h3>🏆 Топ кланов по активности за месяц</h3>
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
            <ClanIcon :clan="c" :size="36" />
            <div class="clan-lb-info">
              <span class="clan-lb-name">{{ c.name }}</span>
              <span class="clan-lb-sub">{{ c.members_count }} участников</span>
            </div>
            <span class="clan-lb-val">{{ formatMinutes(c.total_month_minutes) }}</span>
          </div>
        </div>
      </div>

      <!-- Right column -->
      <div class="col-side">
        <!-- World leaderboard -->
        <div class="card section-card lb-card">
          <div class="section-head">
            <div>
              <h3>🌐 Мировой лидерборд</h3>
              <p class="lb-caption">Топ игроков планеты — не только с GameEyes</p>
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

        <!-- Recommendations -->
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
.home { display: flex; flex-direction: column; gap: 20px; }

.hero {
  padding: 28px 32px;
  background: linear-gradient(135deg, var(--bg-card) 0%, rgba(232, 64, 87, 0.08) 100%);
}
.hero h1 { margin: 0 0 10px; font-size: 28px; line-height: 1.2; }
.accent { color: var(--accent); }
.hero-sub { margin: 0 0 18px; color: var(--text-secondary); max-width: 480px; }
.hero-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.btn-primary {
  background: var(--accent); color: #fff; border: none;
  padding: 10px 18px; border-radius: 10px; font-weight: 700; cursor: pointer;
}
.btn-ghost {
  background: transparent; border: 1px solid var(--border-color); color: var(--text-primary);
  padding: 10px 18px; border-radius: 10px; font-weight: 600; cursor: pointer;
}

.home-grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 20px;
  align-items: start;
}
@media (max-width: 960px) {
  .home-grid { grid-template-columns: 1fr; }
}

.section-card, .social-card { display: flex; flex-direction: column; gap: 10px; }
.section-head {
  display: flex; justify-content: space-between; align-items: center; gap: 8px;
}
.section-head h3, .social-card h3 { margin: 0; font-size: 15px; }
.link-all { font-size: 13px; color: var(--accent); text-decoration: none; font-weight: 600; }
.empty-hint { color: var(--text-secondary); font-size: 13px; padding: 12px 0; text-align: center; }
.lb-caption { margin: 4px 0 0; font-size: 11px; color: var(--text-secondary); }

.lfg-row {
  display: flex; justify-content: space-between; align-items: center; gap: 12px;
  padding: 10px 8px; border-radius: 8px; cursor: pointer;
}
.lfg-row:hover { background: var(--bg-card-hover); }
.lfg-left { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.lfg-game { font-size: 11px; color: var(--accent); font-weight: 700; }
.lfg-title { font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lfg-meta { font-size: 12px; color: var(--text-secondary); flex-shrink: 0; }

.match-feed { display: flex; flex-direction: column; gap: 4px; }
.match-feed-item {
  display: flex; align-items: center; gap: 10px; padding: 9px 8px; border-radius: 8px;
}
.feed-result {
  width: 22px; height: 22px; border-radius: 6px; display: flex; align-items: center;
  justify-content: center; font-size: 11px; font-weight: 800; flex-shrink: 0;
}
.match-feed-item.win .feed-result { background: rgba(74,222,128,0.15); color: var(--success); }
.match-feed-item.loss .feed-result { background: rgba(248,113,113,0.15); color: var(--danger); }
.feed-info { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.feed-title { font-size: 13px; font-weight: 700; }
.feed-game { font-size: 11px; color: var(--text-secondary); }
.feed-kda { font-size: 12px; font-family: monospace; color: var(--text-secondary); }

.platform-select-mini {
  background: var(--bg-primary); border: 1px solid var(--border-color);
  border-radius: var(--radius-sm); color: var(--text-secondary);
  font-size: 11px; padding: 4px 8px; cursor: pointer;
}

.period { font-size: 12px; color: var(--text-secondary); margin: 0; }
.weekly-line { margin: 0; font-size: 14px; }
.w { color: var(--success); font-weight: 800; }
.l { color: var(--danger); font-weight: 800; }
.streak { margin: 0; font-size: 13px; color: var(--text-secondary); }

.clan-lb-row {
  display: flex; align-items: center; gap: 10px; padding: 8px 4px;
  border-radius: 8px; cursor: pointer;
}
.clan-lb-row:hover { background: var(--bg-card-hover); }
.clan-lb-info { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.clan-lb-name { font-weight: 700; font-size: 13px; }
.clan-lb-sub { font-size: 11px; color: var(--text-secondary); }
.clan-lb-val { font-weight: 700; color: var(--accent); font-size: 13px; }

.rank {
  width: 22px; text-align: center; font-weight: 800; font-size: 13px; color: var(--text-secondary);
}
.rank.gold { color: #f0c75e; }
.rank.silver { color: #c0c0c0; }
.rank.bronze { color: #cd7f32; }

.game-tabs { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.game-tab {
  background: none; border: 1px solid var(--border-color); color: var(--text-secondary);
  font-size: 11px; font-weight: 700; padding: 5px 10px; border-radius: 20px; cursor: pointer;
}
.game-tab.active { background: var(--accent); color: #fff; border-color: var(--accent); }

.leaderboard-list { display: flex; flex-direction: column; gap: 2px; max-height: 520px; overflow-y: auto; }
.leaderboard-item {
  display: flex; align-items: center; gap: 10px; padding: 8px 6px;
  border-radius: 8px; text-decoration: none; color: inherit;
}
.leaderboard-item.clickable { cursor: pointer; }
.leaderboard-item.clickable:hover { background: var(--bg-card-hover); }
.lb-avatar {
  width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
  background-color: var(--bg-card-hover); background-size: cover; background-position: center;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 800; color: var(--text-muted);
}
.lb-info { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.lb-name {
  font-size: 13px; font-weight: 700;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.lb-subtitle {
  font-size: 11px; color: var(--text-secondary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.lb-value { font-size: 13px; font-weight: 700; color: var(--accent); flex-shrink: 0; }

.rec-row {
  display: flex; align-items: center; gap: 10px; padding: 8px 0;
  border-bottom: 1px solid var(--border-color); text-decoration: none; color: inherit;
}
.rec-row:last-child { border-bottom: none; }
.rec-avatar {
  width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
  background-color: var(--accent-dim); background-size: cover; background-position: center;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 800; color: var(--accent);
}
.rec-info { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.rec-name { font-weight: 700; font-size: 13px; }
.rec-meta { font-size: 11px; color: var(--text-secondary); }
.lfg-tag {
  font-size: 10px; font-weight: 800; color: var(--accent);
  background: var(--accent-dim); padding: 2px 8px; border-radius: 20px;
}
</style>