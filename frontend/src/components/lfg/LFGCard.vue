<script setup>
import { ref } from 'vue'
import GameIcon from './GameIcon.vue'

const props = defineProps({ post: Object, onRespond: Function })
const emit = defineEmits(['open-chat'])

const state = ref('idle') // idle | loading | done | error

function formatDate(dt) {
  return new Date(dt).toLocaleString('ru-RU', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

function timeUntil(dt) {
  const diff = new Date(dt) - new Date()
  if (diff < 0) return 'уже началось'
  const hours = Math.floor(diff / 1000 / 60 / 60)
  if (hours < 1) return 'скоро'
  if (hours < 24) return `через ${hours} ч`
  return `через ${Math.floor(hours / 24)} дн`
}

async function handleRespond() {
  if (state.value !== 'idle') return
  state.value = 'loading'
  try {
    await props.onRespond(props.post.id)
    state.value = 'done'
  } catch (e) {
    state.value = 'error'
    setTimeout(() => { state.value = 'idle' }, 2000)
  }
}
</script>

<template>
  <div class="lfg-card fade-in-up" :class="{ closed: post.status === 'closed' }">
    <GameIcon :game="post.game" />

    <div class="lfg-main">
      <div class="lfg-top">
        <span class="lfg-game-name">{{ post.game }}</span>
        <div class="badges">
          <span class="slots-badge">{{ post.responses_count }}/{{ post.slots_needed }} игроков</span>
          <span v-if="post.status === 'closed'" class="closed-badge">Заявка закрыта</span>
          <span v-else class="lfg-time-badge">{{ timeUntil(post.datetime) }}</span>
        </div>
      </div>

      <p class="lfg-description" v-if="post.description">{{ post.description }}</p>
      <p class="lfg-description muted" v-else>Без описания</p>

      <div class="lfg-meta">
        <RouterLink :to="`/players/${post.author_id}`" class="author-link">
          <div
            class="author-avatar"
            :style="post.author_avatar ? { backgroundImage: `url(${post.author_avatar})` } : {}"
          >
            <span v-if="!post.author_avatar">{{ post.author?.[0]?.toUpperCase() }}</span>
          </div>
          <span>{{ post.author }}</span>
        </RouterLink>
        <span class="meta-item">🕐 {{ formatDate(post.datetime) }}</span>
      </div>

      <div class="contact-row" v-if="post.contact">
        <span class="contact-label">Контакт:</span>
        <span class="contact-value">{{ post.contact }}</span>
      </div>
      <div class="contact-row locked" v-else-if="post.status !== 'closed' && !post.is_author">
        <span class="lock-icon">🔒</span> Контакт откроется после отклика
      </div>
    </div>

    <div class="lfg-actions">
      <button
        v-if="post.status === 'open' && !post.is_author && !post.has_responded"
        class="btn-respond"
        :class="state"
        @click="handleRespond"
        :disabled="state === 'loading' || state === 'done'"
      >
        <span v-if="state === 'idle'">Откликнуться</span>
        <span v-else-if="state === 'loading'" class="spinner"></span>
        <span v-else-if="state === 'done'">✓ Отправлено</span>
        <span v-else-if="state === 'error'">Ошибка</span>
      </button>

      <button
        v-if="post.has_responded || post.is_author"
        class="btn-chat"
        @click="emit('open-chat', post)"
      >
        💬 Чат
      </button>
    </div>
  </div>
</template>

<style scoped>
.lfg-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 18px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  transition: border-color 0.25s var(--ease), transform 0.25s var(--ease), box-shadow 0.25s var(--ease);
}

.lfg-card:hover {
  border-color: var(--border-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.lfg-card.closed {
  opacity: 0.6;
}

.lfg-main {
  flex: 1;
  min-width: 0;
}

.lfg-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  gap: 10px;
}

.lfg-game-name {
  font-weight: 700;
  font-size: 15px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.badges {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-shrink: 0;
}

.slots-badge {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-primary);
  background: var(--bg-card-hover);
  padding: 3px 9px;
  border-radius: 20px;
}

.lfg-time-badge {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-dim);
  padding: 3px 8px;
  border-radius: 20px;
}

.closed-badge {
  font-size: 11px;
  font-weight: 700;
  color: var(--danger);
  background: rgba(248, 113, 113, 0.12);
  padding: 3px 9px;
  border-radius: 20px;
}

.lfg-description {
  font-size: 13px;
  color: var(--text-primary);
  margin: 0 0 10px;
  line-height: 1.4;
}

.lfg-description.muted {
  color: var(--text-secondary);
  font-style: italic;
}

.lfg-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.author-link {
  display: flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
  color: var(--text-secondary);
  font-size: 12px;
  transition: color 0.15s var(--ease);
}

.author-link:hover {
  color: var(--accent);
}

.author-avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: var(--accent-dim);
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  color: var(--accent);
  flex-shrink: 0;
}

.meta-item {
  font-size: 12px;
  color: var(--text-secondary);
}

.contact-row {
  font-size: 12px;
  padding: 8px 10px;
  background: var(--bg-primary);
  border-radius: 8px;
  display: flex;
  gap: 6px;
  align-items: center;
}

.contact-label {
  color: var(--text-secondary);
}

.contact-value {
  color: var(--success);
  font-weight: 600;
}

.contact-row.locked {
  color: var(--text-muted);
}

.lock-icon {
  font-size: 11px;
}

.lfg-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}

.btn-respond {
  background: transparent;
  border: 1px solid var(--accent);
  color: var(--accent);
  padding: 9px 18px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  min-width: 128px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s var(--ease), color 0.2s var(--ease), box-shadow 0.2s var(--ease);
}

.btn-respond:hover:not(:disabled) {
  background: var(--accent);
  color: white;
  box-shadow: var(--shadow-glow);
}

.btn-respond.done {
  background: rgba(74, 222, 128, 0.12);
  border-color: var(--success);
  color: var(--success);
  cursor: default;
}

.btn-respond.error {
  border-color: var(--danger);
  color: var(--danger);
}

.btn-respond:disabled {
  cursor: default;
}

.btn-chat {
  background: var(--bg-card-hover);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 9px 18px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  min-width: 128px;
  height: 36px;
  transition: border-color 0.2s var(--ease);
}

.btn-chat:hover {
  border-color: var(--border-hover);
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(230, 57, 70, 0.3);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
</style>