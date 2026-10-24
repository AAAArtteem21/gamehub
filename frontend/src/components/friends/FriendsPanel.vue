<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { friendsApi } from '../../api/friends'
import { useAuthStore } from '../../stores/auth'
import { useToast } from '../../composables/useToast'

const props = defineProps({ open: Boolean })
const emit = defineEmits(['close'])

const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const tab = ref('friends')
const friends = ref([])
const incoming = ref([])
const outgoing = ref([])
const suggestions = ref([])
const presence = ref({ status: 'offline', note: '', game: '' })
const loading = ref(false)
const acting = ref(null)

const STATUS_OPTS = [
  { id: 'free', label: 'Свободен', color: '#6aaa7c' },
  { id: 'ranked', label: 'Рейтинг', color: '#e8b84a' },
  { id: 'lfg', label: 'Ищу тим', color: '#5b8def' },
  { id: 'offline', label: 'Не в сети', color: '#888' },
]

async function loadAll() {
  if (!auth.isAuthenticated) return
  loading.value = true
  try {
    const [p, f, r, s] = await Promise.all([
      friendsApi.getPresence(),
      friendsApi.list(),
      friendsApi.requests(),
      friendsApi.suggestions(),
    ])
    presence.value = p.data
    friends.value = f.data || []
    incoming.value = r.data?.incoming || []
    outgoing.value = r.data?.outgoing || []
    suggestions.value = s.data || []
  } catch {
    /* */
  } finally {
    loading.value = false
  }
}

async function setStatus(id) {
  try {
    const res = await friendsApi.setPresence({
      status: id,
      note: presence.value.note || '',
      game: presence.value.game || '',
    })
    presence.value = res.data
    toast.success('Статус обновлён')
  } catch {
    toast.error('Не удалось сменить статус')
  }
}

async function accept(req) {
  acting.value = req.id
  try {
    await friendsApi.acceptRequest(req.id)
    toast.success('Теперь вы друзья')
    await loadAll()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Ошибка')
  } finally {
    acting.value = null
  }
}

async function reject(req) {
  acting.value = req.id
  try {
    await friendsApi.rejectRequest(req.id)
    await loadAll()
  } finally {
    acting.value = null
  }
}

async function addSuggested(user) {
  acting.value = user.id
  try {
    await friendsApi.sendRequest(user.id)
    toast.success('Заявка отправлена')
    user.request_sent = true
  } catch (e) {
    toast.error(
      e.response?.data?.detail || e.response?.data?.user_id?.[0] || 'Ошибка'
    )
  } finally {
    acting.value = null
  }
}

async function invite(user) {
  acting.value = user.id
  try {
    await friendsApi.invite(user.id, {
      message: 'Пойдём поиграем?',
      game: presence.value.game || '',
    })
    toast.success('Приглашение отправлено')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Не удалось')
  } finally {
    acting.value = null
  }
}

async function removeFriend(user) {
  if (!confirm(`Удалить «${user.username}» из друзей?`)) return
  try {
    await friendsApi.unfriend(user.id)
    toast.success('Удалён из друзей')
    await loadAll()
  } catch {
    toast.error('Ошибка')
  }
}

function openProfile(id) {
  emit('close')
  router.push(`/players/${id}`)
}

function statusMeta(st) {
  return STATUS_OPTS.find((o) => o.id === st) || STATUS_OPTS[3]
}

watch(
  () => props.open,
  (v) => {
    if (v) loadAll()
  }
)
onMounted(() => {
  if (props.open) loadAll()
})
</script>

<template>
  <div v-if="open" class="fp-backdrop" @click.self="emit('close')">
    <div class="fp-panel" role="dialog" aria-label="Друзья">
      <header class="fp-head">
        <h2>Друзья</h2>
        <button type="button" class="fp-x" aria-label="Закрыть" @click="emit('close')">
          ✕
        </button>
      </header>

      <div class="fp-status">
        <span class="fp-status-label">Мой статус</span>
        <div class="fp-status-row">
          <button
            v-for="o in STATUS_OPTS"
            :key="o.id"
            type="button"
            class="st-chip"
            :class="{ active: presence.status === o.id }"
            :style="
              presence.status === o.id
                ? { borderColor: o.color, color: o.color }
                : {}
            "
            @click="setStatus(o.id)"
          >
            <span class="dot" :style="{ background: o.color }" />
            {{ o.label }}
          </button>
        </div>
      </div>

      <nav class="fp-tabs">
        <button type="button" :class="{ on: tab === 'friends' }" @click="tab = 'friends'">
          Друзья
          <span v-if="friends.length" class="n">{{ friends.length }}</span>
        </button>
        <button type="button" :class="{ on: tab === 'requests' }" @click="tab = 'requests'">
          Заявки
          <span v-if="incoming.length" class="n alert">{{ incoming.length }}</span>
        </button>
        <button
          type="button"
          :class="{ on: tab === 'suggestions' }"
          @click="tab = 'suggestions'"
        >
          Знакомые
        </button>
      </nav>

      <div class="fp-body">
        <div v-if="loading" class="fp-empty">Загрузка…</div>

        <template v-else-if="tab === 'friends'">
          <div v-if="!friends.length" class="fp-empty">
            Пока нет друзей — загляни во «Знакомые»
          </div>
          <div v-for="u in friends" :key="u.id" class="row">
            <button type="button" class="row-main" @click="openProfile(u.id)">
              <div
                class="av"
                :style="
                  u.avatar_url ? { backgroundImage: `url(${u.avatar_url})` } : {}
                "
              >
                <span v-if="!u.avatar_url">{{ u.username?.[0]?.toUpperCase() }}</span>
                <i
                  class="av-dot"
                  :style="{ background: statusMeta(u.presence?.status).color }"
                />
              </div>
              <div class="meta">
                <span class="name">{{ u.username }}</span>
                <span class="sub">
                  {{ statusMeta(u.presence?.status).label }}
                  <template v-if="u.presence?.game"> · {{ u.presence.game }}</template>
                </span>
              </div>
            </button>
            <div class="row-actions">
              <button
                v-if="u.presence?.status !== 'offline'"
                type="button"
                class="btn-inv"
                :disabled="acting === u.id"
                @click="invite(u)"
              >
                Пригласить
              </button>
              <button
                type="button"
                class="btn-more"
                title="Удалить"
                @click="removeFriend(u)"
              >
                ⋯
              </button>
            </div>
          </div>
        </template>

        <template v-else-if="tab === 'requests'">
          <h3 v-if="incoming.length" class="sec">Входящие</h3>
          <div v-for="r in incoming" :key="'i' + r.id" class="row">
            <button type="button" class="row-main" @click="openProfile(r.user.id)">
              <div
                class="av"
                :style="
                  r.user.avatar_url
                    ? { backgroundImage: `url(${r.user.avatar_url})` }
                    : {}
                "
              >
                <span v-if="!r.user.avatar_url">
                  {{ r.user.username?.[0]?.toUpperCase() }}
                </span>
              </div>
              <div class="meta">
                <span class="name">{{ r.user.username }}</span>
                <span v-if="r.message" class="sub">{{ r.message }}</span>
              </div>
            </button>
            <div class="row-actions">
              <button
                type="button"
                class="btn-ok"
                :disabled="acting === r.id"
                @click="accept(r)"
              >
                ✓
              </button>
              <button
                type="button"
                class="btn-no"
                :disabled="acting === r.id"
                @click="reject(r)"
              >
                ✕
              </button>
            </div>
          </div>

          <h3 v-if="outgoing.length" class="sec">Исходящие</h3>
          <div v-for="r in outgoing" :key="'o' + r.id" class="row dim">
            <div class="row-main">
              <div
                class="av"
                :style="
                  r.user.avatar_url
                    ? { backgroundImage: `url(${r.user.avatar_url})` }
                    : {}
                "
              >
                <span v-if="!r.user.avatar_url">
                  {{ r.user.username?.[0]?.toUpperCase() }}
                </span>
              </div>
              <div class="meta">
                <span class="name">{{ r.user.username }}</span>
                <span class="sub">Ожидает ответа</span>
              </div>
            </div>
          </div>

          <div v-if="!incoming.length && !outgoing.length" class="fp-empty">
            Нет заявок
          </div>
        </template>

        <template v-else>
          <p class="hint">Игроки, с которыми ты пересекался в LFG</p>
          <div v-if="!suggestions.length" class="fp-empty">
            Пока пусто — сыграй с кем-то через LFG
          </div>
          <div v-for="u in suggestions" :key="u.id" class="row">
            <button type="button" class="row-main" @click="openProfile(u.id)">
              <div
                class="av"
                :style="
                  u.avatar_url ? { backgroundImage: `url(${u.avatar_url})` } : {}
                "
              >
                <span v-if="!u.avatar_url">{{ u.username?.[0]?.toUpperCase() }}</span>
                <i
                  class="av-dot"
                  :style="{ background: statusMeta(u.presence?.status).color }"
                />
              </div>
              <div class="meta">
                <span class="name">{{ u.username }}</span>
                <span class="sub">{{ statusMeta(u.presence?.status).label }}</span>
              </div>
            </button>
            <button
              v-if="!u.request_sent"
              type="button"
              class="btn-inv"
              :disabled="acting === u.id"
              @click="addSuggested(u)"
            >
              В друзья
            </button>
            <span v-else class="sent">Отправлено</span>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fp-backdrop {
  position: fixed;
  inset: 0;
  z-index: 80;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  justify-content: flex-end;
  align-items: flex-start;
  padding: calc(var(--topbar-h, 64px) + 8px) 12px 12px;
}
.fp-panel {
  width: min(380px, 100%);
  max-height: calc(100vh - var(--topbar-h, 64px) - 24px);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.45);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.fp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-color);
}
.fp-head h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}
.fp-x {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 16px;
  padding: 4px 8px;
}
.fp-status {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}
.fp-status-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}
.fp-status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.st-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 999px;
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  cursor: pointer;
}
.st-chip.active {
  background: transparent;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.fp-tabs {
  display: flex;
  border-bottom: 1px solid var(--border-color);
}
.fp-tabs button {
  flex: 1;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 10px 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
}
.fp-tabs button.on {
  color: var(--text-primary);
  border-bottom-color: var(--accent);
}
.n {
  font-size: 10px;
  font-family: var(--font-mono);
  background: var(--bg-sunken);
  padding: 1px 6px;
  border-radius: 999px;
}
.n.alert {
  background: var(--accent-dim);
  color: var(--accent);
}

.fp-body {
  overflow-y: auto;
  padding: 8px;
  flex: 1;
  min-height: 120px;
}
.fp-empty {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 28px 12px;
}
.hint {
  margin: 4px 8px 10px;
  font-size: 12px;
  color: var(--text-muted);
}
.sec {
  margin: 8px 8px 6px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: var(--radius-sm);
}
.row:hover {
  background: var(--bg-sunken);
}
.row.dim {
  opacity: 0.7;
}
.row-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  text-align: left;
  padding: 0;
}
.av {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  flex-shrink: 0;
  background: var(--accent-dim) center/cover;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: var(--accent);
  font-size: 13px;
  position: relative;
}
.av-dot {
  position: absolute;
  right: -2px;
  bottom: -2px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid var(--bg-card);
}
.meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.name {
  font-weight: 600;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sub {
  font-size: 11px;
  color: var(--text-muted);
}

.row-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
.btn-inv {
  background: var(--accent-dim);
  border: 1px solid var(--accent);
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
  padding: 5px 10px;
  border-radius: 6px;
  cursor: pointer;
}
.btn-inv:disabled {
  opacity: 0.5;
}
.btn-ok,
.btn-no {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 700;
  border: 1px solid var(--border-color);
  background: var(--bg-sunken);
  color: var(--text-primary);
}
.btn-ok {
  color: var(--success);
  border-color: color-mix(in srgb, var(--success) 40%, transparent);
}
.btn-no {
  color: var(--danger);
}
.btn-more {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 8px;
  font-size: 16px;
}
.sent {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
}
</style>