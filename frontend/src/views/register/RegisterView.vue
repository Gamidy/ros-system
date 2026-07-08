<template>
  <div class="claude-register">
    <div class="register-container">
      <!-- Left Side - Branding -->
      <div class="register-left">
        <div class="register-brand">
          <div class="brand-logo">
            <span class="brand-mark">R</span>
          </div>
          <h1 class="brand-title">ROS 研发运营系统</h1>
          <p class="brand-subtitle">R&amp;D Operations System</p>
        </div>
        <div class="register-features">
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

      <!-- Right Side - Registration Form -->
      <div class="register-right">
        <div class="register-card">
          <h2 class="register-title">申请账号</h2>
          <p class="register-desc">请填写信息，提交后等待管理员审核</p>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-width="0"
            class="register-form"
          >
            <el-form-item prop="name">
              <div class="input-label">姓名</div>
              <el-input
                v-model="form.name"
                placeholder="请输入您的姓名"
                size="large"
                class="claude-input"
              />
            </el-form-item>

            <el-form-item prop="email">
              <div class="input-label">邮箱</div>
              <el-input
                v-model="form.email"
                placeholder="请输入工作邮箱"
                size="large"
                class="claude-input"
              />
            </el-form-item>

            <el-form-item prop="organization">
              <div class="input-label">所属部门/组织</div>
              <el-input
                v-model="form.organization"
                placeholder="请输入部门或组织名称"
                size="large"
                class="claude-input"
              />
            </el-form-item>

            <el-form-item prop="reason">
              <div class="input-label">申请原因</div>
              <el-input
                v-model="form.reason"
                type="textarea"
                :rows="3"
                placeholder="请简要说明需要使用本系统的原因"
                class="claude-input"
              />
            </el-form-item>

            <el-form-item>
              <button
                class="register-btn"
                :class="{ loading }"
                :disabled="loading"
                @click="handleSubmit"
              >
                <span v-if="!loading">提交申请</span>
                <span v-else class="btn-loading">
                  <span class="loading-dot" />
                  <span class="loading-dot" />
                  <span class="loading-dot" />
                </span>
              </button>
            </el-form-item>
          </el-form>

          <!-- Contact admin info -->
          <div class="contact-admin">
            <el-icon class="admin-icon"><Message /></el-icon>
            <span>您也可以通过邮件联系管理员申请账号：</span>
            <a class="admin-email" href="mailto:admin@ros-system.com">admin@ros-system.com</a>
          </div>

          <div class="register-footer">
            <span>已有账号？</span>
            <a class="login-link" @click="goToLogin">返回登录</a>
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
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Message } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'

const router = useRouter()
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  email: '',
  organization: '',
  reason: '',
})
const loading = ref(false)

const rules: FormRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  organization: [{ required: true, message: '请输入部门或组织名称', trigger: 'blur' }],
  reason: [{ required: true, message: '请输入申请原因', trigger: 'blur' }],
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  // Simulate submission — in production, call an API endpoint
  setTimeout(() => {
    loading.value = false
    ElMessage.success({
      message: '申请已提交，请等待管理员审核（通常1-2个工作日）',
      grouping: true,
      duration: 5000,
    })
    formRef.value?.resetFields()
  }, 1200)
}

function goToLogin() {
  router.push('/login')
}
</script>

<style scoped>
.claude-register {
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

/* Register Container */
.register-container {
  display: flex;
  width: 100%;
  max-width: 1000px;
  min-height: 620px;
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
.register-left {
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
.register-left::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 30% 70%, rgba(255,255,255,0.1) 0%, transparent 50%),
    radial-gradient(circle at 70% 30%, rgba(255,255,255,0.08) 0%, transparent 40%);
}

.register-brand {
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

.register-features {
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
.register-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px;
  min-width: 420px;
}

.register-card {
  max-width: 380px;
  margin: 0 auto;
  width: 100%;
}

.register-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a1917;
  margin: 0 0 4px;
  letter-spacing: -0.3px;
}
.register-desc {
  font-size: 14px;
  color: #5e5d59;
  margin: 0 0 28px;
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.input-label {
  font-size: 13px;
  font-weight: 600;
  color: #1a1917;
  margin-bottom: 6px;
}

.register-btn {
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
.register-btn:hover:not(:disabled) {
  background: #c96442;
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(217, 119, 87, 0.3);
}
.register-btn:disabled {
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

/* Contact Admin Section */
.contact-admin {
  margin-top: 20px;
  padding: 14px 16px;
  background: #fdf3ed;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #5e5d59;
  line-height: 1.5;
  flex-wrap: wrap;
}
.admin-icon {
  color: #d97757;
  font-size: 16px;
  flex-shrink: 0;
}
.admin-email {
  color: #d97757;
  font-weight: 600;
  text-decoration: none;
  transition: color 0.15s;
}
.admin-email:hover {
  color: #c96442;
  text-decoration: underline;
}

.register-footer {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
}
.register-footer span {
  color: #5e5d59;
}
.login-link {
  color: #d97757;
  cursor: pointer;
  font-weight: 600;
  text-decoration: none;
  transition: color 0.15s;
  position: relative;
}
.login-link::after {
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
.login-link:hover {
  color: #c96442;
}
.login-link:hover::after {
  transform: scaleX(1);
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
:deep(.claude-input .el-textarea__inner) {
  background: #f0efe8 !important;
  border-radius: 12px !important;
  box-shadow: inset 0 0 0 1px #e5e0da !important;
  padding: 10px 14px !important;
  font-size: 15px;
  color: #1a1917;
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important;
  font-family: inherit;
}
:deep(.claude-input .el-textarea__inner:hover) {
  box-shadow: inset 0 0 0 1px #87867f !important;
}
:deep(.claude-input .el-textarea__inner:focus) {
  box-shadow: inset 0 0 0 1px #d97757, 0 0 0 3px rgba(217, 119, 87, 0.12) !important;
}
:deep(.claude-input .el-textarea__inner::placeholder) {
  color: #87867f;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .register-container {
    flex-direction: column;
    max-width: 100%;
    min-height: auto;
    border-radius: 0;
    box-shadow: none;
  }
  .register-left {
    padding: 32px 24px;
    min-height: 200px;
  }
  .register-right {
    padding: 32px 24px;
    min-width: auto;
  }
  .register-features {
    display: none;
  }
  .claude-register {
    background: #fff;
  }
  .bg-decoration {
    display: none;
  }
}
</style>
