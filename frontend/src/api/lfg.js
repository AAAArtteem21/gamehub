import api from './axios'

export const lfgApi = {
  list: (params) => api.get('lfg-posts/', { params }),
  listByUrl: (url) => api.get(url.replace(/^.*\/api\//, '')), // если next абсолютный — подстрой под axios base
  get: (id) => api.get(`lfg-posts/${id}/`),
  create: (data) => api.post('lfg-posts/', data),
  close: (id) => api.post(`lfg-posts/${id}/close/`),
  applications: (postId) => api.get(`lfg-posts/${postId}/applications/`),

  // заявка
  respond: (postId, payload = {}) =>
    api.post('lfg-responses/', { post: postId, message: payload.message || '', preferred_role: payload.preferred_role || '' }),
  accept: (responseId) => api.post(`lfg-responses/${responseId}/accept/`),
  reject: (responseId) => api.post(`lfg-responses/${responseId}/reject/`),
  withdraw: (responseId) => api.delete(`lfg-responses/${responseId}/`),

  myApplications: () => api.get('lfg-my-applications/'),
  notifications: () => api.get('lfg-notifications/'),
  chatThreads: () => api.get('lfg-chat-threads/'),
  chatMessages: (postId) => api.get('lfg-chat/', { params: { post: postId } }),
  sendChat: (postId, text) => api.post('lfg-chat/', { post: postId, text }),
}