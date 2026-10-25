import api from './axios'

export const analysisApi = {
    /**
     * @param {string|number} matchId
     * @param {object} [hint]
     */
    createDota: (matchId, hint = {}) =>
        api.post('analysis/dota/', {
            match_id: String(matchId),
            ...hint,
        }),

    get: (id) => api.get(`analysis/${id}/`),
    listDota: () => api.get('analysis/dota/list/'),
}