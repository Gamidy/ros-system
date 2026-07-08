import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

interface User {
  id: number
  username: string
  full_name: string | null
  email: string | null
  role: string
  department: string | null
  is_active: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref(localStorage.getItem('token') || '')
  const loading = ref(false)

  async function login(username: string, password: string) {
    loading.value = true
    try {
      const res = await api.post('/auth/login', { username, password })
      token.value = res.data.access_token
      localStorage.setItem('token', token.value)
      await fetchUser()
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    const res = await api.get('/auth/me')
    user.value = res.data
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  async function init() {
    if (token.value) {
      try {
        await fetchUser()
      } catch {
        logout()
      }
    }
  }

  return { user, token, loading, login, logout, init }
})
