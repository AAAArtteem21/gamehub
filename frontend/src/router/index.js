import { createRouter, createWebHistory } from 'vue-router'
import DashboardLayout from '../components/layout/DashboardLayout.vue'
import HomeView from '../views/HomeView.vue'
import LFGFeedView from '../views/LFGFeedView.vue'
import LoginView from '../views/LoginView.vue'
import AuthCallbackView from '../views/AuthCallbackView.vue'
import ClanView from '../views/ClanView.vue'
import ProfileView from '../views/ProfileView.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/login', name: 'login', component: LoginView },
    { path: '/auth/callback', name: 'auth-callback', component: AuthCallbackView },
    {
      path: '/',
      component: DashboardLayout,
      meta: { requiresAuth: true },
      children: [
        { path: '', name: 'home', component: HomeView },
        { path: 'lfg', name: 'lfg', component: LFGFeedView },
        { path: 'lfg/:id', name: 'lfg-lobby', component: () => import('../views/LFGLobbyView.vue') },
        { path: 'clans', name: 'clans', component: ClanView },
        { path: 'profile', name: 'profile', component: ProfileView },
        {
          path: 'players/guest/:game/:externalId',
          name: 'guest-profile',
          component: () => import('../views/GuestProfileView.vue'),
        },
        {
          path: 'players/:id',
          name: 'player-profile',
          component: () => import('../views/PublicProfileView.vue'),
        },
        {
          path: 'compare',
          name: 'compare',
          component: () => import('../views/CompareView.vue'),
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return '/login'
  }
})

export default router