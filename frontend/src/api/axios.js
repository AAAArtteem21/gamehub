// src/api/axios.js
import axios from 'axios'
import router from '../router'
import { useAuthStore } from '../stores/auth'

const api = axios.create({
  baseURL: 'https://gameeyes.onrender.com/',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  withXSRFToken: true,   // ← вот это ключевое, без него заголовок не прикладывается на другой origin
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API error:', error.response?.status, error.config?.url, error.response?.data)
    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      authStore.logout()
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default api