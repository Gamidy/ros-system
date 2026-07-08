import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
      return Promise.reject(err)
    }

    let message = '请求失败'

    // 1. 网络错误（无响应）
    if (!err.response) {
      if (err.code === 'ECONNABORTED') {
        message = '请求超时，请稍后重试'
      } else {
        message = '网络连接失败，请检查网络'
      }
    } else {
      const { data, status } = err.response

      // 2. 优先取 detail，其次 message，纯字符串直接使用
      if (typeof data === 'string') {
        message = data
      } else if (data?.detail) {
        message = data.detail
      } else if (data?.message) {
        message = data.message
      } else {
        // 3. 根据状态码提供默认中文提示
        const statusMessages: Record<number, string> = {
          400: '请求参数错误',
          403: '权限不足',
          404: '资源不存在',
          409: '数据冲突',
          422: '数据验证失败',
          500: '服务器内部错误',
        }
        message = statusMessages[status] || `请求失败 (${status})`
      }
    }

    ElMessage.error(message)
    return Promise.reject(err)
  }
)

export async function changePassword(oldPassword: string, newPassword: string) {
  const res = await api.put('/auth/password', {
    old_password: oldPassword,
    new_password: newPassword,
  })
  return res.data
}

export async function forgotPassword(phone: string, full_name: string) {
  const res = await api.post('/auth/forgot-password', { phone, full_name })
  return res.data
}

export default api
