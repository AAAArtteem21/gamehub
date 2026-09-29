<script setup>
import { ref } from 'vue'
import { clansApi } from '../../api/clans'
import api from '../../api/axios'
import ClanIcon from './ClanIcon.vue'

const emit = defineEmits(['close', 'created'])
const form = ref({ name: '', description: '' })
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
  errors.value = { ...errors.value, logo: undefined }
}

async function submit() {
  submitting.value = true
  errors.value = {}
  try {
    // С файлом — multipart; без — обычный JSON
    let res
    if (logoFile.value) {
      const fd = new FormData()
      fd.append('name', form.value.name.trim())
      if (form.value.description) fd.append('description', form.value.description)
      fd.append('logo', logoFile.value)
      res = await api.post('clans/', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    } else {
      res = await clansApi.create({
        name: form.value.name.trim(),
        description: form.value.description || '',
      })
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
        <button class="close-btn" @click="emit('close')">✕</button>
      </div>

      <form @submit.prevent="submit" class="form">
        <div class="preview-row">
          <ClanIcon
            :clan="{ name: form.name || '?', logo: logoPreview, logo_url: logoPreview }"
            :size="56"
          />
          <span class="preview-hint">Предпросмотр иконки</span>
        </div>

        <label>
          Название
          <input v-model="form.name" placeholder="Название клана" required minlength="3" />
          <span class="error" v-if="errors.name">{{ Array.isArray(errors.name) ? errors.name[0] : errors.name }}</span>
        </label>

        <label>
          Логотип (необязательно)
          <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" @change="onFileChange" />
          <span class="hint">JPEG, PNG, WebP, GIF · до 2 МБ. Если не указано — цветная иконка по названию</span>
          <span class="error" v-if="errors.logo">{{ Array.isArray(errors.logo) ? errors.logo[0] : errors.logo }}</span>
        </label>

        <label>
          Описание
          <textarea v-model="form.description" rows="3" placeholder="Кратко о клане"></textarea>
        </label>

        <span class="error" v-if="errors.detail">
          {{ Array.isArray(errors.detail) ? errors.detail[0] : errors.detail }}
        </span>
        <span class="error" v-if="errors.non_field_errors">
          {{ errors.non_field_errors[0] }}
        </span>

        <button type="submit" class="btn-primary" :disabled="submitting || form.name.trim().length < 3">
          {{ submitting ? 'Создаём...' : 'Создать клан' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.65); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal { width: 440px; max-width: 90vw; }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.modal-header h3 { margin: 0; }
.close-btn { background: none; border: none; color: var(--text-secondary); font-size: 16px; cursor: pointer; }
.form { display: flex; flex-direction: column; gap: 14px; }

.preview-row { display: flex; align-items: center; gap: 12px; padding: 8px 0; }
.preview-hint { font-size: 12px; color: var(--text-secondary); }

label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--text-secondary); }
input, textarea {
  background: var(--bg-primary); border: 1px solid var(--border-color);
  border-radius: var(--radius-sm); padding: 10px 12px; color: var(--text-primary);
  font-size: 14px; font-family: inherit; resize: vertical;
}
input[type="file"] { padding: 8px; }
input:focus, textarea:focus { outline: none; border-color: var(--accent); }
.hint { font-size: 11px; color: var(--text-muted); }
.error { color: var(--danger); font-size: 12px; }
.btn-primary {
  background: var(--accent); color: white; border: none; padding: 12px;
  border-radius: var(--radius-sm); font-weight: 600; font-size: 14px; cursor: pointer; margin-top: 6px;
}
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
</style>