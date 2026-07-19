<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import api from '../../api/axios'
import { useAuthStore } from '../../stores/auth'
import { useChatStore } from '../../stores/chat'

const props = defineProps({ post: Object })
const emit = defineEmits(['close'])

const authStore = useAuthStore()
const chatStore = useChatStore()

const messages = ref([])
const newMessage = ref('')
const messagesEnd = ref(null)

let pollInterval = null

async function loadMessages() {
  const res = await api.get('lfg-chat/', {
    params: { post: props.post.id }
  })

  messages.value = res.data.results || res.data

  // Отмечаем чат как прочитанный
  if (messages.value.length) {
    chatStore.markAsRead(
      props.post.id,
      messages.value[messages.value.length - 1].created_at
    )
  }

  await nextTick()
  messagesEnd.value?.scrollIntoView({ behavior: 'smooth' })
}

async function sendMessage() {
  const text = newMessage.value.trim()
  if (!text) return

  newMessage.value = ''

  await api.post('lfg-chat/', {
    post: props.post.id,
    text
  })

  await loadMessages()
}

onMounted(() => {
  loadMessages()
  pollInterval = setInterval(loadMessages, 4000)
})

onUnmounted(() => {
  clearInterval(pollInterval)
})
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="chat-modal card fade-in-up">
      <div class="modal-header">
        <h3>Чат — {{ post.game }}</h3>
        <button class="close-btn" @click="emit('close')">✕</button>
      </div>

      <div class="messages">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="message"
          :class="{ own: msg.sender_username === authStore.user?.username }"
        >
          <div class="msg-avatar" :style="msg.sender_avatar ? { backgroundImage: `url(${msg.sender_avatar})` } : {}">
            <span v-if="!msg.sender_avatar">{{ msg.sender_username?.[0]?.toUpperCase() }}</span>
          </div>
          <div class="msg-body">
            <div class="msg-top">
              <span class="sender">{{ msg.sender_username }}</span>
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
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.modal-header h3 { margin: 0; font-size: 15px; }
.close-btn { background: none; border: none; color: var(--text-secondary); font-size: 16px; cursor: pointer; }

.messages { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; padding-right: 4px; }

.message { display: flex; gap: 10px; }
.message.own { flex-direction: row-reverse; }
.message.own .msg-body { align-items: flex-end; }
.message.own .text { background: var(--accent-dim); }

.msg-avatar {
  width: 30px; height: 30px; border-radius: 50%; flex-shrink: 0;
  background-color: var(--accent-dim); background-size: cover; background-position: center;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: var(--accent);
}

.msg-body { display: flex; flex-direction: column; gap: 3px; max-width: 78%; }
.msg-top { display: flex; gap: 8px; align-items: baseline; }
.sender { font-weight: 700; color: var(--accent); font-size: 11px; }
.time { font-size: 10px; color: var(--text-muted); }
.text { background: var(--bg-primary); padding: 8px 10px; border-radius: 10px; font-size: 13px; color: var(--text-primary); }

.empty { text-align: center; color: var(--text-secondary); padding: 40px 0; font-size: 13px; }

.input-row { display: flex; gap: 8px; margin-top: 12px; }
.input-row input { flex: 1; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 10px 12px; color: var(--text-primary); font-size: 13px; }
.input-row input:focus { outline: none; border-color: var(--accent); }
.send-btn { background: var(--accent); color: white; border: none; width: 40px; border-radius: var(--radius-sm); cursor: pointer; font-size: 16px; }
</style>