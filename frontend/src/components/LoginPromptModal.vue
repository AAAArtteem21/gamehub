<script setup>
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()
</script>

<template>
  <div v-if="auth.loginPromptOpen" class="overlay" @click.self="auth.loginPromptOpen = false">
    <div class="box">
      <h3>Нужен вход</h3>
      <p>{{ auth.loginPromptReason || 'Это действие доступно только после входа.' }}</p>
      <button class="btn" @click="auth.loginWithSteam()">Войти через Steam</button>
      <button class="cancel" @click="auth.loginPromptOpen = false">Не сейчас</button>
    </div>
  </div>
</template>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,.65); display: flex;
  align-items: center; justify-content: center; z-index: 200; padding: 16px; }
.box { background: var(--bg-card); border: 1px solid var(--border-color);
  border-radius: var(--radius-md); padding: 24px; width: 340px; max-width: 100%;
  text-align: center; display: flex; flex-direction: column; gap: 12px; }
.box h3, .box p { margin: 0; }
.box p { color: var(--text-secondary); font-size: 13px; }
.btn { background: #1b2838; color: #fff; border: 1px solid #2a3f5a; padding: 12px;
  border-radius: var(--radius-sm); font-weight: 600; cursor: pointer; }
.cancel { background: none; border: none; color: var(--text-muted); cursor: pointer; }
</style>