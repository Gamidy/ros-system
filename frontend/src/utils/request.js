import axios from 'axios'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    if (error.response) {
      const { status, data } = error.response
      
      if (status === 401) {
        localStorage.removeItem('token')
        window.location.href = '/login'
      }
      
      // 确保返回的对象有detail字段
      const errData = typeof data === 'object' && data !== null ? data : { detail: data || '请求失败' }
      return Promise.reject(errData)
    }
    return Promise.reject({ detail: error.message || '网络错误' })
  }
)

export default request
