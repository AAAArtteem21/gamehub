<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import api from '../../api/axios'
import { useAuthStore } from '../../stores/auth'

const props = defineProps({ post: Object })
const emit = defineEmits(['close'])
const authStore = useAuthStore()

const messages = ref([])
const newMessage = ref('')
const messagesEnd = ref(null)
const isLive = ref(false)

let socket = null
let pollInterval = null
let fallbackTimer = null

async function loadInitialMessages() {
  const res = await api.get('lfg-chat/', { params: { post: props.post.id } })
  messages.value = res.data.results || res.data
  await nextTick()
  scrollToEnd()
}

function scrollToEnd() {
  messagesEnd.value?.scrollIntoView({ behavior: 'smooth' })
}

function connectSocket() {
  const token = authStore.token
  const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const wsHost = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host

  socket = new WebSocket(`${wsProtocol}://${wsHost}/ws/lfg-chat/${props.post.id}/?token=${token}`)

  fallbackTimer = setTimeout(() => {
    if (!isLive.value) {
      socket?.close()
      startPollingFallback()
    }
  }, 3000)

  socket.onopen = () => {
    isLive.value = true
    clearTimeout(fallbackTimer)
  }

  socket.onmessage = async (event) => {
    const data = JSON.parse(event.data)
    messages.value.push(data)
    await nextTick()
    scrollToEnd()
  }

  socket.onclose = () => {
    if (isLive.value) {
      isLive.value = false
      startPollingFallback()
    }
  }

  socket.onerror = () => {
    clearTimeout(fallbackTimer)
    startPollingFallback()
  }
}

function startPollingFallback() {
  if (pollInterval) return
  pollInterval = setInterval(loadInitialMessages, 4000)
}

async function sendMessage() {
  const text = newMessage.value.trim()
  if (!text) return

  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ text }))
    newMessage.value = ''
  } else {
    // fallback — отправка через обычный REST, как было раньше
    newMessage.value = ''
    await api.post('lfg-chat/', { post: props.post.id, text })
    await loadInitialMessages()
  }
}

onMounted(async () => {
  await loadInitialMessages()
  connectSocket()
})

onUnmounted(() => {
  clearTimeout(fallbackTimer)
  clearInterval(pollInterval)
  socket?.close()
})
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="chat-modal card fade-in-up">
      <div class="modal-header">
        <div class="header-title">
          <h3>Чат — {{ post.game }}</h3>
          <span class="live-indicator" :class="{ live: isLive }">
            {{ isLive ? '🟢 реалтайм' : '🟡 обновление раз в 4с' }}
          </span>
        </div>
        <button class="close-btn" @click="emit('close')">✕</button>
      </div>

      <div class="messages">
        <div
          v-for="msg in messages" :key="msg.id"
          class="message" :class="{ own: msg.sender_username === authStore.user?.username }"
        >
          <RouterLink :to="`/players/${msg.sender_id}`" class="msg-avatar-link" @click="emit('close')">
            <div class="msg-avatar" :style="msg.sender_avatar ? { backgroundImage: `url(${msg.sender_avatar})` } : {}">
              <span v-if="!msg.sender_avatar">{{ msg.sender_username?.[0]?.toUpperCase() }}</span>
            </div>
          </RouterLink>
          <div class="msg-body">
            <div class="msg-top">
              <RouterLink :to="`/players/${msg.sender_id}`" class="sender" @click="emit('close')">
                {{ msg.sender_username }}
              </RouterLink>
              <span class="time">{{ new Date(msg.created_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) }}</span>
            </div>
            <span class="text">{{ msg.text }}</span>
          </div>
        </div>
        <div v-if="messages.length === 0" class="empty">Пока нет сообщений — напиши первым</div>
        <div ref="messagesEnd"></div>
      </div>

      <form class="input-row" @submit.prevent="sendMessage">
        <input v-model="newMessage" placeholder="Написать сообщение..." />
        <button type="submit" class="send-btn">→</button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.65); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 100; }
.chat-modal { width: 460px; max-width: 90vw; height: 580px; display: flex; flex-direction: column; }
.modal-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
.header-title { display: flex; flex-direction: column; gap: 2px; }
.modal-header h3 { margin: 0; font-size: 15px; }
.live-indicator { font-size: 10px; color: var(--text-muted); }
.live-indicator.live { color: var(--success); }
.close-btn { background: none; border: none; color: var(--text-secondary); font-size: 16px; cursor: pointer; }

.messages { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; padding-right: 4px; }
.message { display: flex; gap: 10px; }
.message.own { flex-direction: row-reverse; }
.message.own .msg-body { align-items: flex-end; }
.message.own .text { background: var(--accent-dim); }

.msg-avatar-link { flex-shrink: 0; }
.msg-avatar {
  width: 30px; height: 30px; border-radius: 50%;
  background-color: var(--accent-dim); background-size: cover; background-position: center;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: var(--accent);
}

.msg-body { display: flex; flex-direction: column; gap: 3px; max-width: 78%; }
.msg-top { display: flex; gap: 8px; align-items: baseline; }
.sender { font-weight: 700; color: var(--accent); font-size: 11px; text-decoration: none; }
.sender:hover { text-decoration: underline; }
.time { font-size: 10px; color: var(--text-muted); }
.text { background: var(--bg-primary); padding: 8px 10px; border-radius: 10px; font-size: 13px; color: var(--text-primary); }

.empty { text-align: center; color: var(--text-secondary); padding: 40px 0; font-size: 13px; }

.input-row { display: flex; gap: 8px; margin-top: 12px; }
.input-row input { flex: 1; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 10px 12px; color: var(--text-primary); font-size: 13px; }
.input-row input:focus { outline: none; border-color: var(--accent); }
.send-btn { background: var(--accent); color: white; border: none; width: 40px; border-radius: var(--radius-sm); cursor: pointer; font-size: 16px; }
</style>