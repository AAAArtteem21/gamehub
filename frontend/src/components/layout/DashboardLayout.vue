<script setup>
import Sidebar from './SideBar.vue'
import TopBar from './TopBar.vue'
import ToastHost from '../ui/ToastHost.vue'
</script>

<template>
  <div class="layout">
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
.page-enter-active, .page-leave-active {
  transition: opacity 0.2s var(--ease), transform 0.2s var(--ease);
}
.page-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
.layout {
  display: flex;
}
.main {
  margin-left: 240px;
  width: calc(100% - 240px);
}
.content {
  padding: 24px;
}
</style>