<script setup>
import { onMounted, ref } from 'vue'
import api from './api/axios'
import { useAuthStore } from './stores/auth'
import { useChatStore } from './stores/chat'
import LoginPromptModal from './components/LoginPromptModal.vue'

const chatStore = useChatStore()
const authStore = useAuthStore()
const bootstrapping = ref(true)

onMounted(async () => {
  document.addEventListener('click', () => chatStore.unlockAudio?.(), { once: true })
  api.get('csrf/').catch(() => {})

  try {
    // токен из localStorage уже в store при создании
    if (authStore.token) {
      try {
        await authStore.fetchMe()
        chatStore.startPolling?.()
      } catch (e) {
        console.warn('fetchMe on boot failed', e)
      }
    }
  } finally {
    bootstrapping.value = false
  }
})
</script>

<template>
  <div v-if="bootstrapping" class="app-boot">
    <span class="boot-dots">...</span>
  </div>
  <template v-else>
    <ToastHost />
    <RouterView />
    <LoginPromptModal />
  </template>
</template>

<style scoped>
.app-boot {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}
.boot-dots {
  font-size: 28px;
  letter-spacing: 6px;
  animation: pulse 1s ease-in-out infinite;
}
@keyframes pulse {
  50% { opacity: 0.35; }
}
</style>