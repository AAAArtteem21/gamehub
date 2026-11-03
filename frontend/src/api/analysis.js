import api from './axios'

export const analysisApi = {
    createDota: (matchId, hint = {}) =>
        api.post('analysis/dota/', { match_id: String(matchId), ...hint }),

    createFaceit: (matchId, hint = {}) =>
        api.post('analysis/faceit/', { match_id: String(matchId), ...hint }),

    get: (id) => api.get(`analysis/${id}/`),
    listDota: () => api.get('analysis/dota/list/'),
}