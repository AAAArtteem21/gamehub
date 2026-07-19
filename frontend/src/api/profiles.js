import api from './axios'

export const profilesApi = {
  list() {
    return api.get('game-accounts/')
  },
  create(data) {
    return api.post('game-accounts/', data)
  },
  remove(id) {
    return api.delete(`game-accounts/${id}/`)
  },
  sync(id) {
    return api.post(`game-accounts/${id}/sync/`)
  },
  summary(id) {
    return api.get(`game-accounts/${id}/summary/`)
  },
}