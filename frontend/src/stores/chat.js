import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/axios'

export const useChatStore = defineStore('chat', () => {
  const unreadThreads = ref(new Set())
  const lastSeenTimestamps = ref({})
  let pollInterval = null
  let audioUnlocked = false

  const notifSound = new Audio('/sounds/notify.mp3')

  function unlockAudio() {
    if (audioUnlocked) return
    notifSound.play().then(() => {
      notifSound.pause()
      notifSound.currentTime = 0
      audioUnlocked = true
    }).catch(() => {})
  }

  async function checkNewMessages() {
    try {
      const res = await api.get('lfg-chat-threads/')
      for (const thread of res.data) {
        const lastSeen = lastSeenTimestamps.value[thread.post_id]
        if (thread.last_message_at && (!lastSeen || new Date(thread.last_message_at) > new Date(lastSeen))) {
          if (lastSeen) {
            unreadThreads.value.add(thread.post_id)
            notifSound.currentTime = 0
            notifSound.play().catch(() => {})
          }
          lastSeenTimestamps.value[thread.post_id] = thread.last_message_at
        }
      }
    } catch (e) { /* тихо игнорируем сетевые сбои polling */ }
  }

  function markAsRead(postId, timestamp) {
    unreadThreads.value.delete(postId)
    lastSeenTimestamps.value[postId] = timestamp
  }

  function startPolling() {
    checkNewMessages()
    pollInterval = setInterval(checkNewMessages, 5000)
  }

  function stopPolling() {
    clearInterval(pollInterval)
  }

  return { unreadThreads, markAsRead, startPolling, stopPolling, unlockAudio }
})