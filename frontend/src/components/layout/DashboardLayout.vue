<script setup>
import { ref, provide, watch } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from './SideBar.vue'
import TopBar from './TopBar.vue'
import ToastHost from '../ui/ToastHost.vue'

const route = useRoute()
const sidebarOpen = ref(false)
const year = new Date().getFullYear()

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}
function closeSidebar() {
  sidebarOpen.value = false
}

provide('sidebarOpen', sidebarOpen)
provide('toggleSidebar', toggleSidebar)
provide('closeSidebar', closeSidebar)

watch(() => route.fullPath, closeSidebar)
</script>

<template>
  <div class="layout" :class="{ 'sidebar-open': sidebarOpen }">
    <TopBar />
    <div class="sidebar-backdrop" v-if="sidebarOpen" @click="closeSidebar" />
    <Sidebar />
    <div class="main">
      <div class="content">
        <RouterView v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </RouterView>
      </div>

      <footer class="site-footer">
        <p class="legal">
          GAMEEYES не связан с Valve или Steam. Steam и логотип Steam являются товарными знаками
          Valve Corporation. Все остальные товарные знаки принадлежат их владельцам.
        </p>
        <p class="copy">© {{ year }} GameEyes</p>
      </footer>
    </div>
    <ToastHost />
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
}
.main {
  margin-left: var(--sidebar-w);
  padding-top: var(--topbar-h);
  width: calc(100% - var(--sidebar-w));
  min-width: 0;
  min-height: 100vh;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}
.content {
  flex: 1;
  padding: 20px 24px 32px;
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}
.sidebar-backdrop {
  display: none;
}

/* —— Футер с юридической пометкой —— */
.site-footer {
  margin: 0 24px;
  padding: 16px 0 22px;
  border-top: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 6px;
  text-align: center;
}
.site-footer p {
  margin: 0;
}
.legal {
  max-width: 760px;
  margin: 0 auto !important;
  font-size: 11px;
  line-height: 1.55;
  color: var(--text-muted);
}
.copy {
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
  opacity: 0.7;
}

@media (max-width: 900px) {
  .main {
    margin-left: 0;
    width: 100%;
  }
  .content {
    padding: 14px 14px 24px;
  }
  .site-footer {
    margin: 0 14px;
    padding: 14px 0 18px;
  }
  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 45;
    background: rgba(0, 0, 0, 0.55);
  }
}
</style>