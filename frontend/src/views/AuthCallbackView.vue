<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

onMounted(async () => {
  const token = route.query.token
  if (token) {
    authStore.setToken(String(token))
  }

  const back = sessionStorage.getItem('post_login_redirect') || '/'
  sessionStorage.removeItem('post_login_redirect')

  try {
    await authStore.fetchUser()
    router.replace(back)
  } catch {
    // токен есть — не на login, а на главную
    if (authStore.token) router.replace(back)
    else router.replace('/login')
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