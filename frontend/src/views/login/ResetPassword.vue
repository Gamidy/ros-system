<template>
  <div class="claude-login">
    <div class="login-container">
      <!-- Left Side - Branding -->
      <div class="login-left">
        <div class="login-brand">
          <div class="brand-logo">
            <span class="brand-mark">R</span>
          </div>
          <h1 class="brand-title">重置密码</h1>
          <p class="brand-subtitle">设置您的新密码</p>
        </div>
        <div class="login-features">
          <div class="feature-item">
            <div class="feature-dot" />
            <span>密码长度至少 6 位</span>
          </div>
          <div class="feature-item">
            <div class="feature-dot" />
            <span>建议包含字母和数字</span>
          </div>
          <div class="feature-item">
            <div class="feature-dot" />
            <span>重置后使用新密码登录</span>
          </div>
        </div>
      </div>

      <!-- Right Side - Form -->
      <div class="login-right">
        <div class="login-card">
          <template v-if="!success && !error">
            <h2 class="login-title">设置新密码</h2>
            <p class="login-desc">请输入您的新密码</p>

            <el-form
              ref="formRef"
              :model="form"
              :rules="rules"
              label-width="0"
              @keyup.enter="handleSubmit"
              class="login-form"
            >
              <el-form-item prop="password">
                <div class="input-label">新密码</div>
                <el-input
                  v-model="form.password"
                  type="password"
                  placeholder="请输入新密码"
                  show-password
                  size="large"
                  class="claude-input"
                />
              </el-form-item>

              <el-form-item prop="confirm">
                <div class="input-label">确认密码</div>
                <el-input
                  v-model="form.confirm"
                  type="password"
                  placeholder="请再次输入新密码"
                  show-password
                  size="large"
                  class="claude-input"
                />
              </el-form-item>

              <el-form-item>
                <button
                  class="login-btn"
                  :class="{ loading }"
                  :disabled="loading"
                  @click="handleSubmit"
                >
                  <span v-if="!loading">重置密码</span>
                  <span v-else class="btn-loading">
                    <span class="loading-dot" />
                    <span class="loading-dot" />
                    <span class="loading-dot" />
                  </span>
                </button>
              </el-form-item>
            </el-form>
          </template>

          <!-- 成功状态 -->
          <template v-else-if="success">
            <div class="result-state">
              <div class="result-icon success-icon">✅</div>
              <h2 class="login-title" style="text-align:center">密码重置成功</h2>
              <p style="color: #5e5d59; font-size: 14px; text-align:center; margin-bottom: 24px;">
                请使用新密码登录系统
              </p>
              <button class="login-btn" @click="goLogin">
                去登录
              </button>
            </div>
          </template>

          <!-- 失败状态 -->
          <template v-else>
            <div class="result-state">
              <div class="result-icon error-icon">❌</div>
              <h2 class="login-title" style="text-align:center">链接已失效</h2>
              <p style="color: #5e5d59; font-size: 14px; text-align:center; margin-bottom: 24px;">
                {{ errorMsg || '该重置链接已过期或已被使用，请重新申请' }}
              </p>
              <button class="login-btn" @click="goForgot">
                重新申请
              </button>
            </div>
          </template>

          <!-- Back to login -->
          <div class="register-section" v-if="!success">
            <a class="register-link" @click="goLogin">返回登录</a>
          </div>

          <div class="login-footer">
            <p>© {{ currentYear }} ROS System</p>
          </div>
        </div>
      </div>
    </div>

    <div class="bg-decoration">
      <div class="bg-orb bg-orb-1" />
      <div class="bg-orb bg-orb-2" />
      <div class="bg-orb bg-orb-3" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import api from '../../api'

const router = useRouter()
const route = useRoute()
const formRef = ref<FormInstance>()
const currentYear = computed(() => new Date().getFullYear())

const form = reactive({
  password: '',
  confirm: '',
})
const loading = ref(false)
const success = ref(false)
const error = ref(false)
const errorMsg = ref('')

// 从 URL 查询参数获取 token
const token = computed(() => (route.query.token as string) || '')

onMounted(() => {
  if (!token.value) {
    error.value = true
    errorMsg.value = '缺少重置令牌，请从邮件中的链接访问'
  }
})

const validateConfirm = (_rule: unknown, value: string, callback: (e?: Error) => void) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少 6 位', trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await api.post('/auth/reset-password', {
      token: token.value,
      new_password: form.password,
    })
    success.value = true
    ElMessage.success('密码重置成功')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    const msg = err.response?.data?.detail
    if (msg) {
      error.value = true
      errorMsg.value = msg
    } else {
      ElMessage.error('重置失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}

function goLogin() {
  router.push('/login')
}

function goForgot() {
  router.push('/forgot-password')
}
</script>

<style scoped>
.claude-login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: #f5f4ed;
}

.bg-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}
.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
  animation: float 20s ease-in-out infinite;
}
.bg-orb-1 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(217, 119, 87, 0.2), transparent 70%);
  top: -10%;
  right: -5%;
  animation-delay: 0s;
}
.bg-orb-2 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(201, 100, 66, 0.15), transparent 70%);
  bottom: -10%;
  left: -5%;
  animation-delay: -7s;
}
.bg-orb-3 {
  width: 250px;
  height: 250px;
  background: radial-gradient(circle, rgba(217, 119, 87, 0.1), transparent 70%);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation-delay: -14s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.95); }
}

.login-container {
  display: flex;
  width: 100%;
  max-width: 1000px;
  min-height: 560px;
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08), 0 4px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  position: relative;
  z-index: 1;
  animation: c-fadeInUp 0.5s ease forwards;
}

@keyframes c-fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.login-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px;
  background: linear-gradient(135deg, #d97757 0%, #c96442 100%);
  color: white;
  position: relative;
  overflow: hidden;
}
.login-left::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 30% 70%, rgba(255,255,255,0.1) 0%, transparent 50%),
    radial-gradient(circle at 70% 30%, rgba(255,255,255,0.08) 0%, transparent 40%);
}

.login-brand {
  position: relative;
  z-index: 1;
}

.brand-logo {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: rgba(255,255,255,0.2);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  border: 1px solid rgba(255,255,255,0.2);
}
.brand-mark {
  font-size: 20px;
  font-weight: 700;
  color: white;
}

.brand-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 8px;
  letter-spacing: -0.5px;
  line-height: 1.2;
}
.brand-subtitle {
  font-size: 16px;
  opacity: 0.8;
  margin: 0;
  font-weight: 400;
}

.login-features {
  margin-top: 40px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
  z-index: 1;
}
.feature-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 15px;
  opacity: 0.9;
}
.feature-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255,255,255,0.6);
  flex-shrink: 0;
}

.login-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px;
  min-width: 400px;
}

.login-card {
  max-width: 360px;
  margin: 0 auto;
  width: 100%;
}

.login-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a1917;
  margin: 0 0 4px;
  letter-spacing: -0.3px;
}
.login-desc {
  font-size: 14px;
  color: #5e5d59;
  margin: 0 0 32px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-label {
  font-size: 13px;
  font-weight: 600;
  color: #1a1917;
  margin-bottom: 6px;
}

.login-btn {
  width: 100%;
  height: 44px;
  border-radius: 12px;
  border: none;
  background: #d97757;
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 8px;
}
.login-btn:hover:not(:disabled) {
  background: #c96442;
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(217, 119, 87, 0.3);
}
.login-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-loading {
  display: flex;
  gap: 6px;
  align-items: center;
}
.loading-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: white;
  animation: dotBounce 1.4s ease-in-out infinite;
}
.loading-dot:nth-child(2) { animation-delay: 0.2s; }
.loading-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes dotBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.result-state {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.result-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.register-section {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
}
.register-link {
  color: #d97757;
  cursor: pointer;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}
.register-link::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: -1px;
  width: 100%;
  height: 1.5px;
  background: #d97757;
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.register-link:hover {
  color: #c96442;
}
.register-link:hover::after {
  transform: scaleX(1);
}

.login-footer {
  margin-top: 32px;
  text-align: center;
}
.login-footer p {
  font-size: 12px;
  color: #87867f;
  margin: 0;
}

:deep(.claude-input .el-input__wrapper) {
  background: #f0efe8 !important;
  border-radius: 12px !important;
  box-shadow: inset 0 0 0 1px #e5e0da !important;
  padding: 8px 14px !important;
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
:deep(.claude-input .el-input__wrapper:hover) {
  box-shadow: inset 0 0 0 1px #87867f !important;
}
:deep(.claude-input .el-input__wrapper.is-focus) {
  box-shadow: inset 0 0 0 1px #d97757, 0 0 0 3px rgba(217, 119, 87, 0.12) !important;
}
:deep(.claude-input .el-input__inner) {
  font-size: 15px;
  color: #1a1917;
}
:deep(.claude-input .el-input__inner::placeholder) {
  color: #87867f;
}

@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
    max-width: 100%;
    min-height: auto;
    border-radius: 0;
    box-shadow: none;
  }
  .login-left {
    padding: 32px 24px;
    min-height: 200px;
  }
  .login-right {
    padding: 32px 24px;
    min-width: auto;
  }
  .brand-title {
    font-size: 24px;
  }
  .login-features {
    margin-top: 24px;
    gap: 12px;
  }
}
</style>
