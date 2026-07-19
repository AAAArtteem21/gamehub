<script setup>
import { onMounted } from 'vue'
import api from './api/axios'
import { useAuthStore } from './stores/auth'
import { useChatStore } from './stores/chat'

const chatStore = useChatStore()
const authStore = useAuthStore()

onMounted(async () => {
  document.addEventListener('click', () => chatStore.unlockAudio?.(), { once: true })
  await api.get('csrf/')  // гарантируем что csrftoken cookie установлена
  if (authStore.isAuthenticated && !authStore.user) {
    authStore.fetchMe()
  }
  if (authStore.isAuthenticated) chatStore.startPolling()

})
</script>

<template>
  <RouterView />
</template>