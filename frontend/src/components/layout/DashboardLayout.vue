<script setup>
import { ref, provide, watch } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from './SideBar.vue'
import TopBar from './TopBar.vue'
import ToastHost from '../ui/ToastHost.vue'

const route = useRoute()
const sidebarOpen = ref(false)

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
    <div class="sidebar-backdrop" v-if="sidebarOpen" @click="closeSidebar" />
    <Sidebar />
    <div class="main">
      <TopBar />
      <div class="content">
        <RouterView v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </RouterView>
      </div>
    </div>
    <ToastHost />
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  min-height: 100vh;
}
.main {
  margin-left: var(--sidebar-w);
  width: calc(100% - var(--sidebar-w));
  min-width: 0;
  flex: 1;
}
.content {
  padding: 20px 24px 40px;
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}
.sidebar-backdrop {
  display: none;
}

@media (max-width: 900px) {
  .main {
    margin-left: 0;
    width: 100%;
  }
  .content {
    padding: 14px 14px 32px;
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