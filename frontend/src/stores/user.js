import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from '@/utils/request'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)
  
  const isLoggedIn = computed(() => !!token.value)
  
  const setToken = (newToken) => {
    token.value = newToken
    localStorage.setItem('token', newToken)
    axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
  }
  
  const clearToken = () => {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    delete axios.defaults.headers.common['Authorization']
  }
  
  const login = async (username, password) => {
    try {
      const res = await axios.post('/api/v1/auth/login', { username, password })
      setToken(res.access_token)
      await fetchUserInfo()
      return res
    } catch (error) {
      console.error('Login error:', error)
      throw error
    }
  }
  
  const fetchUserInfo = async () => {
    try {
      const res = await axios.get('/api/v1/auth/me')
      userInfo.value = res
      return res
    } catch (error) {
      console.error('Fetch user info error:', error)
      clearToken()
      throw error
    }
  }
  
  const logout = () => {
    clearToken()
  }
  
  // 初始化时如果有token，设置请求头
  if (token.value) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
  }
  
  return {
    token,
    userInfo,
    isLoggedIn,
    setToken,
    clearToken,
    login,
    fetchUserInfo,
    logout
  }
})
