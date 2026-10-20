import axios from 'axios'

const api = axios.create({
  baseURL: 'https://gameeyes.onrender.com/api/',
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('gh_token')
  if (token) {
    config.headers.Authorization = `Token ${token}`
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  async (err) => {
    if (err.response?.status === 401) {
      const { useAuthStore } = await import('../stores/auth')
      const auth = useAuthStore()
      if (auth.isAuthenticated) auth.logout()
      if (err.config?.method && err.config.method !== 'get') {
        auth.requireAuth('Войди через Steam, чтобы это сделать.')
      }
    }
    return Promise.reject(err)
  }
)

export default api