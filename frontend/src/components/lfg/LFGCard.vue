<script setup>
import { ref } from 'vue'
import GameIcon from './GameIcon.vue'

const props = defineProps({ post: Object, onRespond: Function })
const emit = defineEmits(['open-chat'])

const state = ref('idle')

function formatDate(dt) {
  return new Date(dt).toLocaleString('ru-RU', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
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
    setTimeout(() => {
      state.value = 'idle'
    }, 2000)
  }
}
</script>

<template>
  <div class="lfg-card" :class="{ closed: post.status === 'closed' }">
    <GameIcon :game="post.game" />

    <div class="lfg-main">
      <div class="lfg-top">
        <span class="lfg-game-name">{{ post.game }}</span>
        <div class="badges">
          <span class="slots-badge">
            {{ post.responses_count }}/{{ post.slots_needed }}
          </span>
          <span v-if="post.status === 'closed'" class="closed-badge">Закрыта</span>
          <span v-else class="lfg-time-badge">{{ timeUntil(post.datetime) }}</span>
        </div>
      </div>

      <p class="lfg-description" v-if="post.description">{{ post.description }}</p>
      <p class="lfg-description muted" v-else>Без описания</p>

      <div class="lfg-meta">
        <RouterLink :to="`/players/${post.author_id}`" class="author-link">
          <div
            class="author-avatar"
            :style="
              post.author_avatar
                ? { backgroundImage: `url(${post.author_avatar})` }
                : {}
            "
          >
            <span v-if="!post.author_avatar">
              {{ post.author?.[0]?.toUpperCase() }}
            </span>
          </div>
          <span>{{ post.author }}</span>
        </RouterLink>
        <span class="meta-item">{{ formatDate(post.datetime) }}</span>
      </div>

      <div class="contact-row" v-if="post.contact">
        <span class="contact-label">Контакт</span>
        <span class="contact-value">{{ post.contact }}</span>
      </div>
      <div
        class="contact-row locked"
        v-else-if="post.status !== 'closed' && !post.is_author"
      >
        Контакт после отклика
      </div>
    </div>

    <div class="lfg-actions">
      <button
        v-if="post.status === 'open' && !post.is_author && !post.has_responded"
        type="button"
        class="btn-respond"
        :class="state"
        :disabled="state === 'loading' || state === 'done'"
        @click.stop="handleRespond"
      >
        <span v-if="state === 'idle'">Откликнуться</span>
        <span v-else-if="state === 'loading'" class="spinner"></span>
        <span v-else-if="state === 'done'">Отправлено</span>
        <span v-else-if="state === 'error'">Ошибка</span>
      </button>

      <button
        v-if="post.has_responded || post.is_author"
        type="button"
        class="btn-chat"
        @click.stop="emit('open-chat', post)"
      >
        Чат
      </button>
    </div>
  </div>
</template>

<style scoped>
.lfg-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}
.lfg-card.closed {
  opacity: 0.55;
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
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.02em;
}

.badges {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-shrink: 0;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.slots-badge,
.lfg-time-badge,
.closed-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: var(--radius-sm);
}

.slots-badge {
  color: var(--text-primary);
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  font-family: var(--font-mono);
}
.lfg-time-badge {
  color: var(--accent);
  background: var(--accent-dim);
  border: 1px solid rgba(196, 165, 116, 0.25);
}
.closed-badge {
  color: var(--danger);
  background: rgba(201, 122, 114, 0.12);
}

.lfg-description {
  font-size: 13px;
  color: var(--text-primary);
  margin: 0 0 10px;
  line-height: 1.4;
}
.lfg-description.muted {
  color: var(--text-muted);
  font-style: italic;
}

.lfg-meta {
  display: flex;
  align-items: center;
  gap: 14px;
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
}
.author-link:hover {
  color: var(--accent);
}
.author-avatar {
  width: 20px;
  height: 20px;
  border-radius: 4px;
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
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.contact-row {
  font-size: 12px;
  padding: 7px 10px;
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  display: flex;
  gap: 8px;
  align-items: center;
}
.contact-label {
  color: var(--text-muted);
}
.contact-value {
  color: var(--success);
  font-weight: 600;
  font-family: var(--font-mono);
}
.contact-row.locked {
  color: var(--text-muted);
}

.lfg-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
}

.btn-respond {
  background: transparent;
  border: 1px solid var(--accent);
  color: var(--accent);
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  min-width: 120px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.btn-respond:hover:not(:disabled) {
  background: var(--accent);
  color: #12100c;
}
.btn-respond.done {
  background: rgba(106, 170, 124, 0.12);
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
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  min-width: 120px;
  height: 34px;
}
.btn-chat:hover {
  border-color: var(--border-hover);
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(196, 165, 116, 0.25);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>