<!-- src/components/lfg/NotificationsPanel.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import api from '../../api/axios'

const notifications = ref([])

function timeLeft(expiresAt) {
  const diff = new Date(expiresAt) - new Date()
  if (diff <= 0) return 'истекло'
  const min = Math.floor(diff / 1000 / 60)
  return `${min} мин осталось`
}

onMounted(async () => {
  const res = await api.get('lfg-notifications/')
  notifications.value = res.data
})
</script>

<template>
  <div class="notif-panel card" v-if="notifications.length">
    <h3>Открытые контакты</h3>
    <div v-for="n in notifications" :key="n.post_id" class="notif-item">
      <span class="notif-game">{{ n.game }}</span>
      <span class="notif-contact">{{ n.contact }}</span>
      <span class="notif-time">{{ timeLeft(n.expires_at) }}</span>
    </div>
  </div>
</template>

<style scoped>
.notif-panel { display: flex; flex-direction: column; gap: 10px; }
.notif-panel h3 { margin: 0; font-size: 14px; }
.notif-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border-color); font-size: 12px; }
.notif-item:last-child { border-bottom: none; }
.notif-game { font-weight: 700; }
.notif-contact { color: var(--success); }
.notif-time { color: var(--text-muted); font-size: 11px; }
</style>