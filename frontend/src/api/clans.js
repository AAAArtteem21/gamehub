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
  join(inviteCode) {
    return api.post('clans/join/', { invite_code: inviteCode })
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
}