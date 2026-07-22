<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/axios'
import { GAMES } from '../constants/games'

const gameAccounts = ref([])
const lfgPosts = ref([])
const leaderboard = ref([])
const selectedGame = ref('Dota 2')

async function loadLeaderboard() {
  const res = await api.get('leaderboard/', { params: { game: selectedGame.value } })
  leaderboard.value = res.data
}

onMounted(async () => {
  const accountsRes = await api.get('game-accounts/')
  gameAccounts.value = accountsRes.data.results || accountsRes.data

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
      <div class="left-column">
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

        <div class="card">
          <div class="card-header"><h3>Твои игровые аккаунты</h3></div>
          <div class="accounts-list">
            <div v-for="acc in gameAccounts" :key="acc.id" class="account-item">
              <span class="platform-badge">{{ acc.platform }}</span>
              <span class="verified" v-if="acc.verified">✓ верифицирован</span>
            </div>
            <div v-if="gameAccounts.length === 0" class="empty">
              Подключи Steam или Faceit, чтобы видеть статистику
            </div>
          </div>
        </div>
      </div>

      <div class="card leaderboard-card">
        <div class="card-header">
          <h3>Топ игроков</h3>
          <select v-model="selectedGame" @change="loadLeaderboard" class="game-select-mini">
            <option v-for="g in GAMES" :key="g" :value="g">{{ g }}</option>
          </select>
        </div>
        <div class="leaderboard-list">
          <div v-for="(player, i) in leaderboard" :key="i" class="leaderboard-item">
            <span class="rank" :class="{ top: i < 3 }">{{ i + 1 }}</span>
            <RouterLink :to="`/players/${player.user_id}`" class="player-name">{{ player.username }}</RouterLink>
            <div class="player-stats">
              <span class="player-matches">{{ player.matches }} матчей</span>
              <span class="player-winrate">{{ player.winrate }}% побед</span>
            </div>
          </div>
          <div v-if="leaderboard.length === 0" class="empty">Пока нет данных по этой игре</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.leaderboard-item { display: flex; align-items: center; gap: 12px; padding: 10px 4px; border-bottom: 1px solid var(--border-color); }
.leaderboard-item:last-child { border-bottom: none; }
.rank { width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--bg-card-hover); font-size: 12px; font-weight: 700; color: var(--text-secondary); flex-shrink: 0; }
.rank.top { background: var(--accent-dim); color: var(--accent); }
.player-name { flex: 1; font-size: 13px; font-weight: 600; color: var(--text-primary); text-decoration: none; }
.player-name:hover { color: var(--accent); }
.player-stats { display: flex; flex-direction: column; align-items: flex-end; gap: 1px; }
.player-matches { font-size: 11px; color: var(--text-secondary); }
.player-winrate { font-size: 12px; color: var(--accent); font-weight: 700; }
.dashboard { display: flex; flex-direction: column; gap: 20px; }
.hero { padding: 40px; }
.hero h1 { font-size: 32px; line-height: 1.2; margin: 0 0 12px; }
.accent-text { color: var(--accent); }
.hero p { color: var(--text-secondary); margin: 0 0 24px; }
.hero-actions { display: flex; gap: 12px; }

.grid-2 { display: grid; grid-template-columns: 1fr 380px; gap: 20px; align-items: start; }
.left-column { display: flex; flex-direction: column; gap: 20px; }

.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.card-header h3 { margin: 0; font-size: 15px; }
.link { color: var(--accent); font-size: 13px; text-decoration: none; }

.lfg-item, .account-item { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--border-color); font-size: 13px; }
.lfg-item:last-child, .account-item:last-child { border-bottom: none; }
.lfg-game { font-weight: 600; }
.lfg-responses { color: var(--text-secondary); }
.platform-badge { text-transform: uppercase; font-size: 11px; font-weight: 700; color: var(--accent); }
.verified { color: var(--success); font-size: 12px; }
.empty { color: var(--text-secondary); font-size: 13px; padding: 20px 0; text-align: center; }

.game-select-mini {
  background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius-sm);
  color: var(--text-primary); font-size: 12px; padding: 6px 8px;
}

.leaderboard-list { display: flex; flex-direction: column; gap: 4px; }
.leaderboard-item { display: flex; align-items: center; gap: 12px; padding: 10px 4px; border-bottom: 1px solid var(--border-color); }
.leaderboard-item:last-child { border-bottom: none; }
.rank { width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--bg-card-hover); font-size: 12px; font-weight: 700; color: var(--text-secondary); }
.rank.top { background: var(--accent-dim); color: var(--accent); }
.player-name { flex: 1; font-size: 13px; font-weight: 600; }
.player-rating { font-size: 13px; color: var(--accent); font-weight: 700; }
</style>