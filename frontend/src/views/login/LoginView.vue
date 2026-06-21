<template>
  <div class="claude-login">
    <div class="login-container">
      <!-- Left Side - Branding -->
      <div class="login-left">
        <div class="login-brand">
          <div class="brand-logo">
            <span class="brand-mark">R</span>
          </div>
          <h1 class="brand-title">ROS 研发运营系统</h1>
          <p class="brand-subtitle">R&amp;D Operations System</p>
        </div>
        <div class="login-features">
          <div class="feature-item">
            <div class="feature-dot" />
            <span>产品全生命周期管理</span>
          </div>
          <div class="feature-item">
            <div class="feature-dot" />
            <span>项目穿透分析</span>
          </div>
          <div class="feature-item">
            <div class="feature-dot" />
            <span>实时预警与审批</span>
          </div>
        </div>
      </div>

      <!-- Right Side - Form -->
      <div class="login-right">
        <div class="login-card">
          <h2 class="login-title">欢迎回来</h2>
          <p class="login-desc">请输入您的账号信息</p>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-width="0"
            @keyup.enter="handleLogin"
            class="login-form"
          >
            <el-form-item prop="username">
              <div class="input-label">用户名</div>
              <el-input
                v-model="form.username"
                placeholder="请输入用户名"
                size="large"
                class="claude-input"
              />
            </el-form-item>

            <el-form-item prop="password">
              <div class="input-label">密码</div>
              <el-input
                v-model="form.password"
                type="password"
                placeholder="请输入密码"
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
                @click="handleLogin"
              >
                <span v-if="!loading">登录</span>
                <span v-else class="btn-loading">
                  <span class="loading-dot" />
                  <span class="loading-dot" />
                  <span class="loading-dot" />
                </span>
              </button>
            </el-form-item>
          </el-form>

          <div class="login-footer">
            <p>© {{ currentYear }} ROS System</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Background decoration -->
    <div class="bg-decoration">
      <div class="bg-orb bg-orb-1" />
      <div class="bg-orb bg-orb-2" />
      <div class="bg-orb bg-orb-3" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const currentYear = computed(() => new Date().getFullYear())

const form = reactive({
  username: '',
  password: '',
})
const loading = ref(false)

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    // 使用 authStore.login() 确保 token ref 与 localStorage 同步
    await authStore.login(form.username, form.password)
    ElMessage.success({ message: '登录成功', grouping: true })
    await router.push('/dashboard').catch(() => {
      // 导航失败时不清除 token，让用户可手动刷新
      ElMessage.warning('页面跳转失败，请尝试刷新浏览器')
    })
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
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

/* Background Decoration */
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

/* Login Container */
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

/* Left Side - Branding */
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

/* Right Side - Form */
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

.login-footer {
  margin-top: 32px;
  text-align: center;
}
.login-footer p {
  font-size: 12px;
  color: #87867f;
  margin: 0;
}

/* Input Styling */
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

/* Mobile Responsive */
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
  .login-features {
    display: none;
  }
  .claude-login {
    background: #fff;
  }
  .bg-decoration {
    display: none;
  }
}
</style>
