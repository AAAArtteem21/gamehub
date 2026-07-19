<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { useRouter } from 'vue-router'
import IconSearch from '../icons/IconSearch.vue'
const authStore = useAuthStore()
const router = useRouter()
const menuOpen = ref(false)
const menuRef = ref(null)
const searchQuery = ref('')

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

function handleClickOutside(e) {
  if (menuRef.value && !menuRef.value.contains(e.target)) {
    menuOpen.value = false
  }
}
function handleSearch() {
  if (!searchQuery.value.trim()) return
  router.push({ path: '/lfg', query: { search: searchQuery.value.trim() } })
}


onMounted(() => document.addEventListener('click', handleClickOutside))
onUnmounted(() => document.removeEventListener('click', handleClickOutside))
</script>

<template>
  <header class="topbar">
    <form class="search" @submit.prevent="handleSearch">
      <span class="search-icon"><IconSearch /></span>
      <input v-model="searchQuery" type="text" placeholder="Найти игроков, кланы, заявки..." />
    </form>

    <div class="user-block" ref="menuRef">
      <button class="user-trigger" @click="toggleMenu">
        <div
          class="avatar"
          :style="authStore.user?.avatar_url ? { backgroundImage: `url(${authStore.user.avatar_url})` } : {}"
        >
          <span v-if="!authStore.user?.avatar_url" class="avatar-fallback">
            {{ (authStore.user?.display_name || authStore.user?.username || '?')[0]?.toUpperCase() }}
          </span>
        </div>
        <span class="username">{{ authStore.user?.display_name || authStore.user?.username || '...' }}</span>
        <span class="chevron" :class="{ open: menuOpen }">⌄</span>
      </button>

      <transition name="menu-fade">
        <div class="dropdown" v-if="menuOpen">
          <RouterLink to="/profile" class="dropdown-item" @click="menuOpen = false">
            <span class="dropdown-icon">◈</span> Мой профиль
          </RouterLink>
          <div class="dropdown-divider"></div>
          <button class="dropdown-item danger" @click="handleLogout">
            <span class="dropdown-icon">⏻</span> Выйти
          </button>
        </div>
      </transition>
    </div>
  </header>
</template>

<style scoped>
.search-icon svg { width: 15px; height: 15px; }

.topbar {
  height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  border-bottom: 1px solid var(--border-color);
  background: rgba(10, 12, 16, 0.6);
  backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 50;
}

.search {
  position: relative;
  display: flex;
  align-items: center;
  width: 340px;
}

.search-icon {
  position: absolute;
  left: 14px;
  color: var(--text-muted);
  font-size: 15px;
  pointer-events: none;
}

.search input {
  width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 14px 10px 38px;
  color: var(--text-primary);
  font-size: 13px;
  transition: border-color 0.2s var(--ease), background 0.2s var(--ease);
}

.search input::placeholder {
  color: var(--text-muted);
}

.search input:focus {
  outline: none;
  border-color: var(--accent);
  background: var(--bg-card-hover);
}

.user-block {
  position: relative;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 10px;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 6px 10px 6px 6px;
  border-radius: var(--radius-sm);
  transition: background 0.2s var(--ease);
}

.user-trigger:hover {
  background: var(--bg-card-hover);
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background-color: var(--accent-dim);
  background-size: cover;
  background-position: center;
  border: 2px solid var(--accent);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-fallback {
  font-weight: 700;
  font-size: 14px;
  color: var(--accent);
}

.username {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chevron {
  color: var(--text-secondary);
  font-size: 12px;
  transition: transform 0.2s var(--ease);
}

.chevron.open {
  transform: rotate(180deg);
}

.dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 180px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md);
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 8px;
  color: var(--text-primary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  background: none;
  border: none;
  cursor: pointer;
  width: 100%;
  text-align: left;
  transition: background 0.15s var(--ease);
}

.dropdown-item:hover {
  background: var(--bg-card-hover);
}

.dropdown-item.danger:hover {
  background: rgba(248, 113, 113, 0.1);
  color: var(--danger);
}

.dropdown-icon {
  width: 16px;
  text-align: center;
  color: var(--text-secondary);
}

.dropdown-divider {
  height: 1px;
  background: var(--border-color);
  margin: 4px 2px;
}

.menu-fade-enter-active, .menu-fade-leave-active {
  transition: opacity 0.15s var(--ease), transform 0.15s var(--ease);
}
.menu-fade-enter-from, .menu-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>