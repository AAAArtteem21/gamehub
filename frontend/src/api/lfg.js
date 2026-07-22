import api from './axios'

export const lfgApi = {
  list(params = {}) {
    return api.get('lfg-posts/', { params })
  },
  create(data) {
    return api.post('lfg-posts/', data)
  },
  respond(postId) {
    return api.post('lfg-responses/', { post: postId })
  },
  close(postId) {
    return api.post(`lfg-posts/${postId}/close/`)
  },
}