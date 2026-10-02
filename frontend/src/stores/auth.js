import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('gamehub_token') || null)
  const user = ref(null)
  const loginPromptOpen = ref(false)
  const loginPromptReason = ref('')

  const isAuthenticated = computed(() => !!token.value)

  function setToken(newToken) {
    token.value = newToken
    localStorage.setItem('gamehub_token', newToken)
    api.defaults.headers.common['Authorization'] = `Token ${newToken}`
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('gamehub_token')
    delete api.defaults.headers.common['Authorization']
  }

  async function fetchMe() {
    try {
      const res = await api.get('me/')
      user.value = res.data
    } catch (e) {
      // выходим только если токен реально невалидный, а не при сбое сети/сервера
      if (e.response?.status === 401) logout()
    }
  }

  // вернёт true, если можно продолжать; иначе покажет окно "войди через Steam"
  function requireAuth(reason = '') {
    if (isAuthenticated.value) return true
    loginPromptReason.value = reason
    loginPromptOpen.value = true
    return false
  }

  function loginWithSteam() {
    sessionStorage.setItem('post_login_redirect', location.pathname + location.search)
    window.location.href = `${API_BASE}/api/auth/steam/start/`
  }

  if (token.value) {
    api.defaults.headers.common['Authorization'] = `Token ${token.value}`
  }

  return {
    token, user, isAuthenticated, loginPromptOpen, loginPromptReason,
    setToken, logout, fetchMe, requireAuth, loginWithSteam,
  }
})