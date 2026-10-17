<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
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
const myApps = ref([])
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
const hideResponded = ref(false)
const filtersEl = ref(null)
let searchTimer = null

const visiblePosts = computed(() =>
  hideResponded.value ? posts.value.filter((p) => !p.has_responded) : posts.value
)

const hasActiveFilters = computed(
  () => !!(gameFilter.value || searchTerm.value.trim() || hideResponded.value)
)

async function loadPosts() {
  loading.value = true
  error.value = null
  try {
    const params = {}
    if (gameFilter.value) params.game = gameFilter.value
    if (searchTerm.value.trim()) params.search = searchTerm.value.trim()
    const res = await lfgApi.list(params)
    posts.value = res.data.results || res.data
    nextPageUrl.value = res.data.next || null
  } catch (e) {
    error.value = 'Не удалось загрузить заявки. Проверь подключение к серверу.'
  } finally {
    loading.value = false
  }
}

async function loadMyApps() {
  if (!authStore.isAuthenticated) {
    myApps.value = []
    return
  }
  try {
    const res = await lfgApi.myApplications()
    myApps.value = res.data || []
  } catch {
    myApps.value = []
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
  if (!authStore.requireAuth('Войди через Steam, чтобы подать заявку.')) return false
  await lfgApi.respond(postId)
  const post = posts.value.find((p) => p.id === postId)
  if (post) {
    post.has_responded = true
    post.my_response_status = 'pending'
    post.pending_count = (post.pending_count || 0) + 1
  }
  await loadMyApps()
  chatSidebarRef.value?.loadThreads()
  return true
}

function onPostCreated(newPost) {
  posts.value.unshift(newPost)
}

function openChat(threadOrPost) {
  chatPost.value = {
    id: threadOrPost.post_id ?? threadOrPost.id ?? threadOrPost.post,
    game: threadOrPost.game ?? threadOrPost.post_game,
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

function resetFilters() {
  gameFilter.value = ''
  searchTerm.value = ''
  hideResponded.value = false
  loadPosts()
}

function scrollFilters(dir) {
  filtersEl.value?.scrollBy({ left: dir * 280, behavior: 'smooth' })
}

function formatAppWhen(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('ru-RU', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

watch(searchTerm, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadPosts, 350)
})

onMounted(() => {
  if (route.query.search) searchTerm.value = route.query.search
  loadPosts()
  loadMyApps()
  if (route.query.create) openCreate()
})

onUnmounted(() => clearTimeout(searchTimer))
</script>

<template>
  <div class="lfg-page">
    <!-- Шапка -->
    <div class="page-header">
      <div class="title-block">
        <h1>
          <svg class="h-ico" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          Поиск тиммейтов
          <span class="count-pill" v-if="!loading && !error">
            {{ visiblePosts.length }}<template v-if="nextPageUrl">+</template>
          </span>
        </h1>
        <p class="subtitle">Заявки от игроков с верифицированной статистикой</p>
      </div>
      <button type="button" class="btn-primary" @click="openCreate">+ Создать заявку</button>
    </div>

    <NotificationsPanel v-if="authStore.isAuthenticated" />

    <!-- Поиск и фильтры -->
    <div class="filters-wrap">
      <div class="filters-top">
        <div class="search-wrap">
          <svg class="search-ico" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input
            v-model="searchTerm"
            class="lfg-search"
            placeholder="Поиск по заявкам..."
            autocomplete="off"
          />
          <button
            v-if="searchTerm"
            type="button"
            class="search-clear"
            aria-label="Очистить"
            @click="searchTerm = ''"
          >✕</button>
        </div>

        <label class="toggle" :class="{ on: hideResponded }">
          <input type="checkbox" v-model="hideResponded" />
          <span class="toggle-box" />
          Скрыть мои заявки
        </label>

        <button v-if="hasActiveFilters" type="button" class="reset-btn" @click="resetFilters">
          Сбросить
        </button>
      </div>

      <div class="games-row">
        <button type="button" class="arrow" aria-label="Назад" @click="scrollFilters(-1)">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>
        </button>

        <div class="filters" ref="filtersEl">
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

        <button type="button" class="arrow" aria-label="Вперёд" @click="scrollFilters(1)">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg>
        </button>
      </div>
    </div>

    <div class="content-grid">
      <div class="feed-column">
        <!-- Скелетоны -->
        <div v-if="loading" class="posts-list">
          <div v-for="n in 3" :key="n" class="sk-card">
            <div class="sk-row">
              <span class="sk sk-avatar" />
              <div class="sk-col">
                <span class="sk sk-line w40" />
                <span class="sk sk-line w70" />
              </div>
              <span class="sk sk-btn" />
            </div>
            <span class="sk sk-line w90" />
          </div>
        </div>

        <div v-else-if="error" class="state-message error-state">
          <svg class="state-ico" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 8v4M12 16h.01" />
          </svg>
          <p>{{ error }}</p>
          <button type="button" class="retry-btn" @click="loadPosts">Повторить</button>
        </div>

        <div v-else-if="visiblePosts.length === 0" class="state-message empty-state">
          <svg class="state-ico" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
            <path d="M14 2v6h6M8 13h8M8 17h5" />
          </svg>
          <p v-if="hasActiveFilters">
            Ничего не найдено{{ gameFilter ? ` по ${gameFilter}` : '' }}. Попробуй изменить фильтры.
          </p>
          <p v-else>Пока нет активных заявок.</p>
          <div class="empty-actions">
            <button v-if="hasActiveFilters" type="button" class="btn-secondary" @click="resetFilters">
              Сбросить фильтры
            </button>
            <button type="button" class="btn-primary" @click="openCreate">
              Создать первую заявку
            </button>
          </div>
        </div>

        <div v-else class="posts-list">
          <LFGCard
            v-for="post in visiblePosts"
            :key="post.id"
            :post="post"
            :on-respond="respond"
            @open-chat="openChat"
          />
        </div>

        <button
          v-if="nextPageUrl && !loading"
          type="button"
          class="load-more-btn"
          :disabled="loadingMore"
          @click="loadMore"
        >
          {{ loadingMore ? 'Загружаем...' : 'Загрузить ещё' }}
        </button>
      </div>

      <!-- Правая колонка -->
      <aside class="side-col">
        <!-- Ближайшие матчи (мои заявки) -->
        <div v-if="authStore.isAuthenticated" class="card side-card my-apps">
          <h3>
            <svg class="sh-ico" viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7v5l3 2" />
            </svg>
            Ближайшие матчи
          </h3>
          <div v-if="!myApps.length" class="apps-empty">Нет активных заявок</div>
          <div v-else class="apps-list">
            <div v-for="a in myApps" :key="a.id" class="app-row">
              <div class="app-row-top">
                <span class="app-game">{{ a.post_game }}</span>
                <span class="app-st" :class="a.status">
                  {{ a.status === 'accepted' ? 'Принят' : 'Ожидает' }}
                </span>
              </div>
              <div class="app-when">{{ formatAppWhen(a.post_datetime) }}</div>
              <button
                v-if="a.status === 'accepted'"
                type="button"
                class="app-chat"
                @click="openChat({ id: a.post, game: a.post_game })"
              >
                Чат
              </button>
            </div>
          </div>
        </div>

        <ChatSidebar
          v-if="authStore.isAuthenticated"
          ref="chatSidebarRef"
          @open-thread="openChat"
        />

        <div v-else class="card side-card login-card">
          <h3>Чаты и заявки</h3>
          <p>Войди через Steam, чтобы подавать заявки и общаться с тиммейтами.</p>
          <button type="button" class="btn-primary btn-sm" @click="authStore.loginWithSteam()">
            Войти через Steam
          </button>
        </div>

        <div class="card side-card tips">
          <h3>
            <svg class="sh-ico" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M9 18h6M10 22h4" />
              <path d="M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.2 1 2V17h6v-.3c0-.8.4-1.5 1-2A7 7 0 0 0 12 2z" />
            </svg>
            Как это работает
          </h3>
          <ol class="steps">
            <li>
              <span class="step-n">1</span>
              <div>
                <b>Выбери игру</b>
                <span>Отфильтруй заявки или найди по тексту.</span>
              </div>
            </li>
            <li>
              <span class="step-n">2</span>
              <div>
                <b>Подай заявку</b>
                <span>Автор увидит профиль и статистику.</span>
              </div>
            </li>
            <li>
              <span class="step-n">3</span>
              <div>
                <b>После принятия</b>
                <span>Откроются контакт и чат.</span>
              </div>
            </li>
          </ol>
        </div>
      </aside>
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

/* —— Шапка —— */
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
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 10px;
}
.h-ico {
  width: 24px;
  height: 24px;
  fill: none;
  stroke: var(--accent);
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.count-pill {
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--accent);
  background: var(--accent-dim);
  padding: 3px 9px;
  border-radius: 999px;
}
.subtitle {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
}

/* —— Фильтры —— */
.filters-wrap {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.filters-top {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.search-wrap {
  position: relative;
  flex: 1;
  min-width: 220px;
  max-width: 380px;
}
.search-ico {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 15px;
  height: 15px;
  fill: none;
  stroke: var(--text-muted);
  stroke-width: 2;
  stroke-linecap: round;
  pointer-events: none;
}
.lfg-search {
  width: 100%;
  box-sizing: border-box;
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 9px 30px 9px 34px;
  color: var(--text-primary);
  font-size: 13px;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.lfg-search:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-dim);
}
.search-clear {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 12px;
  cursor: pointer;
  padding: 4px;
}
.search-clear:hover { color: var(--text-primary); }

.toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
}
.toggle input { display: none; }
.toggle-box {
  position: relative;
  width: 30px;
  height: 17px;
  border-radius: 999px;
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  transition: background 0.15s, border-color 0.15s;
}
.toggle-box::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: var(--text-muted);
  transition: transform 0.15s, background 0.15s;
}
.toggle.on { color: var(--text-primary); }
.toggle.on .toggle-box {
  background: var(--accent-dim);
  border-color: var(--accent);
}
.toggle.on .toggle-box::after {
  transform: translateX(13px);
  background: var(--accent);
}
.reset-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.games-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.arrow {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-sunken);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.arrow:hover { border-color: var(--accent); color: var(--accent); }
.arrow svg {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.filters {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  flex: 1;
  min-width: 0;
  padding: 2px 0;
  scrollbar-width: none;
  -webkit-mask-image: linear-gradient(to right, transparent 0, #000 12px, #000 calc(100% - 12px), transparent 100%);
  mask-image: linear-gradient(to right, transparent 0, #000 12px, #000 calc(100% - 12px), transparent 100%);
}
.filters::-webkit-scrollbar { display: none; }
.filter-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 7px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: color 0.15s, border-color 0.15s, background 0.15s, transform 0.15s;
}
.filter-chip:first-child { margin-left: 8px; }
.filter-chip:last-child { margin-right: 8px; }
.filter-chip:hover {
  color: var(--text-primary);
  border-color: var(--border-hover);
  transform: translateY(-1px);
}
.filter-chip.active {
  background: var(--accent-dim);
  border-color: var(--accent);
  color: var(--accent);
  box-shadow: 0 0 14px var(--glow-soft);
}

/* —— Раскладка —— */
.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
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
.side-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
  position: sticky;
  top: calc(var(--topbar-h, 64px) + 16px);
}

/* —— Состояния —— */
.state-message {
  padding: 48px 20px;
  text-align: center;
  color: var(--text-secondary);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}
.state-message p { margin: 0; }
.state-ico {
  width: 40px;
  height: 40px;
  fill: none;
  stroke: var(--text-muted);
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.error-state { color: var(--danger); }
.error-state .state-ico { stroke: var(--danger); }
.empty-actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
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
  padding: 11px;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.load-more-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.load-more-btn:disabled { opacity: 0.55; cursor: default; }

/* —— Скелетоны —— */
.sk-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.sk-row { display: flex; align-items: center; gap: 12px; }
.sk-col { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.sk {
  display: block;
  background: linear-gradient(90deg, var(--bg-sunken), var(--bg-card-hover), var(--bg-sunken));
  background-size: 200% 100%;
  animation: sk 1.3s linear infinite;
  border-radius: 6px;
}
.sk-avatar { width: 44px; height: 44px; border-radius: 10px; }
.sk-btn { width: 90px; height: 32px; border-radius: 8px; }
.sk-line { height: 11px; }
.w90 { width: 90%; } .w70 { width: 70%; } .w40 { width: 40%; }
@keyframes sk { to { background-position: -200% 0; } }

/* —— Боковые карточки —— */
.side-card { display: flex; flex-direction: column; gap: 12px; }
.side-card h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
}
.sh-ico {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: var(--accent);
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.side-card p {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-secondary);
}
.btn-sm { padding: 8px 12px; font-size: 12px; align-self: flex-start; }
.login-card {
  background:
    radial-gradient(ellipse 80% 120% at 100% 0%, rgba(230, 57, 70, 0.2), transparent 60%),
    var(--bg-card);
}
.steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.steps li { display: flex; gap: 12px; align-items: flex-start; }
.steps li div { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.steps b { font-size: 13px; font-weight: 600; }
.steps span:not(.step-n) { font-size: 12px; color: var(--text-secondary); line-height: 1.4; }
.step-n {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
  font-family: var(--font-mono);
  color: var(--accent);
  background: var(--accent-dim);
  border: 1px solid color-mix(in srgb, var(--accent) 40%, transparent);
}

/* —— Ближайшие матчи —— */
.my-apps .apps-empty {
  font-size: 12px;
  color: var(--text-muted);
}
.apps-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.app-row {
  padding: 10px;
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}
.app-row-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.app-game {
  font-weight: 700;
  font-size: 12px;
}
.app-st {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 999px;
  flex-shrink: 0;
}
.app-st.pending {
  color: #e8b84a;
  background: rgba(232, 184, 74, 0.12);
}
.app-st.accepted {
  color: var(--success);
  background: rgba(106, 170, 124, 0.12);
}
.app-when {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  margin-top: 4px;
}
.app-chat {
  margin-top: 8px;
  width: 100%;
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 6px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}
.app-chat:hover {
  border-color: var(--accent);
  color: var(--accent);
}

@media (max-width: 1000px) {
  .content-grid { grid-template-columns: 1fr; }
  .side-col { position: static; }
}
@media (max-width: 900px) {
  .page-header h1 { font-size: 18px; }
  .arrow { display: none; }
}
</style>