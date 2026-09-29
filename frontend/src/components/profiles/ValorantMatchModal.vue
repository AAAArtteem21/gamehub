<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/axios'

const props = defineProps({ matchId: [String, Number] })
const emit = defineEmits(['close'])
const router = useRouter()

const data = ref(null)
const loading = ref(true)
const activeRound = ref(0)

const redTeam = computed(() => data.value?.participants?.filter(p => p.team === 'Red') || [])
const blueTeam = computed(() => data.value?.participants?.filter(p => p.team === 'Blue') || [])
const currentRound = computed(() => data.value?.rounds?.[activeRound.value] || null)

function teamRole(team) {
  if (!currentRound.value) return team
  if (currentRound.value.attacking_team === team) return 'Атака'
  if (currentRound.value.defending_team === team) return 'Защита'
  return team
}

function canOpenProfile(p) {
  if (!p) return false
  if (p.is_gamehub_user && p.gamehub_user_id) return true
  if (p.riot_id) return true
  return false
}

async function load() {
  loading.value = true
  try {
    const res = await api.get(`match-participants/valorant/${props.matchId}/`)
    data.value = res.data
    activeRound.value = 0
  } catch (e) {
    data.value = null
  } finally {
    loading.value = false
  }
}

function goToPlayer(p) {
  if (!canOpenProfile(p)) return
  emit('close')
  if (p.is_gamehub_user && p.gamehub_user_id) {
    router.push(`/players/${p.gamehub_user_id}`)
    return
  }
  if (p.riot_id) {
    router.push(`/players/guest/valorant/${encodeURIComponent(p.riot_id)}`)
  }
}

function fmtTime(ms) {
  if (ms == null) return ''
  const totalSec = Math.floor(ms / 1000)
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

onMounted(load)
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="modal card fade-in-up">
      <div class="modal-header">
        <div>
          <h3>Матч — {{ data?.map || 'Valorant' }}</h3>
          <div class="match-meta" v-if="data">
            <span class="v-score-line">
              <span class="v-score red" :class="{ winner: data.red_won }">{{ data.red_score ?? 0 }}</span>
              <span class="v-div">:</span>
              <span class="v-score blue" :class="{ winner: data.blue_won }">{{ data.blue_score ?? 0 }}</span>
            </span>
            <span class="v-winner" v-if="data.red_won">Победа Red</span>
            <span class="v-winner" v-else-if="data.blue_won">Победа Blue</span>
          </div>
        </div>
        <button class="close-btn" type="button" @click="emit('close')">✕</button>
      </div>

      <div v-if="loading" class="state">Загружаем матч...</div>
      <div v-else-if="!data" class="state">Не удалось получить данные матча</div>

      <template v-else>
        <div class="teams-grid">
          <div class="team-col red-col">
            <div class="team-header">
              <span class="team-label">Red · {{ teamRole('Red') }}</span>
              <span class="team-score">{{ data.red_score ?? 0 }}</span>
            </div>
            <div class="team-players">
              <div
                v-for="p in redTeam"
                :key="p.riot_id || p.display_name"
                class="player-card"
                :class="{ clickable: canOpenProfile(p) }"
                @click="goToPlayer(p)"
              >
                <img v-if="p.avatar" :src="p.avatar" class="p-avatar" alt="" />
                <div v-else class="p-avatar placeholder">{{ p.display_name?.[0]?.toUpperCase() }}</div>
                <div class="p-info">
                  <div class="p-top">
                    <span class="p-name">{{ p.display_name }}</span>
                    <span class="gh-badge" v-if="p.is_gamehub_user">на GameHub</span>
                  </div>
                  <div class="p-agent">{{ p.agent }}</div>
                  <div class="p-kda">{{ p.kda }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="team-col blue-col">
            <div class="team-header">
              <span class="team-label">Blue · {{ teamRole('Blue') }}</span>
              <span class="team-score">{{ data.blue_score ?? 0 }}</span>
            </div>
            <div class="team-players">
              <div
                v-for="p in blueTeam"
                :key="p.riot_id || p.display_name"
                class="player-card"
                :class="{ clickable: canOpenProfile(p) }"
                @click="goToPlayer(p)"
              >
                <img v-if="p.avatar" :src="p.avatar" class="p-avatar" alt="" />
                <div v-else class="p-avatar placeholder">{{ p.display_name?.[0]?.toUpperCase() }}</div>
                <div class="p-info">
                  <div class="p-top">
                    <span class="p-name">{{ p.display_name }}</span>
                    <span class="gh-badge" v-if="p.is_gamehub_user">на GameHub</span>
                  </div>
                  <div class="p-agent">{{ p.agent }}</div>
                  <div class="p-kda">{{ p.kda }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="rounds-wrap" v-if="data.rounds?.length">
          <div class="rounds-title">По раундам</div>
          <div class="round-tabs">
            <button
              v-for="(r, idx) in data.rounds"
              :key="idx"
              type="button"
              class="round-tab"
              :class="{
                active: activeRound === idx,
                'win-red': r.winning_team === 'Red',
                'win-blue': r.winning_team === 'Blue',
              }"
              @click="activeRound = idx"
            >
              <span class="r-num">{{ r.round_number }}</span>
              <span class="r-dot" :class="String(r.winning_team || '').toLowerCase()"></span>
            </button>
          </div>

          <div class="round-role-bar" v-if="currentRound">
            <span class="role-pill attack">Атака · {{ currentRound.attacking_team }}</span>
            <span class="role-pill defense">Защита · {{ currentRound.defending_team }}</span>
            <span class="role-pill plant" v-if="currentRound.plant_time != null">
              💣 Спайк {{ currentRound.plant_site || '' }} · {{ fmtTime(currentRound.plant_time) }}
            </span>
          </div>

          <div class="round-body" v-if="currentRound">
            <div
              v-if="!(currentRound.events || currentRound.kills)?.length"
              class="no-kills"
            >Нет событий в этом раунде</div>

            <div
              v-for="(ev, i) in (currentRound.events || currentRound.kills)"
              :key="i"
              class="kill-row"
              :class="{
                'side-attack': ev.side === 'attack',
                'side-defense': ev.side === 'defense',
                'is-plant': ev.type === 'plant',
              }"
            >
              <template v-if="ev.type === 'plant'">
                <div class="plant-row">
                  <span class="plant-icon">💣</span>
                  <span class="plant-text">Спайк установлен · сайт {{ ev.site }}</span>
                  <span class="k-time">{{ fmtTime(ev.time_in_round) }}</span>
                  <span class="plant-by">{{ ev.planter }}</span>
                </div>
              </template>

              <template v-else>
                <div class="side killer">
                  <img v-if="ev.killer_avatar" :src="ev.killer_avatar" class="k-avatar" alt="" />
                  <div v-else class="k-avatar placeholder">{{ ev.killer?.[0]?.toUpperCase() }}</div>
                  <div class="k-names">
                    <span class="k-name">{{ ev.killer }}</span>
                    <span class="k-agent">{{ ev.killer_agent }}</span>
                  </div>
                </div>

                <div class="k-action">
                  <span class="k-weapon">{{ ev.weapon || '?' }}</span>
                  <span class="k-headshot" v-if="ev.headshot" title="Хэдшот">🎯</span>
                  <span class="k-time">{{ fmtTime(ev.time_in_round) }}</span>
                </div>

                <div class="side victim">
                  <div class="k-names right">
                    <span class="k-name">{{ ev.victim }}</span>
                    <span class="k-agent">{{ ev.victim_agent }}</span>
                  </div>
                  <img v-if="ev.victim_avatar" :src="ev.victim_avatar" class="k-avatar" alt="" />
                  <div v-else class="k-avatar placeholder dead">{{ ev.victim?.[0]?.toUpperCase() }}</div>
                </div>
              </template>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: flex-start;   /* НЕ center — иначе «низко» */
  justify-content: center;
  padding: max(32px, 6vh) 16px 48px;
  background: rgba(0, 0, 0, 0.78);
  backdrop-filter: blur(8px);
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.modal {
  width: min(960px, 100%);
  max-width: 960px;
  flex-shrink: 0;
  margin: 0 auto;
  max-height: none;          /* скролл у оверлея, не у модалки */
  overflow: visible;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px 22px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.55);
  position: relative;
  /* без transform здесь — fade-in-up может глючить с fixed */
}

.modal.fade-in-up {
  animation: modalIn 0.25s var(--ease) both;
}

@keyframes modalIn {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.modal-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 18px; position: sticky; top: 0; background: var(--bg-card); padding-bottom: 10px; z-index: 2;
}
.modal-header h3 { margin: 0 0 4px; font-size: 16px; }
.close-btn { background: none; border: none; color: var(--text-secondary); font-size: 18px; cursor: pointer; }

.match-meta { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: 4px; }
.v-score-line {
  display: flex; align-items: center; gap: 5px;
  background: var(--bg-primary); border: 1px solid var(--border-color);
  padding: 3px 10px; border-radius: 20px;
}
.v-score { font-size: 15px; font-weight: 800; font-family: monospace; }
.v-score.red { color: #FF4655; }
.v-score.blue { color: #3A9BDC; }
.v-score.winner { color: var(--success); }
.v-div { color: var(--text-muted); font-weight: 700; }
.v-winner {
  font-size: 11px; font-weight: 700; color: var(--success);
  background: rgba(74,222,128,0.12); padding: 2px 8px; border-radius: 20px;
}

.state { text-align: center; color: var(--text-secondary); padding: 40px 0; font-size: 13px; }

.teams-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
@media (max-width: 640px) { .teams-grid { grid-template-columns: 1fr; } }

.team-col { display: flex; flex-direction: column; gap: 6px; }
.team-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 10px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 800;
}
.red-col .team-header {
  background: rgba(255,70,85,0.1); color: #FF4655; border: 1px solid rgba(255,70,85,0.2);
}
.blue-col .team-header {
  background: rgba(58,155,220,0.1); color: #3A9BDC; border: 1px solid rgba(58,155,220,0.2);
}

.team-players { display: flex; flex-direction: column; gap: 5px; }
.player-card {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; background: var(--bg-primary); border: 1px solid var(--border-color);
  border-radius: var(--radius-sm); transition: border-color 0.15s var(--ease);
}
.player-card.clickable { cursor: pointer; }
.player-card.clickable:hover { border-color: var(--accent); }
.p-avatar {
  width: 36px; height: 36px; border-radius: 6px; flex-shrink: 0;
  object-fit: cover; background: var(--bg-card-hover);
}
.p-avatar.placeholder {
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: var(--text-muted);
}
.p-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.p-top { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }
.p-name { font-weight: 700; font-size: 12px; }
.gh-badge {
  font-size: 9px; background: var(--accent-dim); color: var(--accent);
  padding: 1px 6px; border-radius: 8px; font-weight: 700;
}
.p-agent { font-size: 10px; color: var(--text-secondary); }
.p-kda { font-size: 11px; font-family: monospace; color: var(--text-muted); }

.rounds-wrap { margin-top: 4px; }
.rounds-title {
  font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;
  color: var(--text-secondary); margin-bottom: 8px;
}
.round-tabs { display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 10px; }
.round-tab {
  display: flex; align-items: center; gap: 5px;
  background: var(--bg-primary); border: 1px solid var(--border-color);
  color: var(--text-secondary); font-size: 11px; font-weight: 600;
  padding: 5px 10px; border-radius: var(--radius-sm); cursor: pointer;
  transition: all 0.15s var(--ease);
}
.round-tab:hover { color: var(--text-primary); border-color: var(--border-hover); }
.round-tab.active { background: var(--accent); color: white; border-color: var(--accent); }
.round-tab.win-red:not(.active) { border-color: rgba(255,70,85,0.4); color: #FF4655; }
.round-tab.win-blue:not(.active) { border-color: rgba(58,155,220,0.4); color: #3A9BDC; }
.r-dot { width: 5px; height: 5px; border-radius: 50%; }
.r-dot.red { background: #FF4655; }
.r-dot.blue { background: #3A9BDC; }

.round-role-bar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.role-pill { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 20px; }
.role-pill.attack { background: rgba(255,70,85,0.15); color: #FF4655; }
.role-pill.defense { background: rgba(58,155,220,0.15); color: #3A9BDC; }
.role-pill.plant { background: rgba(251,191,36,0.15); color: #fbbf24; }

.round-body { display: flex; flex-direction: column; gap: 5px; }
.no-kills { text-align: center; color: var(--text-muted); font-size: 12px; padding: 16px 0; }

.kill-row {
  display: flex; align-items: center; justify-content: space-between;
  gap: 8px; padding: 7px 10px; background: var(--bg-primary);
  border: 1px solid var(--border-color); border-radius: var(--radius-sm);
  border-left: 3px solid transparent;
}
.kill-row.side-attack { border-left-color: #FF4655; }
.kill-row.side-defense { border-left-color: #3A9BDC; }
.kill-row.is-plant { border-left-color: #fbbf24; background: rgba(251,191,36,0.06); }

.side { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0; }
.side.victim { justify-content: flex-end; }
.k-avatar {
  width: 24px; height: 24px; border-radius: 5px; flex-shrink: 0;
  object-fit: cover; background: var(--bg-card-hover);
}
.k-avatar.placeholder {
  display: flex; align-items: center; justify-content: center;
  font-size: 9px; font-weight: 700; color: var(--text-muted);
}
.k-avatar.placeholder.dead { background: rgba(248,113,113,0.15); color: var(--danger); }
.k-names { display: flex; flex-direction: column; min-width: 0; }
.k-names.right { align-items: flex-end; text-align: right; }
.k-name { font-size: 11px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.k-agent { font-size: 9px; color: var(--text-secondary); }
.k-action {
  display: flex; align-items: center; gap: 6px; flex-shrink: 0;
  background: var(--bg-card); padding: 3px 8px; border-radius: 20px;
  border: 1px solid var(--border-color);
}
.k-weapon { font-size: 10px; font-weight: 600; color: var(--text-primary); }
.k-headshot { font-size: 12px; line-height: 1; }
.k-time { font-size: 9px; color: var(--text-muted); font-family: monospace; }

.plant-row {
  display: flex; align-items: center; gap: 8px; width: 100%;
  font-size: 11px; font-weight: 600; color: #fbbf24;
}
.plant-icon { font-size: 14px; }
.plant-text { flex: 1; }
.plant-by { color: var(--text-secondary); font-size: 10px; }
</style>