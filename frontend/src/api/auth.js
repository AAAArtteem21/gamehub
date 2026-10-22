import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

const TOKEN_KEY = 'gh_token'

export const useAuthStore = defineStore('auth', () => {
    const user = ref(null)
    const loading = ref(false)
    const error = ref(null)
    const token = ref(localStorage.getItem(TOKEN_KEY) || null)

    const loginPromptOpen = ref(false)
    const loginPromptReason = ref('')

    const isAuthenticated = computed(() => !!token.value || !!user.value)

    function setToken(newToken) {
        token.value = newToken || null
        if (newToken) {
            localStorage.setItem(TOKEN_KEY, newToken)
            api.defaults.headers.common['Authorization'] = `Token ${newToken}`
        } else {
            localStorage.removeItem(TOKEN_KEY)
            delete api.defaults.headers.common['Authorization']
        }
    }

    // при старте приложения подставляем токен
    if (token.value) {
        api.defaults.headers.common['Authorization'] = `Token ${token.value}`
    }

    function setUser(data) {
        user.value = data
    }

    async function fetchUser() {
        loading.value = true
        error.value = null
        try {
            const response = await api.get('/profiles/me/')
            user.value = response.data
            return response.data
        } catch (err) {
            console.error('Ошибка загрузки профиля:', err)
            if (err.response?.status === 401) {
                setToken(null)
                user.value = null
            }
            error.value = 'Не удалось загрузить профиль'
            throw err
        } finally {
            loading.value = false
        }
    }

    // алиас, если где-то вызывается fetchMe
    async function fetchMe() {
        return fetchUser()
    }

    async function updateProfile(data) {
        const response = await api.patch('/profiles/me/', data)
        user.value = response.data
        return response.data
    }

    async function logout() {
        try {
            await api.post('/auth/logout/')
        } catch (err) {
            console.error(err)
        }
        setToken(null)
        user.value = null
    }

    function requireAuth(reason = '') {
        if (isAuthenticated.value) return true
        loginPromptReason.value = reason
        loginPromptOpen.value = true
        return false
    }

    function loginWithSteam() {
        sessionStorage.setItem('post_login_redirect', location.pathname + location.search)
        const base = import.meta.env.VITE_API_URL || 'https://gameeyes.onrender.com'
        window.location.href = `${base}/api/auth/steam/start/`
    }

    return {
        user,
        loading,
        error,
        token,
        isAuthenticated,
        loginPromptOpen,
        loginPromptReason,
        setToken,
        setUser,
        fetchUser,
        fetchMe,
        updateProfile,
        logout,
        requireAuth,
        loginWithSteam,
    }
})