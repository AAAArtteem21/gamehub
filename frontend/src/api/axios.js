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
  (err) => {
    return Promise.reject(err)
  }
)

export default api