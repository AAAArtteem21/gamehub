<script setup>
import { ref } from 'vue'
import { clansApi } from '../../api/clans'
import api from '../../api/axios'
import ClanIcon from './ClanIcon.vue'

const emit = defineEmits(['close', 'created'])

const form = ref({
  name: '',
  description: '',
  is_open: true,
  game: 'multigaming',
  max_members: '',
  min_playtime_hours: '',
  join_requirements: '',
})

const games = [
  { value: 'dota2', label: 'Dota 2' },
  { value: 'valorant', label: 'Valorant' },
  { value: 'cs2', label: 'CS2 / Faceit' },
  { value: 'lol', label: 'League of Legends' },
  { value: 'deadlock', label: 'Deadlock' },
  { value: 'multigaming', label: 'Мультигейминг' },
  { value: 'other', label: 'Другое' },
]

const logoFile = ref(null)
const logoPreview = ref('')
const errors = ref({})
const submitting = ref(false)

function onFileChange(e) {
  const file = e.target.files?.[0]
  logoFile.value = null
  logoPreview.value = ''
  if (!file) return
  if (file.size > 2 * 1024 * 1024) {
    errors.value = { logo: ['Максимум 2 МБ'] }
    e.target.value = ''
    return
  }
  logoFile.value = file
  logoPreview.value = URL.createObjectURL(file)
}

function payloadBase() {
  const p = {
    name: form.value.name.trim(),
    description: form.value.description || '',
    is_open: !!form.value.is_open,
    game: form.value.game,
    join_requirements: form.value.join_requirements || '',
  }
  if (form.value.max_members !== '' && form.value.max_members != null) {
    p.max_members = Number(form.value.max_members)
  } else {
    p.max_members = null
  }
  if (form.value.min_playtime_hours !== '' && form.value.min_playtime_hours != null) {
    const n = Number(form.value.min_playtime_hours)
    p.min_playtime_hours = n > 0 ? n : null
  } else {
    p.min_playtime_hours = null
  }
  return p
}

async function submit() {
  submitting.value = true
  errors.value = {}
  try {
    const body = payloadBase()
    const res = await clansApi.create(body)
    if (logoFile.value && res.data?.id) {
      try {
        const fd = new FormData()
        fd.append('logo', logoFile.value)
        const up = await api.post(`clans/${res.data.id}/upload_logo/`, fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        res.data.logo = up.data.logo
        res.data.logo_url = up.data.logo_url
      } catch { /* */ }
    }
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
    <div class="modal card fade-in-up">
      <div class="modal-header">
        <h3>Создать клан</h3>
        <button type="button" class="close-btn" @click="emit('close')">✕</button>
      </div>

      <form class="form" @submit.prevent="submit">
        <div class="preview-row">
          <ClanIcon
            :clan="{ name: form.name || '?', logo: logoPreview, logo_url: logoPreview }"
            :size="56"
          />
          <span class="preview-hint">Предпросмотр</span>
        </div>

        <label>
          Название
          <input v-model="form.name" required minlength="3" maxlength="50" placeholder="Название клана" />
          <span class="error" v-if="errors.name">{{ errors.name[0] || errors.name }}</span>
        </label>

        <label>
          Логотип (необязательно)
          <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" @change="onFileChange" />
        </label>

        <label>
          Описание
          <textarea v-model="form.description" rows="2" maxlength="2000" placeholder="О клане" />
          <span class="error" v-if="errors.description">{{ errors.description[0] }}</span>
        </label>

        <label class="check">
          <input v-model="form.is_open" type="checkbox" />
          Открытый клан (вход без кода)
        </label>
        <p class="hint">Закрытый — только по коду. Код видят лидер и офицеры.</p>

        <label>
          Игра
          <select v-model="form.game">
            <option v-for="g in games" :key="g.value" :value="g.value">{{ g.label }}</option>
          </select>
        </label>

        <label>
          Лимит участников (пусто = без лимита)
          <input v-model="form.max_members" type="number" min="2" max="500" placeholder="Например 20" />
        </label>

        <label>
          Мин. часов в игре для входа
          <input
            v-model="form.min_playtime_hours"
            type="number"
            min="0"
            placeholder="Пусто — без требования"
          />
          <span class="hint">
            Например 1000 для Dota. Считаются часы Steam / привязанный аккаунт.
            Для «Мультигейминг» порог не проверяется.
          </span>
          <span class="error" v-if="errors.min_playtime_hours">{{ errors.min_playtime_hours[0] }}</span>
        </label>

        <label>
          Требования для входа (видят все)
          <textarea
            v-model="form.join_requirements"
            rows="2"
            maxlength="500"
            placeholder="Например: микрофон, 18+, адекват"
          />
          <span class="error" v-if="errors.join_requirements">{{ errors.join_requirements[0] }}</span>
        </label>

        <span class="error" v-if="errors.detail">{{ errors.detail[0] || errors.detail }}</span>
        <span class="error" v-if="errors.non_field_errors">{{ errors.non_field_errors[0] }}</span>

        <button
          type="submit"
          class="btn-primary"
          :disabled="submitting || form.name.trim().length < 3"
        >
          {{ submitting ? 'Создаём...' : 'Создать клан' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.65);
  display: flex; align-items: center; justify-content: center; z-index: 100;
  padding: 16px;
}
.modal { width: 460px; max-width: 100%; max-height: 90vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.modal-header h3 { margin: 0; }
.close-btn { background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 16px; }
.form { display: flex; flex-direction: column; gap: 12px; }
.preview-row { display: flex; align-items: center; gap: 12px; }
.preview-hint { font-size: 12px; color: var(--text-secondary); }
label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--text-secondary); }
label.check { flex-direction: row; align-items: center; gap: 8px; color: var(--text-primary); }
input, textarea, select {
  background: var(--bg-primary); border: 1px solid var(--border-color);
  border-radius: var(--radius-sm); padding: 10px 12px; color: var(--text-primary);
  font-size: 14px; font-family: inherit;
}
.hint { margin: 0; font-size: 11px; color: var(--text-muted); }
.error { color: var(--danger); font-size: 12px; }
.btn-primary {
  background: var(--accent); color: #fff; border: none; padding: 12px;
  border-radius: var(--radius-sm); font-weight: 600; cursor: pointer;
}
.btn-primary:disabled { opacity: 0.6; }
</style>