import axios from 'axios'

const api = axios.create({
  baseURL: `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/`,
})

api.interceptors.response.use(
  (r) => r,
  async (err) => {
    if (err.response?.status === 401) {
      const { useAuthStore } = await import('../stores/auth')
      const auth = useAuthStore()
      if (auth.isAuthenticated) auth.logout() // протухший токен
      // окно показываем только на действиях, не на фоновых GET
      if (err.config?.method && err.config.method !== 'get') {
        auth.requireAuth('Войди через Steam, чтобы это сделать.')
      }
    }
    return Promise.reject(err)
  }
)

export default api