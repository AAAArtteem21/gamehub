<script setup>
import logo from '../assets/images/logo.png'

function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
}

async function loginWithSteam() {
  // сначала гарантируем, что CSRF-cookie установлена
  await fetch('http://localhost:8000/api/csrf/', { credentials: 'include' })
  const csrftoken = getCookie('csrftoken')

  // создаём скрытую форму и отправляем POST — GET сюда не пускают (защита от CSRF)
  const form = document.createElement('form')
  form.method = 'POST'
  form.action = 'http://localhost:8000/auth/login/steam/'

  const input = document.createElement('input')
  input.type = 'hidden'
  input.name = 'csrfmiddlewaretoken'
  input.value = csrftoken
  form.appendChild(input)

  document.body.appendChild(form)
  form.submit()
}
</script>

<template>
  <div class="login-page">
    <div class="login-card card">
      <img :src="logo" alt="GameEyes" class="logo-mark" />
      <h1>GAME<span class="accent-text">EYES</span></h1>
      <p class="tagline">FIND. PLAY. WIN.</p>
      <p class="subtitle">Верифицированная статистика. Реальные тиммейты.</p>
      <button class="btn-steam" @click="loginWithSteam">
        Войти через Steam
      </button>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
}
.login-card { width: 380px; padding: 48px 32px; text-align: center; }
.logo-mark { width: 72px; height: 72px; border-radius: var(--radius-md); object-fit: cover; margin: 0 auto 20px; }
h1 { margin: 0 0 4px; font-size: 26px; letter-spacing: 0.5px; }
.accent-text { color: var(--accent); }
.tagline { font-size: 11px; letter-spacing: 1.5px; color: var(--accent); font-weight: 700; margin: 0 0 16px; }
.subtitle { color: var(--text-secondary); font-size: 14px; margin: 0 0 28px; }
.btn-steam { width: 100%; background: #1B2838; color: white; border: none; padding: 13px; border-radius: var(--radius-sm); font-weight: 600; font-size: 14px; cursor: pointer; }
.btn-steam:hover { background: #2A3F5A; }
</style>