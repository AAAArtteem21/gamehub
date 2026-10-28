<script setup>
import { ref, watch, onMounted } from 'vue'
import { friendsApi } from '../../api/friends'
import { useAuthStore } from '../../stores/auth'

const props = defineProps({
  userId: { type: [Number, String], required: true },
})

const auth = useAuthStore()
const relation = ref('none') // none | outgoing | incoming | friends | self
const requestId = ref(null)
const loading = ref(false)
const error = ref('')

async function load() {
  error.value = ''
  if (!auth.isAuthenticated) {
    relation.value = 'none'
    return
  }
  try {
    const res = await friendsApi.relation(props.userId)
    relation.value = res.data.relation || 'none'
    requestId.value = res.data.request_id || null
  } catch {
    relation.value = 'none'
  }
}

async function send() {
  if (!auth.requireAuth?.('Войди через Steam, чтобы добавить в друзья.')) return
  loading.value = true
  error.value = ''
  try {
    await friendsApi.sendRequest(props.userId)
    relation.value = 'outgoing'
  } catch (e) {
    error.value =
      e.response?.data?.detail ||
      e.response?.data?.user_id?.[0] ||
      'Не удалось отправить заявку'
    await load()
  } finally {
    loading.value = false
  }
}

async function accept() {
  if (!requestId.value) return
  loading.value = true
  error.value = ''
  try {
    await friendsApi.acceptRequest(requestId.value)
    relation.value = 'friends'
    requestId.value = null
  } catch (e) {
    error.value = e.response?.data?.detail || 'Не удалось принять'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.userId, load)
</script>

<template>
  <div v-if="relation !== 'self'" class="af">
    <button
      v-if="relation === 'none'"
      type="button"
      class="btn-secondary af-btn"
      :disabled="loading"
      @click="send"
    >
      {{ loading ? '…' : 'В друзья' }}
    </button>

    <span v-else-if="relation === 'outgoing'" class="af-badge">Заявка отправлена</span>

    <button
      v-else-if="relation === 'incoming'"
      type="button"
      class="btn-secondary af-btn"
      :disabled="loading"
      @click="accept"
    >
      {{ loading ? '…' : 'Принять заявку' }}
    </button>

    <span v-else-if="relation === 'friends'" class="af-badge ok">В друзьях</span>

    <p v-if="error" class="af-err">{{ error }}</p>
  </div>
</template>

<style scoped>
.af {
  display: inline-flex;
  flex-direction: column;
  gap: 4px;
}
.af-btn {
  border-color: var(--accent) !important;
  color: var(--accent) !important;
}
.af-badge {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  padding: 8px 4px;
}
.af-badge.ok {
  color: var(--success);
}
.af-err {
  margin: 0;
  font-size: 11px;
  color: var(--danger);
}
</style>