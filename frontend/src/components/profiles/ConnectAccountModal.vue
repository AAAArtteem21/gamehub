<script setup>
import { ref } from 'vue'
import { profilesApi } from '../../api/profiles'

const emit = defineEmits(['close', 'created'])

const platform = ref('steam')
const externalId = ref('')
const errors = ref({})
const submitting = ref(false)

const platforms = [
  { value: 'steam', label: 'Steam', hint: 'Steam ID64 (17 цифр)' },
  { value: 'faceit', label: 'Faceit', hint: 'Player ID или никнейм' },
  { value: 'opendota', label: 'OpenDota (Dota 2)', hint: 'Account ID (число)' },
]

async function submit() {
  submitting.value = true
  errors.value = {}
  try {
    const res = await profilesApi.create({ platform: platform.value, external_id: externalId.value })
    emit('created', res.data)
    emit('close')
  } catch (e) {
    errors.value = e.response?.data || { detail: 'Не удалось подключить аккаунт' }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="modal card">
      <div class="modal-header">
        <h3>Подключить аккаунт</h3>
        <button class="close-btn" @click="emit('close')">✕</button>
      </div>

      <form @submit.prevent="submit" class="form">
        <label>
          Платформа
          <select v-model="platform">
            <option v-for="p in platforms" :key="p.value" :value="p.value">{{ p.label }}</option>
          </select>
        </label>

        <label>
          ID аккаунта
          <input v-model="externalId" :placeholder="platforms.find(p => p.value === platform)?.hint" />
          <span class="error" v-if="errors.external_id">{{ errors.external_id[0] }}</span>
          <span class="error" v-if="errors.platform">{{ errors.platform[0] }}</span>
        </label>

        <span class="error" v-if="errors.detail">{{ errors.detail }}</span>

        <button type="submit" class="btn-primary" :disabled="submitting">
          {{ submitting ? 'Подключаем...' : 'Подключить' }}
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

input, select {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  color: var(--text-primary);
  font-size: 14px;
  font-family: inherit;
}

input:focus, select:focus {
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