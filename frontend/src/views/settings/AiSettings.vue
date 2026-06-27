<template>
  <div class="ai-settings" v-loading="pageLoading">
    <h2>🤖 AI 供应商配置</h2>

    <!-- ─── 权限检查 ─── -->
    <el-alert
      v-if="!isAdmin"
      title="权限不足"
      type="warning"
      :description="'仅系统管理员(admin)可访问此页面'"
      show-icon
      center
      class="permission-alert"
    />

    <template v-if="isAdmin">
      <!-- ═══════════════ Provider 配置表单 ═══════════════ -->
      <el-card shadow="never" class="section-card">
        <template #header>
          <div class="card-header">
            <span>{{ editingId ? '编辑供应商' : '新增供应商' }}</span>
            <el-button size="small" text @click="resetForm" v-if="editingId">
              取消编辑
            </el-button>
          </div>
        </template>
        <el-form
          ref="formRef"
          :model="form"
          :rules="formRules"
          label-width="110px"
          size="default"
          @submit.prevent="handleSubmit"
        >
          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="供应商名称" prop="provider">
                <el-select v-model="form.provider" placeholder="选择或输入" allow-create filterable clearable style="width:100%">
                  <el-option label="OpenAI" value="openai" />
                  <el-option label="DeepSeek" value="deepseek" />
                  <el-option label="通义千问(Qwen)" value="qwen" />
                  <el-option label="文心一言(ERNIE)" value="ernie" />
                  <el-option label="Claude(Anthropic)" value="claude" />
                  <el-option label="智谱AI(GLM)" value="glm" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="模型名称" prop="model">
                <el-input v-model="form.model" placeholder="如 gpt-4o, deepseek-chat, qwen-plus" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="API 基础地址" prop="api_base">
                <el-input v-model="form.api_base" placeholder="可留空使用官方默认地址" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="API 密钥" prop="api_key">
                <el-input
                  v-model="form.api_key"
                  type="password"
                  show-password
                  placeholder="输入 API Key（加密存储）"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="温度参数" prop="temperature">
                <el-slider
                  v-model.number="form.temperature"
                  :min="0"
                  :max="2"
                  :step="0.1"
                  show-input
                  :show-input-controls="false"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="最大 Token" prop="max_tokens">
                <el-input-number v-model.number="form.max_tokens" :min="256" :max="128000" :step="1024" style="width:200px" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item>
            <el-button type="primary" :loading="submitting" @click="handleSubmit">
              {{ editingId ? '更新配置' : '创建配置' }}
            </el-button>
            <el-button
              v-if="editingId"
              type="success"
              plain
              :loading="testingId === editingId"
              @click="handleTestConnection"
            >
              测试连接
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- ═══════════════ 已配置供应商列表 ═══════════════ -->
      <el-card shadow="never" class="section-card">
        <template #header>
          <div class="card-header">
            <span>📋 已配置供应商</span>
            <el-button size="small" text @click="fetchConfigs">刷新</el-button>
          </div>
        </template>
        <el-table
          :data="configList"
          border
          size="small"
          style="width:100%"
          max-height="360"
          v-loading="configLoading"
        >
          <el-table-column prop="provider" label="供应商" width="120">
            <template #default="{ row }">
              <el-tag>{{ row.provider }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="model" label="模型" min-width="140" />
          <el-table-column prop="api_base" label="API Base" min-width="180" show-overflow-tooltip />
          <el-table-column prop="temperature" label="温度" width="80" align="center">
            <template #default="{ row }">{{ row.temperature ?? '-' }}</template>
          </el-table-column>
          <el-table-column prop="enabled" label="状态" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
                {{ row.enabled ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button size="small" text @click="editConfig(row)">编辑</el-button>
              <el-button
                size="small"
                text
                type="primary"
                :loading="testingId === row.id"
                @click="handleTestConnection(row.id)"
              >
                测试
              </el-button>
              <el-popconfirm title="确认删除此配置？" @confirm="deleteConfig(row.id)">
                <template #reference>
                  <el-button size="small" text type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- ═══════════════ 调用日志列表 ═══════════════ -->
      <el-card shadow="never" class="section-card">
        <template #header>
          <div class="card-header">
            <span>📊 调用日志（最近 200 条）</span>
            <div class="header-right">
              <el-select
                v-model="logQuery.provider"
                placeholder="筛选供应商"
                clearable
                size="small"
                style="width:140px;margin-right:8px"
                @change="fetchLogs"
              >
                <el-option v-for="c in configList" :key="c.provider" :label="c.provider" :value="c.provider" />
              </el-select>
              <el-button size="small" text @click="fetchLogs">刷新</el-button>
            </div>
          </div>
        </template>
        <!-- 汇总统计 -->
        <el-row :gutter="16" class="stats-row" v-if="logStats">
          <el-col :span="8">
            <div class="stat-card">
              <span class="stat-label">总 Token 消耗</span>
              <span class="stat-value">{{ (logStats.total_tokens ?? 0).toLocaleString() }}</span>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-card">
              <span class="stat-label">总成本</span>
              <span class="stat-value">¥{{ (logStats.total_cost ?? 0).toFixed(4) }}</span>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-card">
              <span class="stat-label">成功率</span>
              <span class="stat-value" :class="successRateClass(logStats.success_rate)">
                {{ ((logStats.success_rate ?? 1) * 100).toFixed(1) }}%
              </span>
            </div>
          </el-col>
        </el-row>
        <el-table
          :data="logList"
          border
          size="small"
          style="width:100%"
          max-height="480"
          v-loading="logLoading"
          :default-sort="{ prop: 'created_at', order: 'descending' }"
        >
          <el-table-column prop="created_at" label="时间" width="150" sortable>
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="provider" label="供应商" width="90">
            <template #default="{ row }">
              <el-tag size="small">{{ row.provider }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="model" label="模型" width="130" show-overflow-tooltip />
          <el-table-column prop="prompt_tokens" label="输入 Token" width="100" align="right" sortable />
          <el-table-column prop="completion_tokens" label="输出 Token" width="100" align="right" sortable />
          <el-table-column label="合计 Token" width="100" align="right" sortable>
            <template #default="{ row }">
              {{ (row.prompt_tokens + row.completion_tokens).toLocaleString() }}
            </template>
          </el-table-column>
          <el-table-column prop="cost" label="成本" width="90" align="right" sortable>
            <template #default="{ row }">
              ¥{{ row.cost.toFixed(4) }}
            </template>
          </el-table-column>
          <el-table-column prop="response_time_ms" label="耗时(ms)" width="90" align="right" sortable />
          <el-table-column prop="success" label="结果" width="70" align="center">
            <template #default="{ row }">
              <el-tag :type="row.success ? 'success' : 'danger'" size="small">
                {{ row.success ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="error" label="错误信息" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.error" style="color:#f56c6c">{{ row.error }}</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="!logLoading && logList.length === 0" class="empty-hint">
          暂无调用记录
        </div>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/index'
import { useAuthStore } from '../../stores/auth'

// 类型定义
interface AIConfig {
  id: number
  provider: string
  model: string
  api_base: string
  api_key: string
  temperature: number
  max_tokens: number
  enabled: boolean
  created_at: string
  updated_at: string
}

interface AICallLog {
  id: number
  request_id: string
  provider: string
  model: string
  prompt_tokens: number
  completion_tokens: number
  cost: number
  response_time_ms: number
  success: boolean
  error: string | null
  created_at: string
}

interface LogStats {
  total_tokens?: number
  total_cost?: number
  success_rate?: number
}

// ── 状态 ──
const authStore = useAuthStore()
const isAdmin = computed(() => authStore.user?.role === 'admin')

const pageLoading = ref(false)
const configList = ref<AIConfig[]>([])
const configLoading = ref(false)
const logList = ref<AICallLog[]>([])
const logLoading = ref(false)
const logStats = ref<LogStats | null>(null)
const submitting = ref(false)
const testingId = ref<number | null>(null)
const editingId = ref<number | null>(null)

const logQuery = reactive<{ provider: string }>({ provider: '' })

// ── 表单 ──
const formRef = ref()
const defaultForm = () => ({
  provider: '',
  model: '',
  api_base: '',
  api_key: '',
  temperature: 0.7,
  max_tokens: 4096,
})
const form = reactive<{
  provider: string
  model: string
  api_base: string
  api_key: string
  temperature: number
  max_tokens: number
}>(defaultForm())

const formRules = {
  provider: [{ required: true, message: '请选择或输入供应商名称', trigger: 'change' }],
  model: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  api_key: [{ required: true, message: '请输入 API Key', trigger: 'blur' }],
  temperature: [{ type: 'number', min: 0, max: 2, message: '范围 0～2', trigger: 'blur' }],
}

// ── API 调用 ──

async function fetchConfigs() {
  configLoading.value = true
  try {
    const res = await api.get('/admin/ai-configs')
    configList.value = res.data ?? []
  } catch {
    // api interceptor 已处理错误提示
  } finally {
    configLoading.value = false
  }
}

async function fetchLogs() {
  logLoading.value = true
  try {
    const params: Record<string, any> = { page: 1, page_size: 200 }
    if (logQuery.provider) params.provider = logQuery.provider
    const res = await api.get('/admin/ai-call-logs', { params })
    const data = res.data
    logList.value = data.items ?? []
    logStats.value = {
      total_tokens: data.total_tokens,
      total_cost: data.total_cost,
      success_rate: data.success_rate,
    }
  } catch {
    // api interceptor 已处理
  } finally {
    logLoading.value = false
  }
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (editingId.value) {
      await api.put(`/admin/ai-configs/${editingId.value}`, form)
      ElMessage.success('配置已更新')
    } else {
      await api.post('/admin/ai-configs', form)
      ElMessage.success('配置已创建')
    }
    resetForm()
    await fetchConfigs()
  } catch {
    // api interceptor 已处理
  } finally {
    submitting.value = false
  }
}

function editConfig(row: AIConfig) {
  editingId.value = row.id
  form.provider = row.provider
  form.model = row.model
  form.api_base = row.api_base || ''
  form.api_key = ''  // 不回显密钥，让用户重新输入
  form.temperature = row.temperature ?? 0.7
  form.max_tokens = row.max_tokens ?? 4096
}

function resetForm() {
  editingId.value = null
  Object.assign(form, defaultForm())
  formRef.value?.resetFields()
}

async function deleteConfig(id: number) {
  try {
    await api.delete(`/admin/ai-configs/${id}`)
    ElMessage.success('配置已删除')
    await fetchConfigs()
  } catch {
    // api interceptor 已处理
  }
}

async function handleTestConnection(configId?: number) {
  const id = configId ?? editingId.value
  if (!id) {
    ElMessage.warning('请先保存配置后再测试')
    return
  }
  testingId.value = id
  try {
    const res = await api.post(`/admin/ai-configs/${id}/test`)
    const msg = res.data?.message ?? '连接测试成功'
    ElMessage.success(msg)
  } catch {
    ElMessage.error('连接测试失败，请检查配置参数')
  } finally {
    testingId.value = null
  }
}

// ── 工具 ──

function formatTime(iso: string): string {
  if (!iso) return '-'
  try {
    const d = new Date(iso)
    const pad = (n: number) => n.toString().padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch {
    return iso
  }
}

function successRateClass(rate: number | undefined): string {
  if (rate === undefined) return ''
  if (rate >= 0.99) return 'rate-good'
  if (rate >= 0.9) return 'rate-ok'
  return 'rate-bad'
}

// ── 生命周期 ──
onMounted(async () => {
  if (!isAdmin.value) return
  pageLoading.value = true
  await Promise.all([fetchConfigs(), fetchLogs()])
  pageLoading.value = false
})
</script>

<style scoped>
.ai-settings {
  padding: 16px;
}

.ai-settings h2 {
  margin: 0 0 16px;
  font-size: 18px;
}

.permission-alert {
  margin-bottom: 16px;
}

.section-card {
  margin-top: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-right {
  display: flex;
  align-items: center;
}

.stats-row {
  margin-bottom: 16px;
}

.stat-card {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.rate-good { color: #67c23a; }
.rate-ok { color: #e6a23c; }
.rate-bad { color: #f56c6c; }

.empty-hint {
  text-align: center;
  color: #999;
  font-size: 13px;
  padding: 24px 0;
}

.el-form {
  max-width: 900px;
}
</style>
