<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

onMounted(async () => {
  // Разовый token в URL — запасной путь (разные домены / Chrome режет third-party cookie)
  const token = route.query.token
  if (token) {
    authStore.setToken(token)
  }

  try {
    await authStore.fetchMe()
    const back = sessionStorage.getItem('post_login_redirect') || '/'
    sessionStorage.removeItem('post_login_redirect')
    // убираем token из адресной строки
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