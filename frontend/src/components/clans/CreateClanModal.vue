<script setup>
import { ref } from 'vue'
import { clansApi } from '../../api/clans'

const emit = defineEmits(['close', 'created'])

const form = ref({ name: '', description: '' })
const errors = ref({})
const submitting = ref(false)

async function submit() {
  submitting.value = true
  errors.value = {}
  try {
    const res = await clansApi.create(form.value)
    emit('created', res.data)
    emit('close')
  } catch (e) {
    errors.value = e.response?.data || { detail: 'Не удалось создать клан' }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="modal card">
      <div class="modal-header">
        <h3>Создать клан</h3>
        <button class="close-btn" @click="emit('close')">✕</button>
      </div>

      <form @submit.prevent="submit" class="form">
        <label>
          Название
          <input v-model="form.name" placeholder="Название клана" />
          <span class="error" v-if="errors.name">{{ errors.name[0] }}</span>
        </label>

        <label>
          Описание
          <textarea v-model="form.description" rows="3" placeholder="Кратко о клане"></textarea>
        </label>

        <span class="error" v-if="errors.detail">{{ errors.detail }}</span>

        <button type="submit" class="btn-primary" :disabled="submitting">
          {{ submitting ? 'Создаём...' : 'Создать клан' }}
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

.modal {
  width: 420px;
  max-width: 90vw;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-header h3 {
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

input, textarea {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  color: var(--text-primary);
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
}

input:focus, textarea:focus {
  outline: none;
  border-color: var(--accent);
}

.error {
  color: var(--danger);
  font-size: 12px;
}

.btn-primary {
  background: var(--accent);
  color: white;
  border: none;
  padding: 12px;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  margin-top: 6px;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>