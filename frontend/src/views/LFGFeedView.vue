<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { lfgApi } from '../api/lfg'
import LFGCard from '../components/lfg/LFGCard.vue'
import CreatePostModal from '../components/lfg/CreatePostModal.vue'
import ChatModal from '../components/lfg/ChatModal.vue'
import ChatSidebar from '../components/chat/ChatSidebar.vue'
import NotificationsPanel from '../components/lfg/NotificationsPanel.vue'
import { GAMES } from '../constants/games'
import GameIcon from '../components/lfg/GameIcon.vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const posts = ref([])
const loading = ref(true)
const loadingMore = ref(false)
const nextPageUrl = ref(null)
const error = ref(null)
const showCreateModal = ref(false)
const chatPost = ref(null)
const chatSidebarRef = ref(null)
const authStore = useAuthStore()
const gameFilter = ref('')
const searchTerm = ref('')

async function loadPosts() {
  loading.value = true
  error.value = null
  try {
    const params = {}
    if (gameFilter.value) params.game = gameFilter.value
    if (searchTerm.value) params.search = searchTerm.value
    const res = await lfgApi.list(params)
    posts.value = res.data.results || res.data
    nextPageUrl.value = res.data.next || null
  } catch (e) {
    error.value = 'Не удалось загрузить заявки. Проверь подключение к серверу.'
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  if (!nextPageUrl.value || loadingMore.value) return
  loadingMore.value = true
  try {
    const res = await lfgApi.listByUrl(nextPageUrl.value)
    posts.value.push(...(res.data.results || []))
    nextPageUrl.value = res.data.next || null
  } catch (e) {
    /* */
  } finally {
    loadingMore.value = false
  }
}

function openCreate() {
  if (authStore.requireAuth('Войди через Steam, чтобы создать заявку.')) {
    showCreateModal.value = true
  }
}


async function respond(postId) {
  if (!authStore.requireAuth('Войди через Steam, чтобы откликнуться.')) return false
  await lfgApi.respond(postId)
  const post = posts.value.find((p) => p.id === postId)
  if (post) {
    post.responses_count += 1
    post.has_responded = true
  }
  chatSidebarRef.value?.loadThreads()
  return true
}

function onPostCreated(newPost) {
  posts.value.unshift(newPost)
}

function openChat(threadOrPost) {
  chatPost.value = {
    id: threadOrPost.post_id ?? threadOrPost.id,
    game: threadOrPost.game,
  }
}

function closeChat() {
  chatPost.value = null
  chatSidebarRef.value?.loadThreads()
}

function setFilter(g) {
  gameFilter.value = g
  loadPosts()
}

onMounted(() => {
  if (route.query.search) searchTerm.value = route.query.search
  loadPosts()
  if (route.query.create) openCreate()
})
</script>

<template>
  <div class="lfg-page">
    <div class="page-header">
      <div>
        <h1>Поиск тиммейтов</h1>
        <p class="subtitle">Заявки от игроков с верифицированной статистикой</p>
      </div>
      <button type="button" class="btn-primary" @click="showCreateModal = true">
        + Создать заявку
      </button>
    </div>

    <NotificationsPanel v-if="authStore.isAuthenticated" />

    <div class="filters-wrap">
      <div class="filters">
        <button
          type="button"
          class="filter-chip"
          :class="{ active: gameFilter === '' }"
          @click="setFilter('')"
        >
          Все игры
        </button>
        <button
          v-for="g in GAMES"
          :key="g"
          type="button"
          class="filter-chip"
          :class="{ active: gameFilter === g }"
          @click="setFilter(g)"
        >
          <GameIcon :game="g" :size="16" />
          {{ g }}
        </button>
      </div>
    </div>

    <div class="content-grid">
      <div class="feed-column">
        <div v-if="loading" class="state-message">Загружаем заявки...</div>
        <div v-else-if="error" class="state-message error-state">
          {{ error }}
          <button type="button" class="retry-btn" @click="loadPosts">Повторить</button>
        </div>
        <div v-else-if="posts.length === 0" class="state-message empty-state">
          <p>Пока нет активных заявок{{ gameFilter ? ` по ${gameFilter}` : '' }}.</p>
          <button type="button" class="btn-primary" @click="showCreateModal = true">
            Создать первую заявку
          </button>
        </div>
        <div v-else class="posts-list">
          <LFGCard
            v-for="post in posts"
            :key="post.id"
            :post="post"
            :on-respond="respond"
            @open-chat="openChat"
          />
        </div>
        <button
          v-if="nextPageUrl"
          type="button"
          class="load-more-btn"
          :disabled="loadingMore"
          @click="loadMore"
        >
          {{ loadingMore ? 'Загружаем...' : 'Загрузить ещё' }}
        </button>
      </div>

      <ChatSidebar v-if="authStore.isAuthenticated" ref="chatSidebarRef" @open-thread="openChat" />
    </div>

    <CreatePostModal
      v-if="showCreateModal"
      @close="showCreateModal = false"
      @created="onPostCreated"
    />
    <ChatModal v-if="chatPost" :post="chatPost" @close="closeChat" />
  </div>
</template>

<style scoped>
.lfg-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}
.page-header h1 {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 600;
}
.subtitle {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
}

.filters-wrap {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
}
.filters {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding: 2px 0;
  scrollbar-width: thin;
  scrollbar-color: var(--border-hover) transparent;
}
.filters::-webkit-scrollbar { height: 6px; }
.filters::-webkit-scrollbar-track { background: transparent; }
.filters::-webkit-scrollbar-thumb {
  background: var(--border-hover);
  border-radius: 3px;
}
.filter-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  background: var(--bg-card-hover);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 7px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.18s ease;
}
.filter-chip:hover {
  color: var(--text-primary);
  border-color: var(--border-hover);
  transform: translateY(-1px);
}
.filter-chip.active {
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dim) 100%);
  border-color: transparent;
  color: var(--bg-page, #0d1117);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.35);
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 16px;
  align-items: start;
}
.feed-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
.posts-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.state-message {
  padding: 48px 20px;
  text-align: center;
  color: var(--text-secondary);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}
.error-state {
  color: var(--danger);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.retry-btn {
  background: var(--bg-card-hover);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.load-more-btn {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 10px;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
}
.load-more-btn:hover:not(:disabled) { border-color: var(--border-hover); }
.load-more-btn:disabled { opacity: 0.55; cursor: default; }

@media (max-width: 900px) {
  .content-grid { grid-template-columns: 1fr; }
  .page-header h1 { font-size: 18px; }
}
</style>
