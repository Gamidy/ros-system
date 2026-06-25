<template>
  <div class="forgot-password-page">
    <div class="forgot-container">
      <div class="forgot-card">
        <h2 class="forgot-title">{{ step === 1 ? '忘记密码' : '重置密码' }}</h2>
        <p class="forgot-desc">
          {{ step === 1 ? '请输入您的用户名，我们将生成重置令牌' : '请输入收到的令牌和新密码' }}
        </p>

        <!-- Step 1: 输入用户名 -->
        <el-form
          v-if="step === 1"
          ref="formRef1"
          :model="form1"
          :rules="rules1"
          label-width="0"
          @keyup.enter="handleStep1"
          class="forgot-form"
        >
          <el-form-item prop="username">
            <div class="input-label">用户名</div>
            <el-input
              v-model="form1.username"
              placeholder="请输入用户名"
              size="large"
              class="forgot-input"
            />
          </el-form-item>

          <el-form-item>
            <button
              class="forgot-btn"
              :class="{ loading: loading }"
              :disabled="loading"
              @click="handleStep1"
            >
              <span v-if="!loading">提交</span>
              <span v-else class="btn-loading">处理中...</span>
            </button>
          </el-form-item>
        </el-form>

        <!-- Step 2: 输入令牌和新密码 -->
        <el-form
          v-if="step === 2"
          ref="formRef2"
          :model="form2"
          :rules="rules2"
          label-width="0"
          @keyup.enter="handleStep2"
          class="forgot-form"
        >
          <el-form-item prop="token">
            <div class="input-label">重置令牌</div>
            <el-input
              v-model="form2.token"
              placeholder="请输入收到的令牌"
              size="large"
              class="forgot-input"
            />
          </el-form-item>

          <el-form-item prop="newPassword">
            <div class="input-label">新密码</div>
            <el-input
              v-model="form2.newPassword"
              type="password"
              placeholder="请输入新密码"
              show-password
              size="large"
              class="forgot-input"
            />
          </el-form-item>

          <el-form-item prop="confirmPassword">
            <div class="input-label">确认新密码</div>
            <el-input
              v-model="form2.confirmPassword"
              type="password"
              placeholder="请再次输入新密码"
              show-password
              size="large"
              class="forgot-input"
            />
          </el-form-item>

          <el-form-item>
            <button
              class="forgot-btn"
              :class="{ loading: loading2 }"
              :disabled="loading2"
              @click="handleStep2"
            >
              <span v-if="!loading2">重置密码</span>
              <span v-else class="btn-loading">处理中...</span>
            </button>
          </el-form-item>
        </el-form>

        <!-- 操作链接 -->
        <div class="forgot-links">
          <a class="forgot-link" v-if="step === 1" @click="goToLogin">返回登录</a>
          <a class="forgot-link" v-if="step === 2" @click="step = 1">返回上一步</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import api from '../../api'

const router = useRouter()

const step = ref(1)
const loading = ref(false)
const loading2 = ref(false)
const formRef1 = ref<FormInstance>()
const formRef2 = ref<FormInstance>()

const form1 = reactive({
  username: '',
})

const form2 = reactive({
  token: '',
  newPassword: '',
  confirmPassword: '',
})

const rules1: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
}

const validateConfirmPassword = (_rule: any, value: string, callback: any) => {
  if (value !== form2.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules2: FormRules = {
  token: [{ required: true, message: '请输入重置令牌', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
}

async function handleStep1() {
  const valid = await formRef1.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await api.post('/auth/forgot-password', { username: form1.username })
    // 不暴露用户是否存在，总是显示相同提示
    ElMessage.success('如果用户存在，重置链接已生成')
    // 进入第二步 — 让用户输入 token
    step.value = 2
  } catch {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}

async function handleStep2() {
  const valid = await formRef2.value?.validate().catch(() => false)
  if (!valid) return
  loading2.value = true
  try {
    await api.post('/auth/verify-reset-token', {
      token: form2.token,
      new_password: form2.newPassword,
    })
    ElMessage.success('密码重置成功，请使用新密码登录')
    await router.push('/login')
  } catch {
    // 错误已在拦截器中处理
  } finally {
    loading2.value = false
  }
}

function goToLogin() {
  router.push('/login')
}
</script>

<style scoped>
.forgot-password-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f4ed;
  position: relative;
  overflow: hidden;
}

.forgot-container {
  display: flex;
  width: 100%;
  max-width: 480px;
  min-height: 400px;
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08), 0 4px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  position: relative;
  z-index: 1;
  animation: f-fadeInUp 0.5s ease forwards;
}

@keyframes f-fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.forgot-card {
  flex: 1;
  padding: 48px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.forgot-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a1917;
  margin: 0 0 4px;
  letter-spacing: -0.3px;
}

.forgot-desc {
  font-size: 14px;
  color: #5e5d59;
  margin: 0 0 32px;
}

.forgot-form {
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

.forgot-btn {
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
.forgot-btn:hover:not(:disabled) {
  background: #c96442;
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(217, 119, 87, 0.3);
}
.forgot-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-loading {
  display: flex;
  align-items: center;
  gap: 6px;
}

.forgot-links {
  margin-top: 20px;
  text-align: center;
}

.forgot-link {
  color: #d97757;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition: color 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}
.forgot-link:hover {
  color: #c96442;
}

:deep(.forgot-input .el-input__wrapper) {
  background: #f0efe8 !important;
  border-radius: 12px !important;
  box-shadow: inset 0 0 0 1px #e5e0da !important;
  padding: 8px 14px !important;
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
:deep(.forgot-input .el-input__wrapper:hover) {
  box-shadow: inset 0 0 0 1px #87867f !important;
}
:deep(.forgot-input .el-input__wrapper.is-focus) {
  box-shadow: inset 0 0 0 1px #d97757, 0 0 0 3px rgba(217, 119, 87, 0.12) !important;
}
:deep(.forgot-input .el-input__inner) {
  font-size: 15px;
  color: #1a1917;
}
:deep(.forgot-input .el-input__inner::placeholder) {
  color: #87867f;
}
</style>
