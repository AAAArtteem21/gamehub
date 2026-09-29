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

const route = useRoute()
const posts = ref([])
const loading = ref(true)
const loadingMore = ref(false)
const nextPageUrl = ref(null)
const error = ref(null)
const showCreateModal = ref(false)
const chatPost = ref(null)
const chatSidebarRef = ref(null)

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
    // тихо игнорируем — юзер может просто попробовать ещё раз
  } finally {
    loadingMore.value = false
  }
}

async function respond(postId) {
  await lfgApi.respond(postId)
  const post = posts.value.find(p => p.id === postId)
  if (post) {
    post.responses_count += 1
    post.has_responded = true
  }
  chatSidebarRef.value?.loadThreads()
}

function onPostCreated(newPost) {
  posts.value.unshift(newPost)
}

function openChat(threadOrPost) {
  chatPost.value = { id: threadOrPost.post_id ?? threadOrPost.id, game: threadOrPost.game }
}

function closeChat() {
  chatPost.value = null
  chatSidebarRef.value?.loadThreads()
}

onMounted(() => {
  if (route.query.search) searchTerm.value = route.query.search
  loadPosts()
})
</script>

<template>
  <div class="lfg-page">
    <div class="page-header">
      <div>
        <h1>Поиск тиммейтов</h1>
        <p class="subtitle">Заявки от игроков с верифицированной статистикой</p>
      </div>
      <button class="btn-primary" @click="showCreateModal = true">+ Создать заявку</button>
    </div>

    <NotificationsPanel />

    <div class="filters-wrap">
      <div class="filters">
        <button class="filter-chip" :class="{ active: gameFilter === '' }" @click="gameFilter = ''; loadPosts()">
          Все игры
        </button>
        <button v-for="g in GAMES" :key="g" class="filter-chip" :class="{ active: gameFilter === g }" @click="gameFilter = g; loadPosts()">
          <GameIcon :game="g" :size="18" />
          {{ g }}
        </button>
      </div>
    </div>

    <div class="content-grid">
      <div class="feed-column">
        <div v-if="loading" class="state-message">Загружаем заявки...</div>
        <div v-else-if="error" class="state-message error-state">
          {{ error }}
          <button class="retry-btn" @click="loadPosts">Повторить</button>
        </div>
        <div v-else-if="posts.length === 0" class="state-message empty-state">
          <p>Пока нет активных заявок{{ gameFilter ? ` по ${gameFilter}` : '' }}.</p>
          <button class="btn-primary" @click="showCreateModal = true">Создать первую заявку</button>
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
          class="load-more-btn"
          @click="loadMore"
          :disabled="loadingMore"
        >
          {{ loadingMore ? 'Загружаем...' : 'Загрузить ещё' }}
        </button>
      </div>

      <ChatSidebar ref="chatSidebarRef" @open-thread="openChat" />
    </div>

    <CreatePostModal v-if="showCreateModal" @close="showCreateModal = false" @created="onPostCreated" />
    <ChatModal v-if="chatPost" :post="chatPost" @close="closeChat" />
  </div>
</template>

<style scoped>
.lfg-page { display: flex; flex-direction: column; gap: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.page-header h1 { margin: 0 0 4px; font-size: 24px; }
.subtitle { margin: 0; color: var(--text-secondary); font-size: 14px; }

.filters {
  display: flex; gap: 8px; overflow-x: auto; padding-bottom: 6px;
  scrollbar-width: thin;
}
.filter-chip { flex-shrink: 0; }
.filter-chip:hover { color: var(--text-primary); }
.filter-chip.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

.content-grid { display: grid; grid-template-columns: 1fr 320px; gap: 20px; align-items: start; }
.feed-column { display: flex; flex-direction: column; gap: 20px; min-width: 0; }
.posts-list { display: flex; flex-direction: column; gap: 12px; }

.state-message { padding: 60px 20px; text-align: center; color: var(--text-secondary); background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); }
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 16px; }
.error-state { color: var(--danger); display: flex; flex-direction: column; align-items: center; gap: 12px; }
.retry-btn { background: var(--bg-card-hover); border: 1px solid var(--border-color); color: var(--text-primary); padding: 8px 16px; border-radius: var(--radius-sm); cursor: pointer; }

.load-more-btn {
  background: var(--bg-card-hover);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 12px;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.2s var(--ease);
}
.load-more-btn:hover:not(:disabled) { border-color: var(--border-hover); }
.load-more-btn:disabled { opacity: 0.6; cursor: default; }
.filters-wrap {
  position: relative;
}
.filters {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 4px 2px 10px;
  scrollbar-width: thin;
  scrollbar-color: var(--border-hover) transparent;
}
.filters::-webkit-scrollbar { height: 5px; }
.filters::-webkit-scrollbar-thumb { background: var(--border-hover); border-radius: 10px; }

.filter-chip {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-shrink: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 7px 16px 7px 10px;
  border-radius: 20px;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s var(--ease);
}
.filter-chip:hover {
  color: var(--text-primary);
  border-color: var(--border-hover);
  transform: translateY(-1px);
}
.filter-chip.active {
  background: linear-gradient(135deg, var(--accent-dim), rgba(230, 57, 70, 0.06));
  border-color: var(--accent);
  color: var(--accent);
  box-shadow: 0 2px 10px rgba(230, 57, 70, 0.15);
}

/* лёгкое затухание по краям, намекает что список скроллится */
.filters-wrap::before, .filters-wrap::after {
  content: '';
  position: absolute;
  top: 0; bottom: 10px;
  width: 24px;
  pointer-events: none;
  z-index: 1;
}
.filters-wrap::before {
  left: 0;
  background: linear-gradient(90deg, var(--bg-primary), transparent);
}
.filters-wrap::after {
  right: 0;
  background: linear-gradient(270deg, var(--bg-primary), transparent);
}

@media (max-width: 900px) {
  .content-grid { grid-template-columns: 1fr; }
}
</style>