import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/axios'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('gamehub_token') || null)
  const user = ref(null)

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
      logout()
    }
  }

  // при старте приложения — если токен уже есть, сразу проставить заголовок
  if (token.value) {
    api.defaults.headers.common['Authorization'] = `Token ${token.value}`
  }

  return { token, user, isAuthenticated, setToken, logout, fetchMe }
})