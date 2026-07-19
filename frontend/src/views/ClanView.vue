<script setup>
import { ref, onMounted } from 'vue'
import { clansApi } from '../api/clans'
import CreateClanModal from '../components/clans/CreateClanModal.vue'
import JoinClanModal from '../components/clans/JoinClanModal.vue'
import ClanDashboardTable from '../components/clans/ClanDashboardTable.vue'

const clans = ref([])
const loading = ref(true)
const error = ref(null)
const showCreateModal = ref(false)
const showJoinModal = ref(false)

const selectedClan = ref(null)
const dashboard = ref([])
const dashboardLoading = ref(false)
const dashboardError = ref(null)

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

function copyInviteCode(code) {
  navigator.clipboard.writeText(code)
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
        <button class="btn-secondary" @click="showJoinModal = true">Вступить по коду</button>
        <button class="btn-primary" @click="showCreateModal = true">+ Создать клан</button>
      </div>
    </div>

    <div v-if="loading" class="state-message">Загружаем кланы...</div>
    <div v-else-if="error" class="state-message error-state">{{ error }}</div>
    <div v-else-if="clans.length === 0" class="state-message empty-state">
      <p>Ты пока не состоишь ни в одном клане.</p>
      <div class="header-actions">
        <button class="btn-secondary" @click="showJoinModal = true">Вступить по коду</button>
        <button class="btn-primary" @click="showCreateModal = true">Создать первый клан</button>
      </div>
    </div>

    <div v-else class="clans-grid">
      <div v-for="clan in clans" :key="clan.id" class="clan-card card" @click="openClan(clan)">
        <div class="clan-card-header">
          <h3>{{ clan.name }}</h3>
          <span class="members-badge">{{ clan.members_count }} участников</span>
        </div>
        <p class="clan-description">{{ clan.description || 'Без описания' }}</p>
        <div class="invite-row" v-if="clan.invite_code" @click.stop="copyInviteCode(clan.invite_code)">
          <span class="invite-label">Код приглашения:</span>
          <span class="invite-code">{{ clan.invite_code }}</span>
          <span class="copy-hint">нажми, чтобы скопировать</span>
        </div>
        <div class="member-badge" v-else>
          <span>✓ Ты участник этого клана</span>
        </div>
      </div>
    </div>

    <!-- Dashboard modal -->
    <div class="overlay" v-if="selectedClan" @click.self="closeDashboard">
      <div class="dashboard-modal card">
        <div class="modal-header">
          <h2>{{ selectedClan.name }} — активность</h2>
          <button class="close-btn" @click="closeDashboard">✕</button>
        </div>

        <div v-if="dashboardLoading" class="state-message">Считаем активность...</div>
        <div v-else-if="dashboardError" class="state-message error-state">{{ dashboardError }}</div>
        <ClanDashboardTable v-else :entries="dashboard" />
      </div>
    </div>

    <CreateClanModal v-if="showCreateModal" @close="showCreateModal = false" @created="onClanCreated" />
    <JoinClanModal v-if="showJoinModal" @close="showJoinModal = false" @joined="onJoined" />
  </div>
</template>

<style scoped>
.clans-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-header h1 {
  margin: 0 0 4px;
  font-size: 24px;
}

.subtitle {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.btn-primary {
  background: var(--accent);
  color: white;
  border: none;
  padding: 11px 18px;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
}

.btn-secondary {
  background: var(--bg-card-hover);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  padding: 11px 18px;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
}

.clans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.clan-card {
  cursor: pointer;
  transition: border-color 0.15s, transform 0.15s;
}

.clan-card:hover {
  border-color: #363B45;
  transform: translateY(-1px);
}

.clan-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.clan-card-header h3 {
  margin: 0;
  font-size: 16px;
}

.members-badge {
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-card-hover);
  padding: 3px 8px;
  border-radius: 20px;
}

.clan-description {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0 0 14px;
  min-height: 32px;
}

.invite-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
  font-size: 12px;
}

.invite-label {
  color: var(--text-secondary);
}

.invite-code {
  font-family: monospace;
  font-weight: 700;
  color: var(--accent);
}

.copy-hint {
  margin-left: auto;
  color: var(--text-secondary);
  font-size: 11px;
}

.state-message {
  padding: 60px 20px;
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
  gap: 16px;
}

.error-state {
  color: var(--danger);
}

.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.dashboard-modal {
  width: 720px;
  max-width: 92vw;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-header h2 {
  margin: 0;
  font-size: 18px;
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
}
</style>