<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/axios'
import MatchParticipantsModal from '../components/profiles/MatchParticipantsModal.vue'
import ValorantMatchModal from '../components/profiles/ValorantMatchModal.vue'

const route = useRoute()
const router = useRouter()
const profile = ref(null)
const loading = ref(true)
const error = ref(null)
const historyLimit = ref(8)
const openMatchId = ref(null)
const openMatchGame = ref(null)
const isFav = ref(false)

const game = computed(() => String(route.params.game || 'dota2').toLowerCase())
const externalId = computed(() => String(route.params.externalId || ''))

const visibleHistory = computed(() =>
  (profile.value?.match_history || []).slice(0, historyLimit.value)
)
const canExpand = computed(() =>
  (profile.value?.match_history || []).length > historyLimit.value
)

const winrate = computed(() => {
  if (!profile.value) return null
  const w = profile.value.wins || 0
  const l = profile.value.losses || 0
  const t = w + l
  if (!t) return null
  return Math.round((w / t) * 1000) / 10
})

const sourceLabel = computed(() =>
  game.value === 'valorant'
    ? 'Данные Valorant (открытый API)'
    : 'Данные из открытого источника (OpenDota)'
)

function gPlatform() {
  if (game.value === 'dota2' || game.value === 'opendota') return 'opendota'
  return game.value
}

async function load() {
  loading.value = true
  error.value = null
  profile.value = null
  historyLimit.value = 8
  openMatchId.value = null
  openMatchGame.value = null

  const g = game.value
  const eid = externalId.value
  if (!g || !eid || eid === 'undefined') {
    error.value = 'Некорректная ссылка на профиль'
    loading.value = false
    return
  }

  try {
    const res = await api.get(`guest-profile/${g}/${encodeURIComponent(eid)}/`)
    profile.value = res.data
    await loadFavStatus()
  } catch (e) {
    error.value =
      e.response?.data?.detail ||
      `Ошибка ${e.response?.status || ''} — не удалось загрузить профиль`
  } finally {
    loading.value = false
  }
}

async function loadFavStatus() {
  try {
    const res = await api.get('favorites/status/', {
      params: { platform: gPlatform(), external_id: externalId.value },
    })
    isFav.value = !!res.data.favorited
  } catch {
    isFav.value = false
  }
}

async function toggleFav() {
  try {
    const res = await api.post('favorites/toggle/', {
      platform: gPlatform(),
      external_id: externalId.value,
      display_name: profile.value?.display_name || externalId.value,
      avatar_url: profile.value?.avatar_url || '',
    })
    isFav.value = !!res.data.favorited
  } catch (e) {
    alert(e.response?.data?.detail || 'Не удалось изменить избранное')
  }
}

function goToFullProfile() {
  if (profile.value?.gamehub_user_id) {
    router.push(`/players/${profile.value.gamehub_user_id}`)
  }
}

function goCompare() {
  router.push({
    path: '/compare',
    query: {
      platform: gPlatform(),
      external_id: externalId.value,
    },
  })
}

function showMoreHistory() {
  historyLimit.value = Math.min(
    historyLimit.value + 10,
    (profile.value?.match_history || []).length
  )
}

function openMatch(m) {
  if (!m?.match_id) return
  openMatchGame.value = game.value === 'valorant' ? 'valorant' : 'dota2'
  openMatchId.value = m.match_id
}

function closeMatch() {
  openMatchId.value = null
  openMatchGame.value = null
}

onMounted(load)
watch(() => [route.params.game, route.params.externalId], () => load())
</script>

<template>
  <div class="guest-profile">
    <div v-if="loading" class="state-message">Загружаем профиль...</div>
    <div v-else-if="error" class="state-message error-state">{{ error }}</div>

    <template v-else-if="profile">
      <div class="profile-header card">
        <div
          class="avatar-big"
          :style="profile.avatar_url ? { backgroundImage: `url(${profile.avatar_url})` } : {}"
        >
          <span v-if="!profile.avatar_url">?</span>
        </div>
        <div class="header-info">
          <h1 v-if="profile.display_name">{{ profile.display_name }}</h1>
          <h1 v-else class="anon-name">Скрытый профиль</h1>
          <span class="external-badge">{{ sourceLabel }}</span>
          <div class="header-actions">
            <button type="button" class="btn-secondary" @click="toggleFav">
              {{ isFav ? '★ В избранном' : '☆ В избранное' }}
            </button>
            <button type="button" class="btn-secondary" @click="goCompare">
              Сравнить с собой
            </button>
            <button
              v-if="profile.is_gamehub_user"
              type="button"
              class="gh-link-btn"
              @click="goToFullProfile"
            >
              Полный профиль GameEyes →
            </button>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="stats-row">
          <div class="stat-box">
            <span class="stat-value win">{{ profile.wins ?? 0 }}</span>
            <span class="stat-label">побед</span>
          </div>
          <div class="stat-box">
            <span class="stat-value loss">{{ profile.losses ?? 0 }}</span>
            <span class="stat-label">поражений</span>
          </div>
          <div class="stat-box" v-if="winrate != null">
            <span class="stat-value accent">{{ winrate }}%</span>
            <span class="stat-label">винрейт</span>
          </div>
          <div class="stat-box" v-if="profile.mmr_estimate">
            <span class="stat-value accent">{{ profile.mmr_estimate }}</span>
            <span class="stat-label">MMR</span>
          </div>
          <div class="stat-box" v-if="profile.tier">
            <span class="stat-value accent">{{ profile.tier }}</span>
            <span class="stat-label">ранг</span>
          </div>
          <div class="stat-box" v-if="profile.rr != null && profile.rr !== ''">
            <span class="stat-value accent">{{ profile.rr }}</span>
            <span class="stat-label">RR</span>
          </div>
        </div>

        <div class="heroes-section" v-if="profile.top_heroes?.length">
          <h4>{{ game === 'valorant' ? 'Любимые агенты' : 'Любимые герои' }}</h4>
          <div class="hero-row" v-for="h in profile.top_heroes" :key="h.name">
            <span class="hero-name">{{ h.name }}</span>
            <span class="hero-games">{{ h.games }} игр</span>
            <span
              v-if="h.winrate"
              class="hero-winrate"
              :class="{ good: h.winrate >= 50 }"
            >{{ h.winrate }}%</span>
          </div>
        </div>
      </div>

      <div class="card" v-if="profile.match_history?.length">
        <h4 class="section-title">История матчей</h4>
        <div
          v-for="(m, i) in visibleHistory"
          :key="m.match_id || i"
          class="match-row"
          :class="{ win: m.won === true, loss: m.won === false, clickable: !!m.match_id }"
          @click="openMatch(m)"
        >
          <span class="match-result">{{ m.won ? 'W' : 'L' }}</span>
          <div class="match-info">
            <span class="match-title">{{ m.title }}</span>
            <span class="match-meta">
              {{ m.played_at }}
              <template v-if="m.duration"> · {{ m.duration }}</template>
            </span>
          </div>
          <span class="match-kda">{{ m.subtitle }}</span>
          <span v-if="m.match_id" class="match-chevron">›</span>
        </div>
        <button
          v-if="canExpand"
          type="button"
          class="show-more"
          @click="showMoreHistory"
        >
          Показать ещё
        </button>
      </div>
      <div class="card state-message" v-else>
        История матчей пуста
      </div>
    </template>

    <MatchParticipantsModal
      v-if="openMatchId && openMatchGame === 'dota2'"
      game="dota2"
      :match-id="openMatchId"
      @close="closeMatch"
    />
    <ValorantMatchModal
      v-if="openMatchId && openMatchGame === 'valorant'"
      :match-id="openMatchId"
      @close="closeMatch"
    />
  </div>
</template>

<style scoped>
.guest-profile { display: flex; flex-direction: column; gap: 20px; }
.profile-header { display: flex; align-items: center; gap: 20px; }
.avatar-big {
  width: 72px; height: 72px; border-radius: 50%; background-color: var(--accent-dim);
  background-size: cover; background-position: center; border: 3px solid var(--border-color);
  flex-shrink: 0; display: flex; align-items: center; justify-content: center;
  font-size: 24px; font-weight: 800; color: var(--text-muted);
}
.header-info { display: flex; flex-direction: column; gap: 6px; }
.header-info h1 { margin: 0; font-size: 22px; }
.anon-name { color: var(--text-muted); font-style: italic; }
.external-badge { font-size: 11px; color: var(--text-secondary); }
.header-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
.btn-secondary {
  background: var(--bg-primary); border: 1px solid var(--border-color);
  color: var(--text-primary); padding: 6px 12px; border-radius: 8px;
  font-size: 12px; font-weight: 600; cursor: pointer;
}
.btn-secondary:hover { border-color: var(--accent); color: var(--accent); }
.gh-link-btn {
  background: var(--accent-dim); color: var(--accent); border: none;
  padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; cursor: pointer;
}

.stats-row {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  gap: 8px; margin-bottom: 16px;
}
.stat-box {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  background: var(--bg-primary); border-radius: var(--radius-sm); padding: 10px 6px;
}
.stat-value { font-size: 18px; font-weight: 800; }
.stat-value.win { color: var(--success); }
.stat-value.loss { color: var(--danger); }
.stat-value.accent { color: var(--accent); }
.stat-label { font-size: 10px; color: var(--text-secondary); text-transform: uppercase; }

.heroes-section h4 {
  margin: 0 0 8px; font-size: 12px; color: var(--text-secondary); text-transform: uppercase;
}
.hero-row {
  display: flex; align-items: center; gap: 10px; padding: 7px 0;
  border-bottom: 1px solid var(--border-color); font-size: 13px;
}
.hero-row:last-child { border-bottom: none; }
.hero-name { flex: 1; font-weight: 600; }
.hero-games { color: var(--text-secondary); font-size: 12px; }
.hero-winrate { font-weight: 700; color: var(--danger); }
.hero-winrate.good { color: var(--success); }

.section-title {
  margin: 0 0 12px; font-size: 12px; color: var(--text-secondary); text-transform: uppercase;
}
.match-row {
  display: flex; align-items: center; gap: 12px; padding: 10px 8px;
  border-bottom: 1px solid var(--border-color); font-size: 13px; border-radius: 8px;
}
.match-row.clickable { cursor: pointer; }
.match-row.clickable:hover { background: var(--bg-card-hover); }
.match-result {
  width: 24px; height: 24px; border-radius: 6px; display: flex; align-items: center;
  justify-content: center; font-size: 11px; font-weight: 800; flex-shrink: 0;
}
.match-row.win .match-result { background: rgba(74,222,128,0.15); color: var(--success); }
.match-row.loss .match-result { background: rgba(248,113,113,0.15); color: var(--danger); }
.match-info { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.match-title { font-weight: 700; }
.match-meta { font-size: 11px; color: var(--text-secondary); }
.match-kda { font-family: monospace; color: var(--text-secondary); }
.match-chevron { color: var(--text-muted); font-size: 18px; }
.show-more {
  width: 100%; margin-top: 8px; padding: 10px; background: var(--bg-primary);
  border: 1px solid var(--border-color); border-radius: var(--radius-sm);
  color: var(--accent); font-weight: 600; font-size: 13px; cursor: pointer;
}
.show-more:hover { border-color: var(--accent); }

.state-message {
  padding: 40px 20px; text-align: center; color: var(--text-secondary);
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md);
}
.error-state { color: var(--danger); }
</style>