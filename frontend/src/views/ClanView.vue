<script setup>
import { ref, onMounted, computed } from 'vue'
import { clansApi } from '../api/clans'
import api from '../api/axios'
import CreateClanModal from '../components/clans/CreateClanModal.vue'
import JoinClanModal from '../components/clans/JoinClanModal.vue'
import ClanDashboardTable from '../components/clans/ClanDashboardTable.vue'
import ClanIcon from '../components/clans/ClanIcon.vue'
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()


const clans = ref([])
const loading = ref(true)
const error = ref(null)
const showCreateModal = ref(false)
const showJoinModal = ref(false)
const searchQuery = ref('')

const selectedClan = ref(null)
const dashboard = ref([])
const dashboardLoading = ref(false)
const dashboardError = ref(null)

const logoUploading = ref(false)
const logoInput = ref(null)

const roleLabels = { leader: 'Лидер', officer: 'Офицер', member: 'Участник' }

const filteredClans = computed(() =>
  clans.value.filter((c) => c.name.toLowerCase().includes(searchQuery.value.toLowerCase()))
)

function isLeader(clan) {
  return clan?.my_role === 'leader' || (clan?.invite_code != null && clan.invite_code !== '')
}

function openCreate() {
  if (auth.requireAuth('Войди через Steam, чтобы создать клан.')) showCreateModal.value = true
}
function openJoin() {
  if (auth.requireAuth('Войди через Steam, чтобы вступить в клан.')) showJoinModal.value = true
}

async function loadClans() {
  loading.value = true
  error.value = null
  try {
    const res = await clansApi.list()
    clans.value = res.data.results || res.data
  } catch (e) {
    error.value = 'Не удалось загрузить кланы'
  } finally {
    loading.value = false
  }
}

async function openClan(clan) {
  if (!auth.requireAuth('Войди через Steam, чтобы смотреть активность клана.')) return
  selectedClan.value = clan
  dashboard.value = []
  dashboardError.value = null
  dashboardLoading.value = true
  try {
    const res = await clansApi.dashboard(clan.id)
    dashboard.value = res.data
  } catch (e) {
    dashboardError.value = e.response?.data?.detail || 'Дашборд доступен только участникам клана'
  } finally {
    dashboardLoading.value = false
  }
}

function closeDashboard() {
  selectedClan.value = null
}

function onClanCreated(newClan) {
  clans.value.unshift(newClan)
}

function onJoined() {
  loadClans()
}

function onDashboardUpdated() {
  if (selectedClan.value) openClan(selectedClan.value)
}

function copyInviteCode(code) {
  navigator.clipboard.writeText(code)
}

function activeMembersRatio(clan) {
  return clan.members_count > 0 ? Math.min(100, clan.members_count * 15) : 0
}

function triggerLogoPick() {
  logoInput.value?.click()
}

async function onLogoSelected(e) {
  const file = e.target.files?.[0]
  if (!file || !selectedClan.value) return

  if (file.size > 2 * 1024 * 1024) {
    alert('Максимум 2 МБ')
    e.target.value = ''
    return
  }

  logoUploading.value = true
  try {
    const fd = new FormData()
    fd.append('logo', file)
    const res = await api.post(`clans/${selectedClan.value.id}/upload_logo/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const url = res.data.logo_url
    selectedClan.value = {
      ...selectedClan.value,
      logo_url: url,
      logo: url,
    }
    const idx = clans.value.findIndex((c) => c.id === selectedClan.value.id)
    if (idx !== -1) {
      clans.value[idx] = { ...clans.value[idx], logo_url: url, logo: url }
    }
  } catch (err) {
    const msg =
      err.response?.data?.detail ||
      err.response?.data?.logo?.[0] ||
      'Не удалось загрузить логотип'
    alert(msg)
  } finally {
    logoUploading.value = false
    e.target.value = ''
  }
}

onMounted(loadClans)
</script>

<template>
  <div class="clans-page">
    <div class="page-header">
      <div>
        <h1>Кланы</h1>
        <p class="subtitle">Создавай или вступай — следи за активностью команды</p>
      </div>
      <div class="header-actions">
        <button type="button" class="btn-secondary" @click="showJoinModal = true">
          Вступить по коду
        </button>
        <button type="button" class="btn-primary" @click="showCreateModal = true">
          + Создать клан
        </button>
      </div>
    </div>

    <input
      v-if="clans.length > 0"
      v-model="searchQuery"
      class="clan-search"
      placeholder="Поиск клана по названию..."
    />

    <div v-if="loading" class="state-message">Загружаем кланы...</div>
    <div v-else-if="error" class="state-message error-state">{{ error }}</div>

    <div v-else-if="clans.length === 0" class="state-message empty-state">
      <p>Ты пока не состоишь ни в одном клане.</p>
      <div class="header-actions">
        <button type="button" class="btn-secondary" @click="showJoinModal = true">
          Вступить по коду
        </button>
        <button type="button" class="btn-primary" @click="showCreateModal = true">
          Создать первый клан
        </button>
      </div>
    </div>

    <div v-else-if="filteredClans.length === 0" class="state-message empty-state">
      <p>Ничего не найдено по запросу «{{ searchQuery }}»</p>
      <button type="button" class="btn-secondary" @click="searchQuery = ''">Сбросить поиск</button>
    </div>

    <div v-else class="clans-grid">
      <div
        v-for="clan in filteredClans"
        :key="clan.id"
        class="clan-card clickable-card card"
        @click="openClan(clan)"
      >
        <div class="clan-card-top">
          <ClanIcon :clan="clan" :size="48" />
          <div class="clan-card-title-block">
            <h3>{{ clan.name }}</h3>
            <span class="my-role-badge" :class="clan.my_role" v-if="clan.my_role">
              {{ roleLabels[clan.my_role] }}
            </span>
          </div>
          <span class="members-badge">{{ clan.members_count }}</span>
        </div>

        <p class="clan-description">{{ clan.description || 'Без описания' }}</p>

        <div class="activity-bar">
          <div class="activity-fill" :style="{ width: activeMembersRatio(clan) + '%' }"></div>
        </div>

        <div
          class="invite-row"
          v-if="clan.invite_code"
          @click.stop="copyInviteCode(clan.invite_code)"
        >
          <span class="invite-label">Код:</span>
          <span class="invite-code">{{ clan.invite_code }}</span>
          <span class="copy-hint">копировать</span>
        </div>
        <div class="member-badge" v-else-if="clan.is_member">
          <span class="member-icon">✓</span>
          <span>Ты в этом клане</span>
        </div>
      </div>
    </div>

    <div class="overlay" v-if="selectedClan" @click.self="closeDashboard">
      <div class="dashboard-modal card">
        <div class="modal-header">
          <div class="modal-header-title">
            <div class="logo-wrap">
              <ClanIcon :clan="selectedClan" :size="36" />
              <template v-if="isLeader(selectedClan)">
                <input
                  ref="logoInput"
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  class="logo-file-input"
                  @change="onLogoSelected"
                />
                <button
                  type="button"
                  class="logo-edit-btn"
                  :disabled="logoUploading"
                  title="Сменить аватар"
                  @click="triggerLogoPick"
                >
                  {{ logoUploading ? '…' : '✎' }}
                </button>
              </template>
            </div>
            <h2>{{ selectedClan.name }} — активность</h2>
          </div>
          <button type="button" class="close-btn" @click="closeDashboard">✕</button>
        </div>

        <div v-if="dashboardLoading" class="state-message">Считаем активность...</div>
        <div v-else-if="dashboardError" class="state-message error-state">{{ dashboardError }}</div>
        <ClanDashboardTable
          v-else
          :entries="dashboard"
          :clan-id="selectedClan.id"
          :is-leader="selectedClan.invite_code !== null"
          @updated="onDashboardUpdated"
        />
      </div>
    </div>

    <CreateClanModal
      v-if="showCreateModal"
      @close="showCreateModal = false"
      @created="onClanCreated"
    />
    <JoinClanModal
      v-if="showJoinModal"
      @close="showJoinModal = false"
      @joined="onJoined"
    />
  </div>
</template>

<style scoped>
.clans-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
  width: 100%;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}
.page-header h1 {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 600;
}
.subtitle {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
}
.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.clan-search {
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  color: var(--text-primary);
  font-size: 13px;
  width: 100%;
  max-width: 320px;
}

.clans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.clan-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.clan-card-top {
  display: flex;
  align-items: center;
  gap: 12px;
}
.clan-card-title-block {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.clan-card-title-block h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.my-role-badge {
  align-self: flex-start;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.my-role-badge.leader {
  background: var(--accent-dim);
  color: var(--accent);
}
.my-role-badge.officer {
  background: rgba(106, 170, 124, 0.12);
  color: var(--success);
}
.my-role-badge.member {
  background: var(--bg-card-hover);
  color: var(--text-secondary);
}

.members-badge {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  background: var(--bg-sunken);
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
  font-family: var(--font-mono);
}

.clan-description {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
  min-height: 28px;
  line-height: 1.4;
}

.activity-bar {
  height: 3px;
  background: var(--bg-sunken);
  border-radius: 2px;
  overflow: hidden;
}
.activity-fill {
  height: 100%;
  background: var(--accent);
}

.invite-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: var(--bg-sunken);
  border-radius: var(--radius-sm);
  font-size: 12px;
  border: 1px solid var(--border-color);
}
.invite-label { color: var(--text-secondary); }
.invite-code {
  font-family: var(--font-mono);
  font-weight: 700;
  color: var(--accent);
}
.copy-hint {
  margin-left: auto;
  color: var(--text-muted);
  font-size: 11px;
}

.member-badge {
  padding: 8px 10px;
  background: var(--accent-dim);
  border: 1px solid rgba(196, 165, 116, 0.35);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--accent);
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-weight: 600;
}
.member-icon {
  width: 16px;
  height: 16px;
  background: var(--accent);
  color: #12100c;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
}

.state-message {
  padding: 48px 20px;
  text-align: center;
  color: var(--text-secondary);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}
.error-state { color: var(--danger); }

.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.dashboard-modal {
  width: 820px;
  max-width: 92vw;
  max-height: 80vh;
  overflow-y: auto;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.modal-header-title {
  display: flex;
  align-items: center;
  gap: 12px;
}
.modal-header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}
.close-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
}

.logo-wrap {
  position: relative;
  display: inline-flex;
}
.logo-file-input { display: none; }
.logo-edit-btn {
  position: absolute;
  right: -6px;
  bottom: -6px;
  width: 22px;
  height: 22px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  cursor: pointer;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  line-height: 1;
  color: var(--text-secondary);
}
.logo-edit-btn:hover { border-color: var(--accent); color: var(--accent); }
.logo-edit-btn:disabled { opacity: 0.6; cursor: wait; }

@media (max-width: 900px) {
  .clans-grid { grid-template-columns: 1fr; }
  .dashboard-modal { width: 100%; max-width: 100vw; max-height: 90vh; border-radius: 0; }
  .page-header h1 { font-size: 18px; }
}
</style>
