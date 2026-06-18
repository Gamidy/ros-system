<template>
  <div class="login-container">
    <div class="login-card">
      <h1 class="login-title">ROS 研发运营系统</h1>
      <p class="login-subtitle">R&amp;D Operations System</p>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="0"
        size="large"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            class="login-btn"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>
      <div class="login-footer">
        没有账号？
        <router-link to="/register" class="register-link">申请注册</router-link>
        <span style="margin:0 8px">|</span>
        <a class="register-link" style="cursor:pointer" @click="showForgotDialog = true">忘记密码？</a>
      </div>
    </div>

    <!-- 忘记密码对话框 -->
    <el-dialog v-model="showForgotDialog" title="找回密码" width="400px" :close-on-click-modal="false">
      <el-form ref="forgotFormRef" :model="forgotForm" :rules="forgotRules" label-width="80px">
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="forgotForm.phone" placeholder="请输入注册时的手机号" />
        </el-form-item>
        <el-form-item label="真实姓名" prop="full_name">
          <el-input v-model="forgotForm.full_name" placeholder="请输入注册时的真实姓名" />
        </el-form-item>
      </el-form>
      <div v-if="resetResult" style="background:#f0f9eb;padding:16px;border-radius:8px;margin-bottom:12px">
        <p style="color:#67c23a;font-weight:bold;margin:0 0 8px">✅ 密码已重置</p>
        <p style="margin:4px 0">用户名：<b>{{ resetResult.username }}</b></p>
        <p style="margin:4px 0">新密码：<b style="color:#e6a23c;font-size:16px">{{ resetResult.new_password }}</b></p>
        <p style="color:#999;font-size:12px;margin:8px 0 0">请牢记新密码，登录后可自行修改</p>
      </div>
      <template #footer>
        <el-button @click="showForgotDialog = false; resetResult = null">关闭</el-button>
        <el-button type="primary" :loading="resetting" @click="handleForgotPassword" :disabled="!!resetResult">重置密码</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import api from '../../api'

const router = useRouter()
const formRef = ref<FormInstance>()

const form = reactive({
  username: '',
  password: '',
})

const loading = ref(false)

// 忘记密码
const showForgotDialog = ref(false)
const resetting = ref(false)
const resetResult = ref<any>(null)
const forgotFormRef = ref<FormInstance>()
const forgotForm = reactive({ phone: '', full_name: '' })
const forgotRules: FormRules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' },
  ],
  full_name: [{ required: true, message: '请输入真实姓名', trigger: 'blur' }],
}

async function handleForgotPassword() {
  const valid = await forgotFormRef.value?.validate().catch(() => false)
  if (!valid) return
  resetting.value = true
  try {
    const res = await api.post('/auth/forgot-password', forgotForm)
    resetResult.value = res.data
    ElMessage.success('密码已重置')
  } catch {
    // Error handled by interceptor
  } finally {
    resetting.value = false
  }
}

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const res = await api.post('/auth/login', form)
    localStorage.setItem('token', res.data.access_token)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
}
.login-card {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}
.login-title {
  text-align: center;
  margin: 0 0 4px;
  color: #1a73e8;
  font-size: 24px;
}
.login-subtitle {
  text-align: center;
  color: #999;
  margin-bottom: 32px;
  font-size: 14px;
}
.login-btn {
  width: 100%;
}
.login-footer {
  text-align: center;
  margin-top: 16px;
  font-size: 14px;
  color: #666;
}
.register-link {
  color: #1a73e8;
  text-decoration: none;
}
.register-link:hover {
  text-decoration: underline;
}
</style>
