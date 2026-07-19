<!-- src/views/PublicProfileView.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api/axios'

const route = useRoute()
const profile = ref(null)
const loading = ref(true)
const error = ref(null)

const platformLabels = { steam: 'Steam', faceit: 'Faceit', opendota: 'OpenDota' }

async function load() {
  loading.value = true
  error.value = null
  try {
    const res = await api.get(`players/${route.params.id}/`)
    profile.value = res.data
  } catch (e) {
    error.value = 'Не удалось загрузить профиль игрока'
  } finally {
    loading.value = false
  }
}

function allGamesFlat() {
  if (!profile.value) return []
  const rows = []
  for (const acc of profile.value.accounts) {
    for (const s of acc.snapshots || []) {
      rows.push({ ...s, platform: acc.platform })
    }
  }
  return rows.sort((a, b) => b.playtime_forever - a.playtime_forever)
}

onMounted(load)
</script>

<template>
  <div class="public-profile" v-if="!loading && profile">
    <div class="profile-header card">
      <div class="avatar-big" :style="profile.avatar_url ? { backgroundImage: `url(${profile.avatar_url})` } : {}"></div>
      <div>
        <h1>{{ profile.display_name || profile.username }}</h1>
      </div>
    </div>

    <div class="card games-table-card" v-if="allGamesFlat().length">
      <table class="games-table">
        <thead>
          <tr><th>Игра</th><th>Платформа</th><th>Часы всего</th></tr>
        </thead>
        <tbody>
          <tr v-for="row in allGamesFlat()" :key="row.id">
            <td class="game-cell">{{ row.game_name }}</td>
            <td><span class="platform-tag">{{ platformLabels[row.platform] }}</span></td>
            <td class="hours-cell">{{ Math.round(row.playtime_forever / 60) }}ч</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="state-message">У игрока пока нет подключённой статистики</div>
  </div>

  <div v-else-if="loading" class="state-message">Загружаем профиль...</div>
  <div v-else class="state-message error-state">{{ error }}</div>
</template>

<style scoped>
.public-profile { display: flex; flex-direction: column; gap: 20px; }
.profile-header { display: flex; align-items: center; gap: 20px; }
.avatar-big { width: 72px; height: 72px; border-radius: 50%; background: var(--accent-dim); background-size: cover; border: 3px solid var(--accent); flex-shrink: 0; }
.profile-header h1 { margin: 0; font-size: 22px; }
.games-table-card { padding: 0; overflow: hidden; }
.games-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.games-table th { text-align: left; padding: 12px 16px; color: var(--text-secondary); font-weight: 600; border-bottom: 1px solid var(--border-color); font-size: 11px; text-transform: uppercase; }
.games-table td { padding: 12px 16px; border-bottom: 1px solid var(--border-color); }
.games-table tr:last-child td { border-bottom: none; }
.game-cell { font-weight: 600; }
.platform-tag { font-size: 11px; color: var(--accent); font-weight: 700; text-transform: uppercase; }
.hours-cell { font-weight: 600; }
.state-message { padding: 60px 20px; text-align: center; color: var(--text-secondary); background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); }
.error-state { color: var(--danger); }
</style>