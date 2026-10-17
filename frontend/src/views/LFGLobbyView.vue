<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { lfgApi } from '../api/lfg'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../composables/useToast'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const post = ref(null)
const applications = ref([])
const loading = ref(true)
const error = ref(null)
const actingId = ref(null)

const pending = computed(() => applications.value.filter((a) => a.status === 'pending'))
const accepted = computed(() => applications.value.filter((a) => a.status === 'accepted'))
const rejected = computed(() => applications.value.filter((a) => a.status === 'rejected'))

async function load() {
  loading.value = true
  error.value = null
  try {
    const res = await lfgApi.get(route.params.id)
    post.value = res.data
    if (auth.isAuthenticated && res.data.is_author) {
      const appRes = await lfgApi.applications(route.params.id)
      applications.value = appRes.data
    } else if (auth.isAuthenticated) {
      // обычный участник — только accepted список не нужен подробно
      applications.value = []
    }
  } catch (e) {
    error.value =
      e.response?.status === 404 ? 'Заявка не найдена или закрыта' : 'Не удалось загрузить'
  } finally {
    loading.value = false
  }
}

async function accept(app) {
  actingId.value = app.id
  try {
    await lfgApi.accept(app.id)
    toast.success(`Принят: ${app.user}`)
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Не удалось принять')
  } finally {
    actingId.value = null
  }
}

async function reject(app) {
  if (!confirm(`Отклонить заявку от «${app.user}»?`)) return
  actingId.value = app.id
  try {
    await lfgApi.reject(app.id)
    toast.success('Заявка отклонена')
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Не удалось отклонить')
  } finally {
    actingId.value = null
  }
}

async function kick(app) {
  if (!confirm(`Убрать «${app.user}» из лобби?`)) return
  actingId.value = app.id
  try {
    await lfgApi.withdraw(app.id)
    toast.success('Игрок убран')
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Не удалось убрать')
  } finally {
    actingId.value = null
  }
}

function viewProfile(userId) {
  router.push(`/players/${userId}`)
}

function formatDate(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('ru-RU', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="state">Загрузка...</div>
  <div v-else-if="error" class="state error">{{ error }}</div>

  <div class="lobby-page" v-else-if="post">
    <div class="lobby-head">
      <div>
        <h1>{{ post.game }}</h1>
        <p class="sub">{{ formatDate(post.datetime) }} · {{ post.accepted_count ?? 0 }}/{{ post.slots_needed }} слотов</p>
      </div>
      <span class="status-pill" :class="post.status">{{ post.status === 'open' ? 'Открыта' : 'Закрыта' }}</span>
    </div>

    <p v-if="post.description" class="desc">{{ post.description }}</p>

    <div v-if="!auth.isAuthenticated" class="hint">
      <button type="button" class="login-link" @click="auth.loginWithSteam()">
        Войди через Steam
      </button>
      , чтобы видеть участников
    </div>

    <template v-else-if="post.is_author">
      <!-- Pending applications -->
      <section class="section">
        <h2>Заявки <span class="cnt">{{ pending.length }}</span></h2>
        <div v-if="!pending.length" class="empty">Пока нет новых заявок</div>
        <div v-for="app in pending" :key="app.id" class="app-card">
          <div class="app-main" @click="viewProfile(app.user_id)">
            <div
              class="avatar"
              :style="app.profile?.avatar_url ? { backgroundImage: `url(${app.profile.avatar_url})` } : {}"
            >
              <span v-if="!app.profile?.avatar_url">{{ (app.user || '?')[0]?.toUpperCase() }}</span>
            </div>
            <div class="app-info">
              <div class="name-row">
                <span class="name">{{ app.user }}</span>
                <span class="when">{{ formatDate(app.created_at) }}</span>
              </div>
              <p v-if="app.message" class="msg">«{{ app.message }}»</p>
              <div v-if="app.profile?.games?.length" class="games">
                <span v-for="g in app.profile.games" :key="g.platform" class="game-chip">
                  {{ g.game_label || g.platform }}
                  <template v-if="g.skill_rating"> · {{ g.skill_rating }}</template>
                </span>
              </div>
            </div>
          </div>
          <div class="app-actions">
            <button
              type="button"
              class="btn-accept"
              :disabled="actingId === app.id"
              @click="accept(app)"
            >
              Принять
            </button>
            <button
              type="button"
              class="btn-reject"
              :disabled="actingId === app.id"
              @click="reject(app)"
            >
              Отклонить
            </button>
            <button type="button" class="btn-ghost" @click="viewProfile(app.user_id)">
              Профиль
            </button>
          </div>
        </div>
      </section>

      <!-- Accepted -->
      <section class="section">
        <h2>В команде <span class="cnt">{{ accepted.length }}</span></h2>
        <div v-if="!accepted.length" class="empty">Никого пока не приняли</div>
        <div v-for="app in accepted" :key="app.id" class="app-card accepted">
          <div class="app-main" @click="viewProfile(app.user_id)">
            <div
              class="avatar"
              :style="app.profile?.avatar_url ? { backgroundImage: `url(${app.profile.avatar_url})` } : {}"
            >
              <span v-if="!app.profile?.avatar_url">{{ (app.user || '?')[0]?.toUpperCase() }}</span>
            </div>
            <div class="app-info">
              <span class="name">{{ app.user }}</span>
              <div v-if="app.profile?.games?.length" class="games">
                <span v-for="g in app.profile.games" :key="g.platform" class="game-chip">
                  {{ g.game_label || g.platform }}
                </span>
              </div>
            </div>
          </div>
          <button
            type="button"
            class="btn-reject"
            :disabled="actingId === app.id"
            @click="kick(app)"
          >
            Убрать
          </button>
        </div>
      </section>

      <section v-if="rejected.length" class="section muted-sec">
        <h2>Отклонённые <span class="cnt">{{ rejected.length }}</span></h2>
        <div v-for="app in rejected" :key="app.id" class="app-card rejected">
          <span class="name">{{ app.user }}</span>
        </div>
      </section>
    </template>

    <div v-else class="hint">
      Только автор видит список заявок. Если тебя приняли — контакт и чат доступны на главной LFG.
    </div>
  </div>
</template>

<style scoped>
.lobby-page { display: flex; flex-direction: column; gap: 20px; max-width: 720px; }
.lobby-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.lobby-head h1 { margin: 0 0 4px; font-size: 22px; }
.sub { margin: 0; color: var(--text-secondary); font-size: 13px; }
.status-pill {
  font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 999px;
}
.status-pill.open { background: var(--accent-dim); color: var(--accent); }
.status-pill.closed { background: rgba(201, 122, 114, 0.12); color: var(--danger); }
.desc { margin: 0; color: var(--text-primary); line-height: 1.45; font-size: 14px; }

.section h2 {
  margin: 0 0 10px; font-size: 13px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-secondary);
  display: flex; align-items: center; gap: 8px;
}
.cnt {
  font-family: var(--font-mono); font-size: 11px;
  background: var(--bg-sunken); padding: 1px 7px; border-radius: 999px;
}
.empty { color: var(--text-muted); font-size: 13px; padding: 8px 0; }

.app-card {
  display: flex; justify-content: space-between; align-items: center; gap: 12px;
  padding: 12px 14px; margin-bottom: 8px;
  background: var(--bg-card); border: 1px solid var(--border-color);
  border-radius: var(--radius-md); flex-wrap: wrap;
}
.app-card.accepted { border-color: color-mix(in srgb, var(--success) 35%, var(--border-color)); }
.app-card.rejected { opacity: 0.55; }

.app-main {
  display: flex; gap: 12px; align-items: center; cursor: pointer; min-width: 0; flex: 1;
}
.avatar {
  width: 40px; height: 40px; border-radius: 10px; flex-shrink: 0;
  background: var(--accent-dim) center/cover;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; color: var(--accent); font-size: 14px;
}
.app-info { min-width: 0; }
.name-row { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }
.name { font-weight: 700; font-size: 14px; }
.when { font-size: 11px; color: var(--text-muted); font-family: var(--font-mono); }
.msg {
  margin: 4px 0 0; font-size: 12px; color: var(--text-secondary);
  font-style: italic; line-height: 1.35;
}
.games { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.game-chip {
  font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 999px;
  background: var(--bg-sunken); color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.app-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.btn-accept {
  background: var(--accent); color: #12100c; border: none;
  padding: 7px 12px; border-radius: var(--radius-sm); font-weight: 700;
  font-size: 12px; cursor: pointer;
}
.btn-accept:disabled { opacity: 0.5; }
.btn-reject {
  background: transparent; border: 1px solid rgba(230, 57, 70, 0.4); color: var(--danger);
  padding: 7px 12px; border-radius: var(--radius-sm); font-weight: 600;
  font-size: 12px; cursor: pointer;
}
.btn-reject:disabled { opacity: 0.5; }
.btn-ghost {
  background: var(--bg-sunken); border: 1px solid var(--border-color);
  color: var(--text-secondary); padding: 7px 12px; border-radius: var(--radius-sm);
  font-weight: 600; font-size: 12px; cursor: pointer;
}

.state { color: var(--text-secondary); padding: 24px 0; }
.state.error { color: var(--danger); }
.hint { color: var(--text-secondary); font-size: 13px; }
.login-link {
  background: none; border: none; color: var(--accent);
  font-weight: 600; cursor: pointer; padding: 0;
}
.muted-sec { opacity: 0.7; }
</style>