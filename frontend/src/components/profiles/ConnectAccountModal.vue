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
  { value: 'lol', label: 'League of Legends', hint: 'Ник#TAG (Riot ID)' },
  { value: 'valorant', label: 'Valorant', hint: 'Ник#TAG (Riot ID)' },
  { value: 'pubg', label: 'PUBG', hint: 'Ник в PUBG (Steam)' },
  { value: 'roblox', label: 'Roblox', hint: 'Никнейм Roblox' },
  { value: 'fortnite', label: 'Fortnite', hint: 'Никнейм Epic Games' },
]

async function submit() {
  submitting.value = true
  errors.value = {}
  try {
    const res = await profilesApi.create({
      platform: platform.value,
      external_id: externalId.value,
    })
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
  <Teleport to="body">
    <div class="overlay" @click.self="emit('close')">
      <div class="modal card">
        <div class="modal-header">
          <h3>Подключить аккаунт</h3>
          <button type="button" class="close-btn" @click="emit('close')">✕</button>
        </div>

        <form class="form" @submit.prevent="submit">
          <label>
            Платформа
            <select v-model="platform">
              <option
                v-for="p in platforms"
                :key="p.value"
                :value="p.value"
              >
                {{ p.label }}
              </option>
            </select>
          </label>

          <label>
            ID аккаунта
            <input
              v-model="externalId"
              :placeholder="platforms.find((p) => p.value === platform)?.hint"
            />
            <span class="error" v-if="errors.external_id">{{ errors.external_id[0] }}</span>
            <span class="error" v-if="errors.platform">{{ errors.platform[0] }}</span>
          </label>

          <span class="error" v-if="errors.detail">{{ errors.detail }}</span>

          <button type="submit" class="btn-submit" :disabled="submitting">
            {{ submitting ? 'Подключаем...' : 'Подключить' }}
          </button>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(0, 0, 0, 0.72);
  box-sizing: border-box;
}

.modal {
  width: 400px;
  max-width: 100%;
  max-height: min(90vh, 640px);
  overflow-y: auto;
  padding: 20px;
  margin: 0;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.modal-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
  line-height: 1;
  padding: 4px;
}

.close-btn:hover {
  color: var(--text-primary);
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
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}

input,
select {
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  color: var(--text-primary);
  font-size: 13px;
  font-family: inherit;
}

input:focus,
select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--shadow-ring);
}

.error {
  color: var(--danger);
  font-size: 12px;
}

.btn-submit {
  background: var(--accent);
  color: #12100c;
  border: 1px solid var(--accent);
  padding: 11px;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  margin-top: 4px;
  font-family: inherit;
}

.btn-submit:hover:not(:disabled) {
  background: var(--accent-hover);
  border-color: var(--accent-hover);
}

.btn-submit:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
