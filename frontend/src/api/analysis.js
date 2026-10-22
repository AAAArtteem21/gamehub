import api from './axios'

export const analysisApi = {
    createDota: (matchId) =>
        api.post('analysis/dota/', { match_id: String(matchId) }),

    get: (id) => api.get(`analysis/${id}/`),

    listDota: () => api.get('analysis/dota/list/'),
}