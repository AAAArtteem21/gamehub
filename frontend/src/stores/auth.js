import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TOKEN_KEY = 'gh_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(
    localStorage.getItem(TOKEN_KEY) ||
    localStorage.getItem('gamehub_token') ||
    null
  )
  const user = ref(null)
  const loginPromptOpen = ref(false)
  const loginPromptReason = ref('')

  const isAuthenticated = computed(() => !!token.value || !!user.value)

  function setToken(newToken) {
    token.value = newToken || null

    if (newToken) {
      localStorage.setItem(TOKEN_KEY, newToken)
      localStorage.removeItem('gamehub_token')
      api.defaults.headers.common['Authorization'] = `Token ${newToken}`
    } else {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem('gamehub_token')
      delete api.defaults.headers.common['Authorization']
    }
  }

  function clearLocal() {
    token.value = null
    user.value = null

    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem('gamehub_token')

    delete api.defaults.headers.common['Authorization']
  }

  async function logout() {
    try {
      await api.post('auth/logout/')
    } catch (_) {
    }
    clearLocal()
  }

  async function fetchMe() {
    try {
      const res = await api.get('me/')
      user.value = res.data
      if (!token.value && res.data) {
        token.value = 'cookie'
      }
      return res.data
    } catch (e) {
      if (e.response?.status === 401) clearLocal()
      throw e
    }
  }

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


  if (token.value && token.value !== 'cookie') {
    localStorage.setItem(TOKEN_KEY, token.value)
    localStorage.removeItem('gamehub_token')
    api.defaults.headers.common['Authorization'] = `Token ${token.value}`
  }

  return {
    token,
    user,
    isAuthenticated,
    loginPromptOpen,
    loginPromptReason,
    setToken,
    clearLocal,
    logout,
    fetchMe,
    requireAuth,
    loginWithSteam,
  }
})