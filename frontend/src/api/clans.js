
import api from './axios'

export const clansApi = {
  list: (params) => api.get('clans/', { params }),
  create: (data) => api.post('clans/', data),
  join: (data) => api.post('clans/join/', data),
  joinOpen: (clanId) => api.post('clans/join/', { clan_id: clanId }),
  leave: (id) => api.post(`clans/${id}/leave/`),
  dashboard: (id) => api.get(`clans/${id}/dashboard/`),
  members: (id) => api.get(`clans/${id}/members/`),
  kick: (id, userId, reason = '') =>
    api.post(`clans/${id}/kick/`, { user_id: userId, reason }),
  ban: (id, userId, reason = '') =>
    api.post(`clans/${id}/ban/`, { user_id: userId, reason }),
  unban: (id, userId) =>
    api.post(`clans/${id}/unban/`, { user_id: userId }),
  changeRole: (id, userId, role) =>
    api.post(`clans/${id}/change_role/`, { user_id: userId, role }),
  modLog: (id) => api.get(`clans/${id}/mod_log/`),
  bans: (id) => api.get(`clans/${id}/bans/`),
  uploadLogo: (id, formData) =>
    api.post(`clans/${id}/upload_logo/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
}
