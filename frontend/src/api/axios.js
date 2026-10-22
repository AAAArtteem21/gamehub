import axios from 'axios'

const api = axios.create({
  baseURL: 'https://gameeyes.onrender.com/api/',
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('gh_token')
  if (token) {
    config.headers.Authorization = `Token ${token}`
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  async (err) => {
    if (err.response?.status === 401) {
      const url = err.config?.url || ''
      // только явный me/logout — не сносить токен на любой 401
      const isAuthCheck =
        url.includes('me/') ||
        url.includes('auth/logout')

      if (isAuthCheck) {
        localStorage.removeItem('gh_token')
        delete api.defaults.headers.common['Authorization']
        try {
          const { useAuthStore } = await import('../stores/auth')
          const auth = useAuthStore()
          auth.user = null
          auth.token = null
        } catch (_) { }
      }
    }
    return Promise.reject(err)
  }
)

export default api