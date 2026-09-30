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
  max-width: none; /* ← убрать потолок */
  box-sizing: border-box;
}
</style>