<template>
  <div class="register-container">
    <div class="register-card">
      <h1 class="register-title">ROS 研发运营系统</h1>
      <p class="register-subtitle">账号申请</p>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="80px"
        size="large"
      >
        <el-form-item label="真实姓名" prop="displayName">
          <el-input v-model="form.displayName" placeholder="请输入真实姓名（将作为登录名）" />
          <span style="font-size:12px;color:#999;margin-left:8px;">将作为登录账号名</span>
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="部门" prop="department">
          <el-input v-model="form.department" placeholder="请输入所属部门" />
        </el-form-item>
        <el-form-item label="职位" prop="position">
          <el-input v-model="form.position" placeholder="请输入职位" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            class="register-btn"
            @click="handleSubmit"
          >
            {{ loading ? '提交中...' : '提交申请' }}
          </el-button>
        </el-form-item>
      </el-form>
      <div class="register-footer">
        已有账号？
        <router-link to="/login" class="register-link">去登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import api from '../../api'

const formRef = ref<FormInstance>()

const form = reactive({
  password: '',
  confirmPassword: '',
  displayName: '',
  department: '',
  position: '',
  phone: '',
})

const loading = ref(false)

const validateConfirmPassword = (_rule: any, value: string, callback: any) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 128, message: '密码长度不能少于 6 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
  displayName: [
    { required: true, message: '请输入真实姓名', trigger: 'blur' },
    { min: 2, max: 50, message: '姓名长度在 2 到 50 个字符', trigger: 'blur' },
  ],
  department: [
    { required: true, message: '请输入部门', trigger: 'blur' },
  ],
  position: [
    { required: true, message: '请输入职位', trigger: 'blur' },
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' },
  ],
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    // 用真实姓名作为登录账号名
    await api.post('/auth/apply', {
      username: form.displayName,
      password: form.password,
      full_name: form.displayName,
      department: form.department,
      position: form.position,
      phone: form.phone,
    })
    ElMessage.success('申请已提交，等待研发总监审批')
    // Reset form after successful submission
    formRef.value?.resetFields()
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
  padding: 40px 0;
}
.register-card {
  width: 520px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}
.register-title {
  text-align: center;
  margin: 0 0 4px;
  color: #1a73e8;
  font-size: 24px;
}
.register-subtitle {
  text-align: center;
  color: #999;
  margin-bottom: 32px;
  font-size: 14px;
}
.register-btn {
  width: 100%;
}
.register-footer {
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
