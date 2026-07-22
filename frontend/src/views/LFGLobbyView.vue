<!-- src/views/LFGLobbyView.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { lfgApi } from '../api/lfg'
import api from '../api/axios'

const route = useRoute()
const router = useRouter()
const post = ref(null)
const responders = ref([])
const loading = ref(true)

async function load() {
  const res = await lfgApi.list() // временно; лучше сделать lfgApi.detail(id)
  post.value = res.data.results?.find(p => p.id == route.params.id) || res.data.find(p => p.id == route.params.id)
  const respRes = await api.get('lfg-responses/', { params: { post: route.params.id } })
  responders.value = respRes.data.results || respRes.data
  loading.value = false
}

async function kick(userId) {
  if (!confirm('Убрать этого игрока из заявки?')) return
  await api.delete(`lfg-responses/${userId}/`) // потребует doработки бэкенда под удаление по user+post
  load()
}

function viewProfile(userId) {
  router.push(`/players/${userId}`)
}

onMounted(load)
</script>

<template>
  <div class="lobby-page" v-if="!loading && post">
    <h1>{{ post.game }} — Лобби</h1>
    <p>{{ post.description }}</p>
    <div class="responders-list">
      <div v-for="r in responders" :key="r.id" class="responder-item">
        <span @click="viewProfile(r.user)" class="responder-name">{{ r.user }}</span>
        <button v-if="post.is_author" @click="kick(r.user)" class="kick-btn">Кикнуть</button>
      </div>
    </div>
  </div>
</template>