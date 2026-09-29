<script setup>
import { ref, computed } from 'vue'
import api from '../../api/axios'
import { PLATFORMS, LOL_PLATFORMS } from '../../constants/platforms'

const emit = defineEmits(['created', 'close'])

const platform = ref('opendota')
const externalId = ref('')
const riotPlatform = ref('euw1')
const loading = ref(false)
const error = ref(null)

const current = computed(() => PLATFORMS.find((p) => p.value === platform.value) || PLATFORMS[0])
const isLol = computed(() => platform.value === 'lol')

async function submit() {
  error.value = null
  const id = externalId.value.trim()
  if (!id) {
    error.value = 'Укажи ID / ник'
    return
  }
  if (platform.value === 'pubg' && !/^\d+$/.test(id)) {
    error.value = 'PUBG: только SteamID64 (цифры)'
    return
  }
  if ((platform.value === 'lol' || platform.value === 'valorant') && !id.includes('#')) {
    error.value = 'Формат Name#Tag'
    return
  }

  loading.value = true
  try {
    const body = { platform: platform.value, external_id: id }
    if (platform.value === 'lol') {
      body.extra_stats = { riot_platform: riotPlatform.value }
    }
    const res = await api.post('game-accounts/', body)
    emit('created', res.data)
    externalId.value = ''
  } catch (e) {
    error.value = e.response?.data?.detail || e.response?.data?.platform?.[0] || 'Не удалось подключить'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <form class="connect-form" @submit.prevent="submit">
    <label>
      Игра
      <select v-model="platform">
        <option v-for="p in PLATFORMS" :key="p.value" :value="p.value">{{ p.label }}</option>
      </select>
    </label>

    <label v-if="isLol">
      Регион LoL
      <select v-model="riotPlatform">
        <option v-for="r in LOL_PLATFORMS" :key="r.value" :value="r.value">{{ r.label }}</option>
      </select>
    </label>

    <label>
      {{ current.label }} ID
      <input v-model="externalId" type="text" :placeholder="current.placeholder" />
      <span v-if="current.hint" class="hint">{{ current.hint }}</span>
    </label>

    <p v-if="error" class="error">{{ error }}</p>
    <button type="submit" class="btn-primary" :disabled="loading">
      {{ loading ? 'Подключаем…' : 'Подключить' }}
    </button>
  </form>
</template>

<style scoped>
.connect-form { display: flex; flex-direction: column; gap: 12px; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--text-secondary); }
input, select {
  background: var(--bg-primary); border: 1px solid var(--border-color);
  border-radius: var(--radius-sm); padding: 10px 12px; color: var(--text-primary); font-size: 14px;
}
.hint { font-size: 11px; color: var(--text-muted); }
.error { color: var(--danger); font-size: 12px; margin: 0; }
.btn-primary {
  background: var(--accent); color: #fff; border: none; padding: 12px;
  border-radius: var(--radius-sm); font-weight: 600; cursor: pointer;
}
.btn-primary:disabled { opacity: 0.6; }
</style>