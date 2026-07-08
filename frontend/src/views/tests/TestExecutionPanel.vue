<template>
  <div class="execution-panel">
    <div class="panel-header">
      <span class="panel-title">执行记录</span>
      <el-button type="primary" size="small" @click="showCreateDialog = true">新增执行记录</el-button>
    </div>

    <el-table :data="executions" stripe border size="small" v-loading="loading">
      <el-table-column prop="lab" label="实验室" width="120" />
      <el-table-column prop="equipment" label="设备" width="120" />
      <el-table-column prop="operator" label="操作人员" width="100" />
      <el-table-column prop="start_time" label="开始时间" width="160" />
      <el-table-column prop="end_time" label="结束时间" width="160">
        <template #default="{ row }">
          {{ row.end_time || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="execStatusType(row.status)" size="small">{{ execStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'running'"
            link type="success" size="small"
            @click="completeExecution(row)"
          >完成执行</el-button>
          <el-button
            v-if="row.status === 'running'"
            link type="danger" size="small"
            @click="abortExecution(row)"
          >终止</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增执行记录对话框 -->
    <el-dialog v-model="showCreateDialog" title="新增执行记录" width="450">
      <el-form :model="execForm" label-width="100">
        <el-form-item label="实验室" required>
          <el-input v-model="execForm.lab" placeholder="如 噪音实验室" />
        </el-form-item>
        <el-form-item label="设备" required>
          <el-input v-model="execForm.equipment" placeholder="设备编号/名称" />
        </el-form-item>
        <el-form-item label="操作人员" required>
          <el-input v-model="execForm.operator" placeholder="姓名" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createExecution">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const props = defineProps<{
  testRequestId: number | null
}>()

const emit = defineEmits<{
  (e: 'refresh'): void
}>()

const executions = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const showCreateDialog = ref(false)

const execForm = ref({ lab: '', equipment: '', operator: '' })

const execStatusMap: Record<string, string> = {
  running: '进行中',
  completed: '已完成',
  aborted: '已终止',
}
const execStatusTypeMap: Record<string, string> = {
  running: 'warning',
  completed: 'success',
  aborted: 'danger',
}

function execStatusLabel(s: string) { return execStatusMap[s] || s }
function execStatusType(s: string) { return (execStatusTypeMap[s] || 'info') as any }

async function fetchExecutions() {
  if (!props.testRequestId) return
  loading.value = true
  try {
    const res = await api.get(`/test-requests/${props.testRequestId}/executions`)
    executions.value = res.data
  } finally { loading.value = false }
}

async function createExecution() {
  if (!props.testRequestId) return
  saving.value = true
  try {
    await api.post(`/test-requests/${props.testRequestId}/executions`, execForm.value)
    ElMessage.success('创建成功')
    showCreateDialog.value = false
    execForm.value = { lab: '', equipment: '', operator: '' }
    await fetchExecutions()
    emit('refresh')
  } finally { saving.value = false }
}

async function completeExecution(row: any) {
  try {
    await api.put(`/test-executions/${row.id}/complete`)
    ElMessage.success('已标记完成')
    await fetchExecutions()
    emit('refresh')
  } catch { /* handled by interceptor */ }
}

async function abortExecution(row: any) {
  try {
    await api.put(`/test-executions/${row.id}/abort`)
    ElMessage.success('已终止')
    await fetchExecutions()
    emit('refresh')
  } catch { /* handled by interceptor */ }
}

watch(() => props.testRequestId, (val) => {
  if (val) fetchExecutions()
})
</script>

<style scoped>
.execution-panel { margin-top: 16px; }
.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.panel-title { font-weight: bold; font-size: 14px; }
</style>
