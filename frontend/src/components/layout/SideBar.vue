<script setup>
import { RouterLink, useRoute } from 'vue-router'
import { ref, onMounted } from 'vue'
import logo from '../../assets/images/logo.png'
import api from '../../api/axios'
import IconHome from '../icons/IconHome.vue'
import IconSword from '../icons/IconSword.vue'
import IconShield from '../icons/IconShield.vue'
import IconTarget from '../icons/IconTarget.vue'

const navItems = [
  { name: 'Дашборд', path: '/', icon: IconHome },
  { name: 'Поиск тиммейтов', path: '/lfg', icon: IconSword },
  { name: 'Кланы', path: '/clans', icon: IconShield },
  { name: 'Профиль', path: '/profile', icon: IconTarget },
]

const route = useRoute()
const quickStats = ref(null)

async function loadQuickStats() {
  try {
    const res = await api.get('me/quick-stats/')
    quickStats.value = res.data
  } catch (e) {
    quickStats.value = null
  }
}

onMounted(loadQuickStats)
</script>

<template>
  <aside class="sidebar">
    <div class="logo">
      <img :src="logo" alt="GameEyes" class="logo-mark" />
      <div class="logo-text-group">
        <span class="logo-text">GAME<span class="accent-text">EYES</span></span>
        <span class="logo-tagline">FIND. PLAY. WIN.</span>
      </div>
    </div>

    <nav class="nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: route.path === item.path }"
      >
        <span class="nav-icon"><component :is="item.icon" /></span>
        {{ item.name }}
      </RouterLink>
    </nav>

    <div class="sidebar-widget" v-if="quickStats">
      <span class="widget-title">Сегодня</span>
      <div class="widget-row">
        <span class="widget-label">Активных заявок</span>
        <span class="widget-value">{{ quickStats.open_lfg }}</span>
      </div>
      <div class="widget-row">
        <span class="widget-label">Непрочитано чатов</span>
        <span class="widget-value accent">{{ quickStats.unread_chats }}</span>
      </div>
      <div class="widget-row">
        <span class="widget-label">Кланов</span>
        <span class="widget-value">{{ quickStats.clans_count }}</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 240px;
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  background: var(--bg-card);
  border-right: 1px solid var(--border-color);
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 8px;
}

.logo-mark {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  flex-shrink: 0;
}

.logo-text-group {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}

.logo-text {
  font-weight: 800;
  letter-spacing: 0.5px;
  font-size: 15px;
  color: var(--text-primary);
}

.accent-text {
  color: var(--accent);
}

.logo-tagline {
  font-size: 9px;
  letter-spacing: 1.2px;
  color: var(--text-secondary);
  font-weight: 600;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 12px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.2s var(--ease), color 0.2s var(--ease);
}

.nav-item:hover {
  background: var(--bg-card-hover);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--accent-dim);
  color: var(--accent);
}

.nav-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-icon svg {
  width: 20px;
  height: 20px;
  transition: transform 0.2s var(--ease);
}

.nav-item:hover .nav-icon svg {
  transform: scale(1.1);
}

.sidebar-widget {
  margin-top: auto;
  background: var(--bg-card-hover);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.widget-title {
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  font-weight: 700;
}

.widget-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.widget-label {
  color: var(--text-secondary);
}

.widget-value {
  font-weight: 700;
}

.widget-value.accent {
  color: var(--accent);
}
</style>