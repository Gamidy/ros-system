import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<{ username: string } | null>(null)
  const token = ref(localStorage.getItem('token') || '')

  async function login(username: string, password: string) {
    const res = await api.post('/auth/token', { username, password })
    token.value = res.data.access_token
    localStorage.setItem('token', token.value)
    await fetchUser()
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

  return { user, token, login, fetchUser, logout }
})
