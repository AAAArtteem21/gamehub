<script setup>
import { ref } from 'vue'
import { clansApi } from '../../api/clans'

const emit = defineEmits(['close', 'joined'])

const inviteCode = ref('')
const error = ref('')
const submitting = ref(false)

async function submit() {
  submitting.value = true
  error.value = ''
  try {
    await clansApi.join(inviteCode.value.trim())
    emit('joined')
    emit('close')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Не удалось вступить в клан'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="modal card">
      <div class="modal-header">
        <h3>Вступить в клан</h3>
        <button class="close-btn" @click="emit('close')">✕</button>
      </div>

      <form @submit.prevent="submit" class="form">
        <label>
          Код приглашения
          <input v-model="inviteCode" placeholder="Например: a1b2c3d4" />
        </label>
        <span class="error" v-if="error">{{ error }}</span>
        <button type="submit" class="btn-primary" :disabled="submitting">
          {{ submitting ? 'Вступаем...' : 'Вступить' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal { width: 380px; max-width: 90vw; }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.modal-header h3 { margin: 0; }
.close-btn { background: none; border: none; color: var(--text-secondary); font-size: 16px; cursor: pointer; }
.form { display: flex; flex-direction: column; gap: 14px; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--text-secondary); }
input { background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 10px 12px; color: var(--text-primary); font-size: 14px; }
input:focus { outline: none; border-color: var(--accent); }
.error { color: var(--danger); font-size: 12px; }
.btn-primary { background: var(--accent); color: white; border: none; padding: 12px; border-radius: var(--radius-sm); font-weight: 600; font-size: 14px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
</style>