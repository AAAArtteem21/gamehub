<script setup>
import { ref, onMounted } from 'vue'
import api from '../../api/axios'
import { useChatStore } from '../../stores/chat'
const chatStore = useChatStore()

const emit = defineEmits(['open-thread'])
const threads = ref([])

async function loadThreads() {
  try {
    const res = await api.get('lfg-chat-threads/')
    threads.value = res.data
  } catch (e) {
    threads.value = []
  }
}

onMounted(loadThreads)
defineExpose({ loadThreads })
</script>

<template>
  <div class="chat-sidebar card">
    <h3>Чаты</h3>
    <div class="threads">
      <button
        v-for="t in threads"
        :key="t.post_id"
        class="thread-item"
        
        @click="emit('open-thread', t)"
      >
        <div class="thread-avatar" :class="{ 'has-unread': chatStore.unreadThreads.has(t.post_id) }">
          {{ t.author?.[0]?.toUpperCase() || '?' }}
          <span class="unread-dot" v-if="chatStore.unreadThreads.has(t.post_id)"></span>
        </div>
        <div class="thread-info">
          <span class="thread-game">{{ t.game }}</span>
          <span class="thread-preview">{{ t.last_message || 'Нет сообщений' }}</span>
        </div>
      </button>
      <div v-if="threads.length === 0" class="empty">Пока нет активных чатов</div>
    </div>
  </div>
</template>

<style scoped>
.thread-avatar { position: relative; }
.unread-dot {
  position: absolute; top: -2px; right: -2px;
  width: 10px; height: 10px; background: var(--danger);
  border-radius: 50%; border: 2px solid var(--bg-card);
}

.chat-sidebar {
  display: flex;
  flex-direction: column;
  gap: 14px;
  position: sticky;
  top: 84px;
}
.chat-sidebar h3 { margin: 0; font-size: 14px; }

.threads {
  display: flex;
  flex-direction: column;
}

.thread-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background: none;
  border: none;
  border-bottom: 1px solid var(--border-color);
  padding: 12px 6px;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s var(--ease);
}

.thread-item:first-child {
  border-top: 1px solid var(--border-color);
}

.thread-item:hover {
  background: var(--bg-card-hover);
  border-radius: var(--radius-sm);
}

.thread-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
}

.thread-info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  gap: 2px;
}

.thread-game {
  font-size: 13px;
  font-weight: 700;
}

.thread-preview {
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty {
  font-size: 12px;
  color: var(--text-secondary);
  text-align: center;
  padding: 30px 0;
}
</style>