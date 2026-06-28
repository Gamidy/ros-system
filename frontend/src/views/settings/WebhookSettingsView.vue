<template>
  <div class="webhook-settings" v-loading="pageLoading">
    <div class="page-header">
      <h2>🔗 Webhook 订阅配置</h2>
      <el-button type="primary" size="small" @click="openCreate">
        + 新建订阅
      </el-button>
    </div>

    <!-- ═══════════════ 订阅列表 ═══════════════ -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span>📋 订阅列表</span>
          <el-button size="small" text @click="fetchList">刷新</el-button>
        </div>
      </template>
      <el-table
        :data="list"
        border
        size="small"
        style="width: 100%"
        max-height="520"
        v-loading="listLoading"
      >
        <el-table-column prop="name" label="名称" min-width="130" show-overflow-tooltip />
        <el-table-column prop="url" label="URL" min-width="200" show-overflow-tooltip />
        <el-table-column prop="event_type" label="事件类型" width="140">
          <template #default="{ row }">
            <el-tag size="small">{{ eventTypeLabel(row.event_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
              {{ row.enabled ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_by" label="创建人" width="100" show-overflow-tooltip />
        <el-table-column prop="updated_at" label="更新时间" width="150">
          <template #default="{ row }">
            {{ formatTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text @click="openEdit(row)">编辑</el-button>
            <el-button
              size="small"
              text
              type="primary"
              :loading="testingId === row.id"
              @click="handleTest(row)"
            >
              测试
            </el-button>
            <el-button size="small" text type="primary" @click="openLogDrawer(row)">
              日志
            </el-button>
            <el-popconfirm title="确认删除此 Webhook 订阅？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button size="small" text type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!listLoading && list.length === 0" class="empty-hint">
        暂无 Webhook 订阅
      </div>
    </el-card>

    <!-- ═══════════════ 新建/编辑 弹窗 ═══════════════ -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑 Webhook 订阅' : '新建 Webhook 订阅'"
      width="560px"
      :close-on-click-modal="false"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="100px"
        size="default"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如：审批通知推送" />
        </el-form-item>
        <el-form-item label="URL" prop="url">
          <el-input v-model="form.url" placeholder="https://hooks.example.com/webhook" />
        </el-form-item>
        <el-form-item label="事件类型" prop="event_type">
          <el-select v-model="form.event_type" placeholder="选择事件类型" style="width: 100%">
            <el-option
              v-for="opt in eventTypeOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="密钥" prop="secret">
          <el-input
            v-model="form.secret"
            type="password"
            show-password
            placeholder="可选，用于签名验证"
          />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ editingId ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- ═══════════════ 发送日志抽屉 ═══════════════ -->
    <el-drawer
      v-model="logDrawerVisible"
      :title="`📤 发送日志 — ${logDrawerWebhookName}`"
      size="600px"
      @closed="resetLogs"
    >
      <el-table
        :data="logList"
        border
        size="small"
        style="width: 100%"
        max-height="560"
        v-loading="logLoading"
      >
        <el-table-column prop="event_type" label="事件类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ eventTypeLabel(row.event_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="response_status" label="状态码" width="80" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.response_status >= 200 && row.response_status < 300 ? 'success' : 'danger'"
              size="small"
            >
              {{ row.response_status ?? '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="success" label="成功" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="row.success ? 'success' : 'danger'" size="small">
              {{ row.success ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="attempted_at" label="发送时间" width="150">
          <template #default="{ row }">
            {{ formatTime(row.attempted_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="retry_count" label="重试次数" width="80" align="center" />
      </el-table>
      <div v-if="!logLoading && logList.length === 0" class="empty-hint">
        暂无发送日志
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/index'

/* ── 类型定义 ── */

interface WebhookSubscription {
  id: number
  name: string
  url: string
  event_type: string
  /** API 返回时 secret 已掩码 */
  secret: string
  enabled: boolean
  created_by: string
  created_at: string
  updated_at: string
}

interface WebhookLog {
  id: number
  event_type: string
  payload_truncated: string
  response_status: number
  response_body: string
  success: boolean
  attempted_at: string
  retry_count: number
}

interface WebhookForm {
  name: string
  url: string
  event_type: string
  secret: string
  enabled: boolean
}

/* ── 常量 ── */

const EVENT_TYPE_LABELS: Record<string, string> = {
  'plan.approved': '策划审批通过',
  'plan.submitted': '策划提交',
  'review.created': '评审创建',
  'gate.passed': '评审门通过',
  'cost.alert': '成本预警',
  'all events': '所有事件',
}

const eventTypeOptions = [
  { value: 'plan.approved', label: '策划审批通过 (plan.approved)' },
  { value: 'plan.submitted', label: '策划提交 (plan.submitted)' },
  { value: 'review.created', label: '评审创建 (review.created)' },
  { value: 'gate.passed', label: '评审门通过 (gate.passed)' },
  { value: 'cost.alert', label: '成本预警 (cost.alert)' },
  { value: 'all events', label: '所有事件 (all events)' },
]

/* ── 状态 ── */

const pageLoading = ref(false)
const listLoading = ref(false)
const list = ref<WebhookSubscription[]>([])

// 新建/编辑弹窗
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)

const defaultForm = (): WebhookForm => ({
  name: '',
  url: '',
  event_type: '',
  secret: '',
  enabled: true,
})

const form = reactive<WebhookForm>(defaultForm())
const formRef = ref()

const formRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  url: [
    { required: true, message: '请输入 URL', trigger: 'blur' },
    { type: 'url', message: '请输入有效的 URL', trigger: 'blur' },
  ],
  event_type: [{ required: true, message: '请选择事件类型', trigger: 'change' }],
}

// 测试
const testingId = ref<number | null>(null)

// 日志抽屉
const logDrawerVisible = ref(false)
const logDrawerWebhookName = ref('')
const logDrawerWebhookId = ref<number | null>(null)
const logLoading = ref(false)
const logList = ref<WebhookLog[]>([])

/* ── API ── */

/** 获取 Webhook 订阅列表 */
async function fetchList() {
  listLoading.value = true
  try {
    const res = await api.get('/api/webhooks')
    list.value = res.data ?? []
  } catch {
    // interceptor 已处理
  } finally {
    listLoading.value = false
  }
}

/** 打开新建弹窗 */
function openCreate() {
  editingId.value = null
  Object.assign(form, defaultForm())
  dialogVisible.value = true
}

/** 打开编辑弹窗 */
function openEdit(row: WebhookSubscription) {
  editingId.value = row.id
  form.name = row.name
  form.url = row.url
  form.event_type = row.event_type
  form.secret = row.secret
  form.enabled = row.enabled
  dialogVisible.value = true
}

/** 重置表单 */
function resetForm() {
  editingId.value = null
  Object.assign(form, defaultForm())
  formRef.value?.resetFields()
}

/** 提交新建/编辑 */
async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const payload = {
      name: form.name,
      url: form.url,
      event_type: form.event_type,
      secret: form.secret || undefined,
      enabled: form.enabled,
    }
    if (editingId.value) {
      await api.put(`/api/webhooks/${editingId.value}`, payload)
      ElMessage.success('Webhook 订阅已更新')
    } else {
      await api.post('/api/webhooks', payload)
      ElMessage.success('Webhook 订阅已创建')
    }
    dialogVisible.value = false
    await fetchList()
  } catch {
    // interceptor 已处理
  } finally {
    submitting.value = false
  }
}

/** 删除订阅 */
async function handleDelete(id: number) {
  try {
    await api.delete(`/api/webhooks/${id}`)
    ElMessage.success('Webhook 订阅已删除')
    await fetchList()
  } catch {
    // interceptor 已处理
  }
}

/** 测试发送 */
async function handleTest(row: WebhookSubscription) {
  testingId.value = row.id
  try {
    const res = await api.post(`/api/webhooks/${row.id}/test`)
    const msg = res.data?.message ?? '测试发送成功'
    ElMessage.success(msg)
  } catch {
    ElMessage.error('测试发送失败，请检查订阅 URL 和配置')
  } finally {
    testingId.value = null
  }
}

/** 打开发送日志抽屉 */
async function openLogDrawer(row: WebhookSubscription) {
  logDrawerWebhookId.value = row.id
  logDrawerWebhookName.value = row.name
  logDrawerVisible.value = true
  await fetchLogs(row.id)
}

/** 获取发送日志 */
async function fetchLogs(webhookId: number) {
  logLoading.value = true
  try {
    const res = await api.get(`/api/webhooks/${webhookId}/logs`, { params: { limit: 50 } })
    logList.value = res.data ?? []
  } catch {
    // interceptor 已处理
  } finally {
    logLoading.value = false
  }
}

/** 重置日志状态 */
function resetLogs() {
  logList.value = []
  logDrawerWebhookId.value = null
}

/* ── 工具 ── */

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

function eventTypeLabel(t: string): string {
  return EVENT_TYPE_LABELS[t] ?? t
}

/* ── 生命周期 ── */

onMounted(async () => {
  pageLoading.value = true
  await fetchList()
  pageLoading.value = false
})
</script>

<style scoped>
.webhook-settings {
  padding: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 18px;
}

.section-card {
  margin-top: 0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.empty-hint {
  padding: 32px 0;
  text-align: center;
  color: #909399;
  font-size: 14px;
}
</style>
