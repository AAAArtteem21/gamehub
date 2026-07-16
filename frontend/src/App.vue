<script setup>
import api from './api/axios'
import { ref, onMounted } from 'vue'

const status = ref('checking...')

onMounted(async () => {
  try {
    await api.get('csrf/')
    status.value = 'Backend connected ✅'
  } catch (e) {
    status.value = 'Backend NOT connected ❌'
  }
})
</script>

<template>
  <div>{{ status }}</div>
</template>