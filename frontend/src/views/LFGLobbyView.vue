<!-- src/views/LFGLobbyView.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/axios'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const post = ref(null)
const responders = ref([])
const loading = ref(true)
const error = ref(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    const res = await api.get(`lfg-posts/${route.params.id}/`)
    post.value = res.data
    if (auth.isAuthenticated) {
      const respRes = await api.get('lfg-responses/', { params: { post: route.params.id } })
      responders.value = respRes.data.results || respRes.data
    }
  } catch (e) {
    error.value =
      e.response?.status === 404 ? 'Заявка не найдена или закрыта' : 'Не удалось загрузить'
  } finally {
    loading.value = false
  }
}

async function kick(responseId) {
  if (!confirm('Убрать этого игрока из заявки?')) return
  try {
    await api.delete(`lfg-responses/${responseId}/`)
    await load()
  } catch (e) {
    alert(e.response?.data?.detail || 'Не удалось убрать игрока')
  }
}

function viewProfile(userId) {
  router.push(`/players/${userId}`)
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="state">Загрузка...</div>
  <div v-else-if="error" class="state error">{{ error }}</div>

  <div class="lobby-page" v-else-if="post">
    <h1>{{ post.game }} — Лобби</h1>
    <p>{{ post.description }}</p>

    <div v-if="!auth.isAuthenticated" class="hint">
      <button type="button" class="login-link" @click="auth.loginWithSteam()">
        Войди через Steam
      </button>
      , чтобы видеть участников
    </div>

    <div v-else class="responders-list">
      <div v-if="!responders.length" class="state">Пока никто не откликнулся</div>
      <div v-for="r in responders" :key="r.id" class="responder-item">
        <span class="responder-name" @click="viewProfile(r.user_id ?? r.user)">
          {{ r.username ?? r.user }}
        </span>
        <button v-if="post.is_author" type="button" class="kick-btn" @click="kick(r.id)">
          Кикнуть
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.lobby-page { display: flex; flex-direction: column; gap: 12px; }
.state { color: var(--text-secondary); padding: 24px 0; }
.state.error { color: var(--danger); }
.hint { color: var(--text-secondary); font-size: 13px; }
.login-link {
  background: none; border: none; color: var(--accent);
  font-weight: 600; cursor: pointer; padding: 0;
}
.responders-list { display: flex; flex-direction: column; gap: 6px; }
.responder-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; background: var(--bg-card);
  border: 1px solid var(--border-color); border-radius: var(--radius-sm);
}
.responder-name { cursor: pointer; font-weight: 600; }
.responder-name:hover { color: var(--accent); }
.kick-btn {
  background: none; border: 1px solid var(--danger); color: var(--danger);
  border-radius: var(--radius-sm); padding: 4px 10px; cursor: pointer; font-size: 12px;
}
</style>