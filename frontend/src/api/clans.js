import api from './axios'

export const clansApi = {
  list() {
    return api.get('clans/')
  },
  create(data) {
    return api.post('clans/', data)
  },
  detail(id) {
    return api.get(`clans/${id}/`)
  },
  join(payload) {
    if (typeof payload === 'string') {
      return api.post('clans/join/', { invite_code: payload })
    }
    return api.post('clans/join/', payload)
  },
  joinOpen(clanId) {
    return api.post('clans/join/', { clan_id: clanId })
  },
  dashboard(id) {
    return api.get(`clans/${id}/dashboard/`)
  },
  members(id) {
    return api.get(`clans/${id}/members/`)
  },
  kick(id, userId) {
    return api.post(`clans/${id}/kick/`, { user_id: userId })
  },
  leave(id) {
    return api.post(`clans/${id}/leave/`)
  },
  changeRole(id, userId, role) {
    return api.post(`clans/${id}/change_role/`, { user_id: userId, role })
  },
}