import api from './axios'

export const friendsApi = {
    getPresence: () => api.get('friends/presence/'),
    setPresence: (data) => api.post('friends/presence/', data),
    list: () => api.get('friends/'),
    requests: () => api.get('friends/requests/'),
    sendRequest: (userId, message = '') =>
        api.post('friends/requests/', { user_id: Number(userId), message }),
    acceptRequest: (id) => api.post(`friends/requests/${id}/accept/`),
    rejectRequest: (id) => api.post(`friends/requests/${id}/reject/`),
    cancelRequest: (id) => api.post(`friends/requests/${id}/cancel/`),
    unfriend: (userId) => api.delete(`friends/${userId}/`),
    suggestions: () => api.get('friends/suggestions/'),
    invite: (userId, { message = '', game = '' } = {}) =>
        api.post('friends/invite/', { user_id: Number(userId), message, game }),
    relation: (userId) => api.get(`friends/status/${userId}/`),
}