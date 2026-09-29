import api from './axios'

export const lfgApi = {
  list(params = {}) {
    return api.get('lfg-posts/', { params })
  },
  listByUrl(url) {
    // next/previous от DRF приходят полным URL с доменом — вырезаем только путь+query
    const path = url.replace(/^https?:\/\/[^/]+\/api\//, '')
    return api.get(path)
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