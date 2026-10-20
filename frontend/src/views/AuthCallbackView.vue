<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

onMounted(async () => {
  // Токен уже в HttpOnly cookie (выставил бэкенд при redirect).
  // Никакого route.query.token и localStorage.
  try {
    await authStore.fetchMe()
    const back = sessionStorage.getItem('post_login_redirect') || '/'
    sessionStorage.removeItem('post_login_redirect')
    router.replace(back)
  } catch {
    router.replace('/login')
  }
})
</script>

<template>
  <div class="callback-page">
    <p>Входим...</p>
  </div>
</template>

<style scoped>
.callback-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}
</style>