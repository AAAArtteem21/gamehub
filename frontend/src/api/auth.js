import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useAuthStore = defineStore('auth', () => {

    const user = ref(null)
    const loading = ref(false)
    const error = ref(null)


    async function fetchUser() {
        loading.value = true
        error.value = null

        try {
            const response = await api.get('/profiles/me/')
            
            user.value = response.data

        } catch (err) {
            console.error('Ошибка загрузки профиля:', err)

            user.value = null
            error.value = 'Не удалось загрузить профиль'

        } finally {
            loading.value = false
        }
    }


    async function updateProfile(data) {
        try {
            const response = await api.patch('/profiles/me/', data)

            user.value = response.data

            return response.data

        } catch (err) {
            console.error('Ошибка обновления профиля:', err)
            throw err
        }
    }


    async function logout() {
        try {
            await api.post('/auth/logout/')
        } catch (err) {
            console.error(err)
        }

        user.value = null
    }


    function setUser(data) {
        user.value = data
    }


    return {
        user,
        loading,
        error,

        fetchUser,
        updateProfile,
        logout,
        setUser
    }
})