<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/axios'

const props = defineProps({ game: String, matchId: [String, Number] })
const emit = defineEmits(['close'])
const router = useRouter()

const participants = ref([])
const radiantWin = ref(null)
const duration = ref(null)
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    const res = await api.get(`match-participants/${props.game}/${props.matchId}/`)
    participants.value = res.data.participants
    radiantWin.value = res.data.radiant_win
    duration.value = res.data.duration
  } catch (e) {
    participants.value = []
  } finally {
    loading.value = false
  }
}

function goToPlayer(p) {
  if (!p.is_gamehub_user) return
  emit('close')
  router.push(`/players/${p.gamehub_user_id}`)
}

function fmtDuration(sec) {
  if (!sec) return ''
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

onMounted(load)
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="modal card fade-in-up">
      <div class="modal-header">
        <div>
          <h3>Участники матча</h3>
          <span class="match-meta" v-if="duration">
            {{ fmtDuration(duration) }} ·
            <span :class="radiantWin ? 'radiant-text' : 'dire-text'">
              {{ radiantWin ? 'Победа Radiant' : 'Победа Dire' }}
            </span>
          </span>
        </div>
        <button class="close-btn" @click="emit('close')">✕</button>
      </div>

      <div v-if="loading" class="state">Загружаем участников...</div>
      <div v-else-if="participants.length === 0" class="state">Не удалось получить участников</div>

      <div v-else class="teams">
        <div class="team">
          <span class="team-label radiant">Radiant</span>
          <div
            v-for="p in participants.filter(p => p.is_radiant)" :key="p.account_id || p.hero + Math.random()"
            class="player-card" :class="{ clickable: p.is_gamehub_user }"
            @click="goToPlayer(p)"
          >
            <div class="player-avatar" :style="p.avatar ? { backgroundImage: `url(${p.avatar})` } : {}">
              <span v-if="!p.avatar">?</span>
            </div>
            <div class="player-main">
              <div class="player-top">
                <span class="player-name" v-if="p.display_name">{{ p.display_name }}</span>
                <span class="player-name anon" v-else>Скрытый профиль</span>
                <span class="gamehub-badge" v-if="p.is_gamehub_user">на GameHub</span>
              </div>
              <div class="player-hero-row">
                <span class="player-hero">{{ p.hero }}</span>
                <span class="player-level" v-if="p.level">ур. {{ p.level }}</span>
                <span class="player-kda">{{ p.kda }}</span>
              </div>
              <div class="player-stats-grid">
                <div class="pstat"><span>GPM</span><b>{{ p.gpm ?? '—' }}</b></div>
                <div class="pstat"><span>XPM</span><b>{{ p.xpm ?? '—' }}</b></div>
                <div class="pstat"><span>CS</span><b>{{ (p.last_hits ?? 0) + (p.denies ?? 0) }}</b></div>
                <div class="pstat"><span>Net Worth</span><b>{{ p.net_worth ?? '—' }}</b></div>
                <div class="pstat"><span>Урон герою</span><b>{{ p.hero_damage ?? '—' }}</b></div>
                <div class="pstat"><span>Урон башням</span><b>{{ p.tower_damage ?? '—' }}</b></div>
                <div class="pstat"><span>Лечение</span><b>{{ p.hero_healing ?? '—' }}</b></div>
              </div>
              <div class="player-items" v-if="p.items?.length">
                <span class="item-chip" v-for="(item, idx) in p.items" :key="idx">{{ item }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="team">
          <span class="team-label dire">Dire</span>
          <div
            v-for="p in participants.filter(p => !p.is_radiant)" :key="p.account_id || p.hero + Math.random()"
            class="player-card" :class="{ clickable: p.is_gamehub_user }"
            @click="goToPlayer(p)"
          >
            <div class="player-avatar" :style="p.avatar ? { backgroundImage: `url(${p.avatar})` } : {}">
              <span v-if="!p.avatar">?</span>
            </div>
            <div class="player-main">
              <div class="player-top">
                <span class="player-name" v-if="p.display_name">{{ p.display_name }}</span>
                <span class="player-name anon" v-else>Скрытый профиль</span>
                <span class="gamehub-badge" v-if="p.is_gamehub_user">на GameHub</span>
              </div>
              <div class="player-hero-row">
                <span class="player-hero">{{ p.hero }}</span>
                <span class="player-level" v-if="p.level">ур. {{ p.level }}</span>
                <span class="player-kda">{{ p.kda }}</span>
              </div>
              <div class="player-stats-grid">
                <div class="pstat"><span>GPM</span><b>{{ p.gpm ?? '—' }}</b></div>
                <div class="pstat"><span>XPM</span><b>{{ p.xpm ?? '—' }}</b></div>
                <div class="pstat"><span>CS</span><b>{{ (p.last_hits ?? 0) + (p.denies ?? 0) }}</b></div>
                <div class="pstat"><span>Net Worth</span><b>{{ p.net_worth ?? '—' }}</b></div>
                <div class="pstat"><span>Урон герою</span><b>{{ p.hero_damage ?? '—' }}</b></div>
                <div class="pstat"><span>Урон башням</span><b>{{ p.tower_damage ?? '—' }}</b></div>
                <div class="pstat"><span>Лечение</span><b>{{ p.hero_healing ?? '—' }}</b></div>
              </div>
              <div class="player-items" v-if="p.items?.length">
                <span class="item-chip" v-for="(item, idx) in p.items" :key="idx">{{ item }}</span>
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
  position: fixed; inset: 0; background: rgba(0,0,0,0.75); backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center; z-index: 100; padding: 24px;
}
.modal {
  width: 100%; max-width: 1100px; height: 90vh; overflow-y: auto;
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

.teams { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
@media (max-width: 800px) { .teams { grid-template-columns: 1fr; } }

.team { display: flex; flex-direction: column; gap: 10px; }
.team-label { font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; }
.team-label.radiant { color: var(--success); }
.team-label.dire { color: var(--danger); }

.player-card {
  display: flex; gap: 12px; padding: 14px; border-radius: var(--radius-md);
  background: var(--bg-primary); border: 1px solid var(--border-color);
  transition: border-color 0.15s var(--ease);
}
.player-card.clickable { cursor: pointer; }
.player-card.clickable:hover { border-color: var(--accent); }

.player-avatar {
  width: 52px; height: 52px; border-radius: 10px; flex-shrink: 0;
  background-color: var(--bg-card-hover); background-size: cover; background-position: center;
  display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-weight: 700;
}

.player-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6px; }
.player-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.player-name { font-weight: 700; font-size: 14px; }
.player-name.anon { color: var(--text-muted); font-style: italic; font-weight: 500; }
.gamehub-badge { font-size: 10px; background: var(--accent-dim); color: var(--accent); padding: 2px 8px; border-radius: 10px; font-weight: 700; }

.player-hero-row { display: flex; align-items: center; gap: 10px; font-size: 12px; }
.player-hero { color: var(--accent); font-weight: 700; }
.player-level { color: var(--text-secondary); }
.player-kda { font-family: monospace; color: var(--text-secondary); }

.player-stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px 10px; }
.pstat { display: flex; flex-direction: column; }
.pstat span { font-size: 9px; color: var(--text-muted); text-transform: uppercase; }
.pstat b { font-size: 12px; font-weight: 700; }

.player-items { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 2px; }
.item-chip { font-size: 10px; background: var(--bg-card-hover); color: var(--text-secondary); padding: 2px 7px; border-radius: 6px; }
</style>