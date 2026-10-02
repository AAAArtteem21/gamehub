<script setup>
import logo from '../assets/images/logo.png'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function loginWithSteam() {
  window.location.href = `${API_BASE}/api/auth/steam/start/`
}

async function loginWithSteam() {
  await fetch(`${API_BASE}/api/csrf/`, { credentials: 'include' })
  const csrftoken = getCookie('csrftoken')

  const form = document.createElement('form')
  form.method = 'POST'
  form.action = `${API_BASE}/auth/login/steam/`

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
    <div class="login-card">
      <img :src="logo" alt="GameEyes" class="logo-mark" />
      <h1>GAME<span class="accent">EYES</span></h1>
      <p class="tagline">find · play · win</p>
      <p class="subtitle">
        Статистика с привязанных аккаунтов. Поиск тиммейтов и кланы.
      </p>
      <button type="button" class="btn-steam" @click="loginWithSteam">
        Войти через Steam
      </button>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  padding: 24px;
}
.login-card {
  width: 100%;
  max-width: 360px;
  padding: 40px 28px;
  text-align: center;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}
.logo-mark {
  width: 56px;
  height: 56px;
  border-radius: 6px;
  object-fit: cover;
  margin: 0 auto 16px;
  display: block;
}
h1 {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.accent { color: var(--accent); }
.tagline {
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  font-weight: 500;
  margin: 0 0 14px;
  text-transform: lowercase;
}
.subtitle {
  color: var(--text-secondary);
  font-size: 13px;
  margin: 0 0 24px;
  line-height: 1.45;
}
.btn-steam {
  width: 100%;
  background: #1b2838;
  color: #fff;
  border: 1px solid #2a3f5a;
  padding: 12px;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
}
.btn-steam:hover {
  background: #243447;
  border-color: #3d5a80;
}
</style>
