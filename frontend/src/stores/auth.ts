import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { authApi } from '@/api/admin'

interface AdminUser {
  uuid: string
  username: string
  display_name: string
  role: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AdminUser | null>(null)
  const checked = ref(false)
  const loading = ref(false)
  const isAuthenticated = computed(() => Boolean(user.value))

  async function check() {
    if (checked.value) return isAuthenticated.value
    try {
      const result = await authApi.me()
      user.value = result.user
    } catch {
      user.value = null
    } finally {
      checked.value = true
    }
    return isAuthenticated.value
  }

  async function login(username: string, password: string) {
    loading.value = true
    try {
      const result = await authApi.login(username, password)
      user.value = result.user
      checked.value = true
    } finally {
      loading.value = false
    }
  }

  async function initialize(payload: Record<string, string>) {
    loading.value = true
    try {
      const result = await authApi.initialize(payload)
      user.value = result.user
      checked.value = true
      localStorage.setItem('evidentfolio_setup_complete', '1')
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    await authApi.logout()
    user.value = null
    checked.value = true
  }

  return { user, checked, loading, isAuthenticated, check, login, initialize, logout }
})
