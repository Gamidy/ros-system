<template>
  <div class="saga-chain-viewer">
    <!-- ═══════ 顶部标题 + 查询框 ═══════ -->
    <div class="scv-header">
      <h2>🔗 Saga 事务查看器</h2>
      <div class="scv-search">
        <el-input
          v-model="sagaId"
          placeholder="输入 Saga ID 查询"
          size="small"
          style="width:300px"
          clearable
          @keyup.enter="fetchSaga"
        />
        <el-button type="primary" size="small" :loading="loading" @click="fetchSaga">查询</el-button>
      </div>
    </div>

    <!-- ═══════ 加载态 / 空态 ═══════ -->
    <div v-loading="loading" element-loading-text="加载 Saga 链...">
      <el-empty
        v-if="!loading && !sagaData && !errorMsg"
        description="请输入 Saga ID 进行查询"
        :image-size="70"
        style="margin-top:60px"
      />
      <el-empty
        v-if="errorMsg && !loading"
        :description="errorMsg"
        :image-size="60"
        style="margin-top:60px"
      />
    </div>

    <!-- ═══════ Saga 基本信息 ═══════ -->
    <div v-if="sagaData && !loading" class="scv-content">
      <el-card shadow="never" class="saga-info-card">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="Saga ID">
            <code>{{ sagaData.saga_id || sagaData.id }}</code>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="sagaStatusType" size="small" effect="dark">
              {{ sagaData.status || '—' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ formatTime(sagaData.started_at || sagaData.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="结束时间" v-if="sagaData.completed_at || sagaData.updated_at">
            {{ formatTime(sagaData.completed_at || sagaData.updated_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="关联 Plan" v-if="sagaData.plan_id">
            {{ sagaData.plan_id }}
          </el-descriptions-item>
          <el-descriptions-item label="步骤数" v-if="sagaData.steps">
            {{ sagaData.steps.length }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- ═══════ Saga 步骤链 ═══════ -->
      <el-card shadow="never" class="steps-card" v-if="sagaData.steps && sagaData.steps.length > 0">
        <template #header>
          <span style="font-weight:600">步骤链</span>
        </template>

        <el-steps :active="currentStepIndex" align-center finish-status="success" process-status="process" direction="vertical">
          <el-step
            v-for="(step, idx) in sagaData.steps"
            :key="idx"
            :status="stepStatus(step)"
            :title="step.action || step.name || `步骤 ${Number(idx) + 1}`"
          >
            <template #description>
              <div class="step-description">
                <div class="step-meta">
                  <el-tag
                    :type="stepTagType(step)"
                    size="small"
                    effect="plain"
                  >
                    {{ step.status || 'pending' }}
                  </el-tag>
                  <span class="step-time" v-if="step.completed_at || step.created_at">
                    {{ formatTime(step.completed_at || step.created_at) }}
                  </span>
                </div>
                <div class="step-result" v-if="step.result">
                  <span class="step-result-label">结果:</span>
                  <pre class="step-result-json">{{ JSON.stringify(step.result, null, 2) }}</pre>
                </div>
                <div class="step-detail" v-if="step.detail">
                  <pre class="step-result-json">{{ JSON.stringify(step.detail, null, 2) }}</pre>
                </div>
                <div class="step-error" v-if="step.error || step.err">
                  <el-alert
                    :title="step.error || step.err"
                    type="error"
                    show-icon
                    :closable="false"
                  />
                </div>
              </div>
            </template>
          </el-step>
        </el-steps>
      </el-card>

      <!-- 无 steps 字段的兜底 -->
      <el-empty
        v-if="sagaData && (!sagaData.steps || sagaData.steps.length === 0)"
        description="该 Saga 无步骤数据"
        :image-size="50"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

// ── Types ──
interface SagaStep {
  action?: string
  name?: string
  status?: string
  completed_at?: string
  created_at?: string
  result?: Record<string, unknown>
  detail?: Record<string, unknown>
  error?: string
  err?: string
}

interface SagaData {
  saga_id?: string
  id?: number | string
  status?: string
  started_at?: string
  created_at?: string
  completed_at?: string
  updated_at?: string
  plan_id?: number | string
  steps?: SagaStep[]
}

// ── Data ──
const sagaId = ref('')
const sagaData = ref<SagaData | null>(null)
const loading = ref(false)
const errorMsg = ref('')

// ── Computed ──
const sagaStatus = computed(() => sagaData.value?.status || '')
const sagaStatusType = computed(() => {
  const map: Record<string, string> = {
    completed: 'success',
    failed: 'danger',
    compensating: 'warning',
    compensated: 'info',
    pending: 'info',
    running: 'primary',
  }
  return map[sagaStatus.value] || 'info'
})

const currentStepIndex = computed(() => {
  if (!sagaData.value?.steps) return 0
  const steps = sagaData.value.steps
  for (let i = 0; i < steps.length; i++) {
    const s = steps[i].status || ''
    if (s === 'failed' || s === 'compensated' || s === 'pending') return i
    if (s === 'running') return i
  }
  return steps.length
})

// ── Helpers ──
function formatTime(iso: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function stepStatus(step: SagaStep): 'wait' | 'process' | 'finish' | 'error' | 'success' {
  const s = step.status || 'pending'
  if (s === 'success' || s === 'completed') return 'success'
  if (s === 'failed') return 'error'
  if (s === 'compensated') return 'finish'
  if (s === 'running' || s === 'processing') return 'process'
  return 'wait'
}

function stepTagType(step: SagaStep): string {
  const map: Record<string, string> = {
    success: 'success',
    completed: 'success',
    failed: 'danger',
    compensating: 'warning',
    compensated: 'info',
    running: 'primary',
    processing: 'primary',
    pending: 'info',
  }
  return map[step.status] || 'info'
}

// ── API ──
async function fetchSaga() {
  const id = sagaId.value.trim()
  if (!id) {
    ElMessage.warning('请输入 Saga ID')
    return
  }
  loading.value = true
  errorMsg.value = ''
  sagaData.value = null
  try {
    const res = await api.get(`/api/v2/events/saga/${encodeURIComponent(id)}`)
    sagaData.value = res.data
  } catch (e: unknown) {
    if (e && typeof e === 'object' && 'response' in e) {
      const resp = (e as {response?: {status?: number; data?: {detail?: string}}}).response
      if (resp?.status === 404) {
        errorMsg.value = '未找到该 Saga 记录'
      } else {
        errorMsg.value = resp?.data?.detail || '查询失败，请稍后重试'
      }
    } else {
      errorMsg.value = '查询失败，请稍后重试'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.saga-chain-viewer {
  padding: 0 4px;
}
.scv-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;
}
.scv-header h2 {
  margin: 0;
  font-size: 18px;
}
.scv-search {
  display: flex;
  align-items: center;
  gap: 8px;
}
.scv-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.saga-info-card {
  border-radius: 8px;
}
.steps-card {
  border-radius: 8px;
}
.step-description {
  margin-top: 4px;
  padding: 4px 0;
}
.step-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.step-time {
  font-size: 12px;
  color: #909399;
}
.step-result {
  margin-top: 6px;
}
.step-result-label {
  font-size: 12px;
  font-weight: 600;
  color: #606266;
  display: block;
  margin-bottom: 4px;
}
.step-result-json {
  background: #f5f7fa;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 11px;
  line-height: 1.4;
  max-height: 160px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
.step-detail {
  margin-top: 4px;
}
.step-error {
  margin-top: 6px;
}
</style>
