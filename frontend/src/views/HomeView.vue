<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/axios'

const lfgPosts = ref([])
const leaderboard = ref([])
const leaderboardLoading = ref(true)
const selectedGame = ref('dota2')

const worldGames = [
  { value: 'dota2', label: 'Dota 2' },
  { value: 'lol', label: 'League of Legends' },
]

async function loadLeaderboard() {
  leaderboardLoading.value = true
  try {
    const res = await api.get('world-leaderboard/', { params: { game: selectedGame.value } })
    leaderboard.value = res.data
  } catch (e) {
    leaderboard.value = []
  } finally {
    leaderboardLoading.value = false
  }
}

onMounted(async () => {
  const lfgRes = await api.get('lfg-posts/')
  lfgPosts.value = (lfgRes.data.results || lfgRes.data).slice(0, 5)
  await loadLeaderboard()
})
</script>

<template>
  <div class="dashboard">
    <div class="hero card">
      <h1>Найди свою<br /><span class="accent-text">идеальную команду</span></h1>
      <p>Играй с теми, кто подходит по стилю и рангу. Никаких выдуманных профилей.</p>
      <div class="hero-actions">
        <RouterLink to="/lfg" class="btn-primary">Найти тиммейтов</RouterLink>
        <RouterLink to="/lfg" class="btn-secondary">Создать заявку</RouterLink>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-header">
          <h3>Последние заявки LFG</h3>
          <RouterLink to="/lfg" class="link">Все →</RouterLink>
        </div>
        <div class="lfg-list">
          <div v-for="post in lfgPosts" :key="post.id" class="lfg-item">
            <div class="lfg-game">{{ post.game }}</div>
            <div class="lfg-desc">{{ post.description || 'Без описания' }}</div>
            <div class="lfg-responses">{{ post.responses_count }} откликов</div>
          </div>
          <div v-if="lfgPosts.length === 0" class="empty">Пока нет активных заявок</div>
        </div>
      </div>

      <div class="card leaderboard-card">
        <div class="leaderboard-header">
          <div class="leaderboard-title-block">
            <h3>🌍 Мировой лидерборд</h3>
            <span class="leaderboard-sub">Топ игроков планеты — не только с GameHub</span>
          </div>
          <div class="game-tabs">
            <button
              v-for="g in worldGames" :key="g.value"
              class="game-tab" :class="{ active: selectedGame === g.value }"
              @click="selectedGame = g.value; loadLeaderboard()"
            >
              {{ g.label }}
            </button>
          </div>
        </div>

        <div v-if="leaderboardLoading" class="lb-state">Загружаем лидерборд...</div>
        <div v-else-if="leaderboard.length === 0" class="lb-state">Данные временно недоступны</div>

        <div v-else class="leaderboard-list">
          <component
            :is="entry.guest_link ? 'RouterLink' : 'div'"
            v-for="(entry, i) in leaderboard" :key="entry.external_id"
            :to="entry.guest_link"
            class="leaderboard-item"
            :class="{ clickable: entry.guest_link }"
          >
            <span class="rank" :class="{ gold: i === 0, silver: i === 1, bronze: i === 2 }">{{ i + 1 }}</span>
            <div class="lb-avatar" :style="entry.avatar ? { backgroundImage: `url(${entry.avatar})` } : {}">
              <span v-if="!entry.avatar">{{ entry.name?.[0]?.toUpperCase() }}</span>
            </div>
            <div class="lb-info">
              <span class="lb-name">{{ entry.name }}</span>
              <span class="lb-subtitle">{{ entry.subtitle }}</span>
            </div>
            <span class="lb-value" v-if="entry.value">{{ entry.value }}</span>
          </component>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 20px; }
.hero { padding: 40px; }
.hero h1 { font-size: 32px; line-height: 1.2; margin: 0 0 12px; }
.accent-text { color: var(--accent); }
.hero p { color: var(--text-secondary); margin: 0 0 24px; }
.hero-actions { display: flex; gap: 12px; }

.grid-2 { display: grid; grid-template-columns: 1fr 420px; gap: 20px; align-items: start; }

.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.card-header h3 { margin: 0; font-size: 15px; }
.link { color: var(--accent); font-size: 13px; text-decoration: none; }

.lfg-item { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--border-color); font-size: 13px; }
.lfg-item:last-child { border-bottom: none; }
.lfg-game { font-weight: 600; }
.lfg-responses { color: var(--text-secondary); }
.empty { color: var(--text-secondary); font-size: 13px; padding: 20px 0; text-align: center; }

.leaderboard-card { padding: 0; overflow: hidden; }
.leaderboard-header {
  padding: 18px 20px 14px;
  background: linear-gradient(135deg, var(--accent-dim), transparent);
  border-bottom: 1px solid var(--border-color);
}
.leaderboard-title-block h3 { margin: 0 0 2px; font-size: 16px; }
.leaderboard-sub { font-size: 11px; color: var(--text-secondary); }

.game-tabs { display: flex; gap: 6px; margin-top: 12px; }
.game-tab {
  background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-secondary);
  font-size: 12px; font-weight: 600; padding: 6px 14px; border-radius: 20px; cursor: pointer;
  transition: all 0.2s var(--ease);
}
.game-tab:hover { color: var(--text-primary); }
.game-tab.active { background: var(--accent); color: white; border-color: var(--accent); }

.lb-state { padding: 40px 20px; text-align: center; color: var(--text-secondary); font-size: 13px; }

.leaderboard-list { display: flex; flex-direction: column; padding: 8px; }
.leaderboard-item {
  display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: var(--radius-sm);
  text-decoration: none; color: inherit; transition: background 0.15s var(--ease);
}
.leaderboard-item.clickable { cursor: pointer; }
.leaderboard-item.clickable:hover { background: var(--bg-card-hover); }

.rank {
  width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 800; background: var(--bg-card-hover); color: var(--text-secondary); flex-shrink: 0;
}
.rank.gold { background: linear-gradient(135deg, #FFD700, #FFA500); color: #1a1a1a; }
.rank.silver { background: linear-gradient(135deg, #E0E0E0, #B0B0B0); color: #1a1a1a; }
.rank.bronze { background: linear-gradient(135deg, #CD7F32, #A0522D); color: white; }

.lb-avatar {
  width: 34px; height: 34px; border-radius: 50%; background-color: var(--accent-dim); background-size: cover; background-position: center;
  display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; color: var(--accent); flex-shrink: 0;
}

.lb-info { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.lb-name { font-size: 13px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lb-subtitle { font-size: 11px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lb-value { font-size: 13px; font-weight: 700; color: var(--accent); flex-shrink: 0; }
</style>