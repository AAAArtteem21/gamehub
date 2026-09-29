<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/axios'

const props = defineProps({
  game: { type: String, default: 'dota2' },
  matchId: { type: [String, Number], required: true },
})
const emit = defineEmits(['close'])
const router = useRouter()

const participants = ref([])
const radiantWin = ref(null)
const duration = ref(null)
const loading = ref(true)
const matchData = ref({})
const activeRound = ref(0)

const resolvedGame = computed(() => {
  const g = String(props.game || 'dota2').toLowerCase()
  if (!g || g === 'undefined' || g === 'null' || g === 'opendota') return 'dota2'
  return g
})

const isValorant = computed(() => resolvedGame.value === 'valorant')
const redTeam = computed(() => participants.value.filter(p => p.team === 'Red' || p.team === 'red'))
const blueTeam = computed(() => participants.value.filter(p => p.team === 'Blue' || p.team === 'blue'))
const radiantPlayers = computed(() => participants.value.filter(p => p.is_radiant))
const direPlayers = computed(() => participants.value.filter(p => !p.is_radiant))

function canOpenProfile(p) {
  if (!p) return false
  if (p.is_gamehub_user && p.gamehub_user_id) return true
  if (p.account_id) return true
  if (p.riot_id) return true
  return false
}

async function load() {
  loading.value = true
  try {
    const res = await api.get(
      `match-participants/${resolvedGame.value}/${props.matchId}/`
    )
    participants.value = res.data.participants || []
    radiantWin.value = res.data.radiant_win
    duration.value = res.data.duration
    matchData.value = {
      map: res.data.map,
      red_won: res.data.red_won,
      blue_won: res.data.blue_won,
      red_score: res.data.red_score,
      blue_score: res.data.blue_score,
      rounds: res.data.rounds || [],
    }
    activeRound.value = 0
  } catch (e) {
    participants.value = []
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
  if (resolvedGame.value === 'dota2' && p.account_id) {
    router.push(`/players/guest/dota2/${p.account_id}`)
    return
  }
  if (resolvedGame.value === 'valorant' && p.riot_id) {
    router.push(`/players/guest/valorant/${encodeURIComponent(p.riot_id)}`)
  }
}

function fmtDuration(sec) {
  if (!sec) return ''
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function formatTime(ms) {
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
    <div class="modal card fade-in-up" :class="{ 'valorant-modal': isValorant }">
      <div class="modal-header">
        <div>
          <h3>Участники матча</h3>
          <span class="match-meta" v-if="!isValorant && duration">
            {{ fmtDuration(duration) }} ·
            <span :class="radiantWin ? 'radiant-text' : 'dire-text'">
              {{ radiantWin ? 'Победа Radiant' : 'Победа Dire' }}
            </span>
          </span>
          <span class="match-meta valorant-meta" v-if="isValorant">
            <span class="v-map">{{ matchData.map || 'Карта' }}</span>
            <span class="v-score-line">
              <span class="v-score red" :class="{ winner: matchData.red_won }">{{ matchData.red_score ?? 0 }}</span>
              <span class="v-score-div">:</span>
              <span class="v-score blue" :class="{ winner: matchData.blue_won }">{{ matchData.blue_score ?? 0 }}</span>
            </span>
            <span class="v-winner-tag" v-if="matchData.red_won">Победа Red</span>
            <span class="v-winner-tag" v-else-if="matchData.blue_won">Победа Blue</span>
          </span>
        </div>
        <button class="close-btn" type="button" @click="emit('close')">✕</button>
      </div>

      <div v-if="loading" class="state">Загружаем участников...</div>
      <div v-else-if="participants.length === 0" class="state">Не удалось получить участников</div>

      <!-- VALORANT -->
      <template v-else-if="isValorant">
        <div class="v-teams">
          <div class="v-team red-side">
            <div class="v-team-header">
              <span>Red</span>
              <span>{{ matchData.red_score ?? 0 }}</span>
            </div>
            <div
              v-for="p in redTeam"
              :key="p.riot_id || p.display_name"
              class="v-player-card"
              :class="{ clickable: canOpenProfile(p) }"
              @click="goToPlayer(p)"
            >
              <img v-if="p.avatar" :src="p.avatar" class="v-player-avatar" alt="" />
              <div v-else class="v-player-avatar placeholder">{{ p.display_name?.[0]?.toUpperCase() }}</div>
              <div class="v-player-info">
                <div class="v-player-top">
                  <span class="v-player-name">{{ p.display_name }}</span>
                  <span class="gamehub-badge" v-if="p.is_gamehub_user">на GameHub</span>
                </div>
                <div class="v-player-agent">{{ p.agent }}</div>
                <div class="v-player-kda">{{ p.kda }}</div>
              </div>
            </div>
          </div>

          <div class="v-team blue-side">
            <div class="v-team-header">
              <span>Blue</span>
              <span>{{ matchData.blue_score ?? 0 }}</span>
            </div>
            <div
              v-for="p in blueTeam"
              :key="p.riot_id || p.display_name"
              class="v-player-card"
              :class="{ clickable: canOpenProfile(p) }"
              @click="goToPlayer(p)"
            >
              <img v-if="p.avatar" :src="p.avatar" class="v-player-avatar" alt="" />
              <div v-else class="v-player-avatar placeholder">{{ p.display_name?.[0]?.toUpperCase() }}</div>
              <div class="v-player-info">
                <div class="v-player-top">
                  <span class="v-player-name">{{ p.display_name }}</span>
                  <span class="gamehub-badge" v-if="p.is_gamehub_user">на GameHub</span>
                </div>
                <div class="v-player-agent">{{ p.agent }}</div>
                <div class="v-player-kda">{{ p.kda }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="rounds-section" v-if="matchData.rounds?.length">
          <div class="rounds-title">По раундам</div>
          <div class="round-tabs">
            <button
              v-for="(rnd, idx) in matchData.rounds"
              :key="idx"
              type="button"
              class="round-tab"
              :class="{
                active: activeRound === idx,
                'red-win': rnd.winning_team === 'Red',
                'blue-win': rnd.winning_team === 'Blue',
              }"
              @click="activeRound = idx"
            >
              <span>{{ rnd.round_number }}</span>
              <span class="round-dot" :class="String(rnd.winning_team || '').toLowerCase()"></span>
            </button>
          </div>
          <div class="round-kills" v-if="matchData.rounds[activeRound]">
            <div v-if="!(matchData.rounds[activeRound].kills || []).length" class="no-kills">
              Нет убийств в этом раунде
            </div>
            <div
              v-for="(kill, kidx) in (matchData.rounds[activeRound].kills || [])"
              :key="kidx"
              class="kill-row"
            >
              <div class="kill-side">
                <div class="kill-avatar placeholder">{{ kill.killer?.[0]?.toUpperCase() }}</div>
                <div class="kill-names">
                  <span class="kill-name">{{ kill.killer }}</span>
                  <span class="kill-agent">{{ kill.killer_agent }}</span>
                </div>
              </div>
              <div class="kill-action">
                <span class="weapon">{{ kill.weapon || '?' }}</span>
                <span v-if="kill.headshot">🎯</span>
                <span class="kill-time">{{ formatTime(kill.time_in_round) }}</span>
              </div>
              <div class="kill-side victim">
                <div class="kill-names right">
                  <span class="kill-name">{{ kill.victim }}</span>
                  <span class="kill-agent">{{ kill.victim_agent }}</span>
                </div>
                <div class="kill-avatar placeholder victim">{{ kill.victim?.[0]?.toUpperCase() }}</div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- DOTA -->
      <div v-else class="dota-layout">
        <div class="dota-team">
          <div class="dota-team-header radiant">Radiant</div>
          <div
            v-for="(p, i) in radiantPlayers"
            :key="'r-' + (p.account_id || p.hero || i)"
            class="dota-player-card"
            :class="{ clickable: canOpenProfile(p) }"
            @click="goToPlayer(p)"
          >
            <div class="dota-player-top">
              <div class="dota-avatar" :style="p.avatar ? { backgroundImage: `url(${p.avatar})` } : {}">
                <span v-if="!p.avatar">?</span>
              </div>
              <div class="dota-player-title">
                <div class="dota-name-row">
                  <span class="dota-name" v-if="p.display_name">{{ p.display_name }}</span>
                  <span class="dota-name anon" v-else>Скрытый профиль</span>
                  <span class="gamehub-badge" v-if="p.is_gamehub_user">на GameHub</span>
                </div>
                <div class="dota-hero-row">
                  <span class="dota-hero">{{ p.hero }}</span>
                  <span class="dota-level" v-if="p.level">ур. {{ p.level }}</span>
                  <span class="dota-kda">{{ p.kda }}</span>
                </div>
              </div>
            </div>

            <div class="dota-stats">
              <div class="dst"><span>GPM</span><b>{{ p.gpm ?? '—' }}</b></div>
              <div class="dst"><span>XPM</span><b>{{ p.xpm ?? '—' }}</b></div>
              <div class="dst"><span>CS</span><b>{{ (p.last_hits ?? 0) + (p.denies ?? 0) }}</b></div>
              <div class="dst"><span>Net</span><b class="val-gold">{{ p.net_worth ?? '—' }}</b></div>
              <div class="dst"><span>Hero Dmg</span><b class="val-dmg">{{ p.hero_damage ?? '—' }}</b></div>
              <div class="dst"><span>Tower Dmg</span><b>{{ p.tower_damage ?? '—' }}</b></div>
              <div class="dst"><span>Heal</span><b>{{ p.hero_healing ?? '—' }}</b></div>
              <div class="dst"><span>Denies</span><b>{{ p.denies ?? '—' }}</b></div>
            </div>

            <div class="dota-items-row">
              <div class="dota-items">
                <div
                  class="dota-item"
                  v-for="(item, idx) in (p.items || [])"
                  :key="'it-' + idx"
                  :title="item.name"
                >
                  <img v-if="item.icon_url" :src="item.icon_url" :alt="item.name || ''" />
                  <span v-else class="dota-item-fallback">{{ item.name?.slice(0, 2) }}</span>
                </div>
              </div>
              <div class="dota-extra-items">
                <div
                  v-if="p.neutral_item"
                  class="dota-item neutral"
                  :title="p.neutral_item.name || 'Neutral'"
                >
                  <img
                    v-if="p.neutral_item.icon_url"
                    :src="p.neutral_item.icon_url"
                    :alt="p.neutral_item.name || ''"
                  />
                  <span v-else class="dota-item-fallback">N</span>
                </div>
                <span v-if="p.aghanims_scepter" class="buff-pill scepter" title="Aghanim's Scepter">Ага</span>
                <span v-if="p.aghanims_shard" class="buff-pill shard" title="Aghanim's Shard">Шард</span>
                <span v-if="p.moonshard" class="buff-pill moon" title="Moon Shard">Мун</span>
              </div>
            </div>
          </div>
        </div>

        <div class="dota-team">
          <div class="dota-team-header dire">Dire</div>
          <div
            v-for="(p, i) in direPlayers"
            :key="'d-' + (p.account_id || p.hero || i)"
            class="dota-player-card"
            :class="{ clickable: canOpenProfile(p) }"
            @click="goToPlayer(p)"
          >
            <div class="dota-player-top">
              <div class="dota-avatar" :style="p.avatar ? { backgroundImage: `url(${p.avatar})` } : {}">
                <span v-if="!p.avatar">?</span>
              </div>
              <div class="dota-player-title">
                <div class="dota-name-row">
                  <span class="dota-name" v-if="p.display_name">{{ p.display_name }}</span>
                  <span class="dota-name anon" v-else>Скрытый профиль</span>
                  <span class="gamehub-badge" v-if="p.is_gamehub_user">на GameHub</span>
                </div>
                <div class="dota-hero-row">
                  <span class="dota-hero">{{ p.hero }}</span>
                  <span class="dota-level" v-if="p.level">ур. {{ p.level }}</span>
                  <span class="dota-kda">{{ p.kda }}</span>
                </div>
              </div>
            </div>

            <div class="dota-stats">
              <div class="dst"><span>GPM</span><b>{{ p.gpm ?? '—' }}</b></div>
              <div class="dst"><span>XPM</span><b>{{ p.xpm ?? '—' }}</b></div>
              <div class="dst"><span>CS</span><b>{{ (p.last_hits ?? 0) + (p.denies ?? 0) }}</b></div>
              <div class="dst"><span>Net</span><b class="val-gold">{{ p.net_worth ?? '—' }}</b></div>
              <div class="dst"><span>Hero Dmg</span><b class="val-dmg">{{ p.hero_damage ?? '—' }}</b></div>
              <div class="dst"><span>Tower Dmg</span><b>{{ p.tower_damage ?? '—' }}</b></div>
              <div class="dst"><span>Heal</span><b>{{ p.hero_healing ?? '—' }}</b></div>
              <div class="dst"><span>Denies</span><b>{{ p.denies ?? '—' }}</b></div>
            </div>

            <div class="dota-items-row">
              <div class="dota-items">
                <div
                  class="dota-item"
                  v-for="(item, idx) in (p.items || [])"
                  :key="'it-' + idx"
                  :title="item.name"
                >
                  <img v-if="item.icon_url" :src="item.icon_url" :alt="item.name || ''" />
                  <span v-else class="dota-item-fallback">{{ item.name?.slice(0, 2) }}</span>
                </div>
              </div>
              <div class="dota-extra-items">
                <div
                  v-if="p.neutral_item"
                  class="dota-item neutral"
                  :title="p.neutral_item.name || 'Neutral'"
                >
                  <img
                    v-if="p.neutral_item.icon_url"
                    :src="p.neutral_item.icon_url"
                    :alt="p.neutral_item.name || ''"
                  />
                  <span v-else class="dota-item-fallback">N</span>
                </div>
                <span v-if="p.aghanims_scepter" class="buff-pill scepter" title="Aghanim's Scepter">Ага</span>
                <span v-if="p.aghanims_shard" class="buff-pill shard" title="Aghanim's Shard">Шард</span>
                <span v-if="p.moonshard" class="buff-pill moon" title="Moon Shard">Мун</span>
              </div>
            </div>
          </div>
        </div>
      </div>
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
  margin-bottom: 20px; position: sticky; top: 0; background: var(--bg-card); padding-bottom: 12px; z-index: 2;
}
.modal-header h3 { margin: 0 0 4px; font-size: 18px; }
.match-meta { font-size: 12px; color: var(--text-secondary); }
.radiant-text { color: var(--success); font-weight: 700; }
.dire-text { color: var(--danger); font-weight: 700; }
.close-btn { background: none; border: none; color: var(--text-secondary); font-size: 18px; cursor: pointer; }
.state { text-align: center; color: var(--text-secondary); padding: 60px 0; font-size: 13px; }
.gamehub-badge {
  font-size: 10px; font-weight: 700; color: var(--accent);
  background: var(--accent-dim); padding: 2px 8px; border-radius: 20px;
}

.valorant-modal { max-width: 900px; }
.valorant-meta { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.v-map { font-weight: 600; color: var(--text-primary); }
.v-score-line {
  display: flex; align-items: center; gap: 6px;
  background: var(--bg-primary); padding: 4px 12px; border-radius: 20px;
  border: 1px solid var(--border-color);
}
.v-score { font-size: 16px; font-weight: 800; font-family: monospace; }
.v-score.red { color: #ff6b6b; }
.v-score.blue { color: #4dabf7; }
.v-score.winner { color: var(--success); }
.v-score-div { color: var(--text-muted); font-weight: 700; }
.v-winner-tag {
  font-size: 11px; font-weight: 700; color: var(--success);
  background: rgba(74, 222, 128, 0.12); padding: 2px 10px; border-radius: 20px;
}
.v-teams { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 16px; }
@media (max-width: 700px) { .v-teams { grid-template-columns: 1fr; } }
.v-team { display: flex; flex-direction: column; gap: 6px; }
.v-team-header {
  display: flex; justify-content: space-between; padding: 8px 12px;
  border-radius: var(--radius-sm); font-size: 13px; font-weight: 800;
}
.red-side .v-team-header { background: rgba(255,107,107,0.1); color: #ff6b6b; }
.blue-side .v-team-header { background: rgba(77,171,247,0.1); color: #4dabf7; }
.v-player-card {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px;
  background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius-sm);
  transition: border-color 0.15s ease;
}
.v-player-card.clickable { cursor: pointer; }
.v-player-card.clickable:hover { border-color: var(--accent); }
.v-player-avatar {
  width: 40px; height: 40px; border-radius: 8px; object-fit: cover; background: var(--bg-card-hover);
}
.v-player-avatar.placeholder {
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; color: var(--text-muted);
}
.v-player-name { font-weight: 700; font-size: 13px; }
.v-player-agent { font-size: 11px; color: var(--text-secondary); }
.v-player-kda { font-size: 12px; font-family: monospace; color: var(--text-muted); }
.v-player-top { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.v-player-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }

.rounds-title {
  font-size: 12px; font-weight: 800; text-transform: uppercase;
  color: var(--text-secondary); margin-bottom: 8px;
}
.round-tabs { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }
.round-tab {
  display: flex; align-items: center; gap: 6px;
  background: var(--bg-primary); border: 1px solid var(--border-color);
  color: var(--text-secondary); font-size: 12px; font-weight: 600;
  padding: 6px 10px; border-radius: var(--radius-sm); cursor: pointer;
}
.round-tab.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.round-dot { width: 6px; height: 6px; border-radius: 50%; }
.round-dot.red { background: #ff6b6b; }
.round-dot.blue { background: #4dabf7; }
.round-kills { display: flex; flex-direction: column; gap: 6px; }
.no-kills { text-align: center; color: var(--text-muted); font-size: 13px; padding: 16px 0; }
.kill-row {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 8px 12px; background: var(--bg-primary); border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}
.kill-side { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }
.kill-side.victim { justify-content: flex-end; }
.kill-avatar {
  width: 28px; height: 28px; border-radius: 6px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 700; background: var(--bg-card-hover); color: var(--text-muted);
}
.kill-avatar.victim { background: rgba(248,113,113,0.15); color: var(--danger); }
.kill-names { display: flex; flex-direction: column; min-width: 0; }
.kill-names.right { align-items: flex-end; text-align: right; }
.kill-name { font-size: 12px; font-weight: 700; }
.kill-agent { font-size: 10px; color: var(--text-secondary); }
.kill-action {
  display: flex; align-items: center; gap: 8px; flex-shrink: 0;
  background: var(--bg-card); padding: 4px 10px; border-radius: 20px;
  border: 1px solid var(--border-color);
}
.weapon { font-size: 11px; font-weight: 600; }
.kill-time { font-size: 10px; color: var(--text-muted); font-family: monospace; }

.dota-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 800px) { .dota-layout { grid-template-columns: 1fr; } }
.dota-team { display: flex; flex-direction: column; gap: 10px; }
.dota-team-header {
  font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.6px;
  padding: 6px 10px; border-radius: var(--radius-sm);
}
.dota-team-header.radiant {
  color: var(--success); background: rgba(74,222,128,0.08); border: 1px solid rgba(74,222,128,0.15);
}
.dota-team-header.dire {
  color: var(--danger); background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.15);
}
.dota-player-card {
  background: var(--bg-primary); border: 1px solid var(--border-color);
  border-radius: var(--radius-md); padding: 12px;
  transition: border-color 0.15s ease;
}
.dota-player-card.clickable { cursor: pointer; }
.dota-player-card.clickable:hover { border-color: var(--accent); }
.dota-player-top { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.dota-avatar {
  width: 44px; height: 44px; border-radius: 8px; flex-shrink: 0;
  background-color: var(--bg-card-hover); background-size: cover; background-position: center;
  display: flex; align-items: center; justify-content: center;
  color: var(--text-muted); font-weight: 700;
}
.dota-name { font-weight: 700; font-size: 13px; }
.dota-name.anon { color: var(--text-muted); font-style: italic; font-weight: 500; }
.dota-name-row { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.dota-hero-row { display: flex; gap: 8px; font-size: 12px; align-items: center; }
.dota-hero { color: var(--accent); font-weight: 700; }
.dota-level, .dota-kda { color: var(--text-secondary); }
.dota-kda { font-family: monospace; }

.dota-stats {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px 8px; margin-bottom: 10px;
}
.dst {
  display: flex; flex-direction: column;
  background: var(--bg-card); padding: 5px 6px; border-radius: 6px;
  border: 1px solid var(--border-color);
}
.dst span { font-size: 9px; color: var(--text-muted); text-transform: uppercase; }
.dst b { font-size: 12px; font-weight: 700; margin-top: 1px; }
.val-gold { color: #f0c75e !important; }
.val-dmg { color: #f87171 !important; }

.dota-items-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.dota-items { display: flex; flex-wrap: wrap; gap: 5px; }
.dota-extra-items { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }
.dota-item {
  width: 36px; height: 36px; border-radius: 6px; overflow: hidden;
  background: var(--bg-card-hover); border: 1px solid var(--border-color);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.dota-item img { width: 100%; height: 100%; object-fit: cover; }
.dota-item-fallback { font-size: 9px; font-weight: 700; color: var(--text-muted); }
.dota-item.neutral {
  border-color: #a78bfa;
  box-shadow: 0 0 0 1px rgba(167, 139, 250, 0.35);
}
.buff-pill {
  font-size: 10px; font-weight: 800; padding: 3px 7px; border-radius: 6px;
  text-transform: uppercase;
}
.buff-pill.scepter { background: rgba(96, 165, 250, 0.2); color: #60a5fa; }
.buff-pill.shard { background: rgba(167, 139, 250, 0.2); color: #a78bfa; }
.buff-pill.moon { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
</style>