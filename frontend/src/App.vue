<script setup>
import { onMounted } from 'vue'
import api from './api/axios'
import { useAuthStore } from './stores/auth'
import { useChatStore } from './stores/chat'
import LoginPromptModal from './components/LoginPromptModal.vue'

const chatStore = useChatStore()
const authStore = useAuthStore()

onMounted(() => {
  document.addEventListener('click', () => chatStore.unlockAudio?.(), { once: true })
  api.get('csrf/').catch(() => {})
  if (authStore.isAuthenticated) {
    if (!authStore.user) authStore.fetchMe()
    chatStore.startPolling()
  }
})
</script>

<template>
  <ToastHost />
  <RouterView />
  <LoginPromptModal />
</template>