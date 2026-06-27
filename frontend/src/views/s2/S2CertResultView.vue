<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>认证结果管理</span>
          <el-button type="primary" @click="openDialog()">新建认证结果</el-button>
        </div>
      </template>

      <el-table :data="items" stripe border v-loading="loading" max-height="550">
        <el-table-column prop="id" label="结果ID" width="80" />
        <el-table-column prop="cert_execution_id" label="执行ID" width="100" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="summary" label="结果摘要" min-width="250" />
        <el-table-column label="结果日期" width="120">
          <template #default="{ row }">{{ row.result_date?.slice(0, 10) }}</template>
        </el-table-column>
        <el-table-column :label="'创建日期'" width="120">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button link type="success" size="small" @click="transitionStatus(row, 'submitted')" v-if="row.status==='draft'">提交</el-button>
            <el-button link type="warning" size="small" @click="transitionStatus(row, 'testing')" v-if="row.status==='submitted'">开始测试</el-button>
            <el-button link type="success" size="small" @click="transitionStatus(row, 'passed')" v-if="row.status==='testing'">通过</el-button>
            <el-button link type="danger" size="small" @click="transitionStatus(row, 'failed')" v-if="row.status==='testing'">失败</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑认证结果' : '新建认证结果'" width="550">
      <el-form :model="form" label-width="110">
        <el-form-item label="执行ID" required>
          <el-input-number v-model="form.cert_execution_id" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结果日期">
          <el-date-picker v-model="form.result_date" type="date" style="width: 100%" />
        </el-form-item>
        <el-form-item label="摘要">
          <el-input v-model="form.summary" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="附件JSON">
          <el-input v-model="form.attachments" placeholder='{"files":[]}' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const items = ref<Record<string, unknown>[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)

const statusMap: Record<string, string> = { draft: '草稿', submitted: '已提交', testing: '测试中', passed: '通过', failed: '失败', expired: '过期' }
const statusTypeMap: Record<string, string> = { draft: 'info', submitted: 'primary', testing: 'warning', passed: 'success', failed: 'danger', expired: 'info' }
function statusLabel(s: string) { return statusMap[s] || s }
function statusType(s: string) { return (statusTypeMap[s] || 'info') as string }

const form = ref<Record<string, unknown>>({ cert_execution_id: 1, result_date: null, summary: '', attachments: '' })

function formatDate(d: string) { if (!d) return ''; return d.slice(0, 10) }

async function fetchData() {
  loading.value = true
  try {
    const res = await api.get('/s2/certification-results')
    items.value = res.data || []
  } finally { loading.value = false }
}

function openDialog(row?: Record<string, unknown>) {
  if (row) {
    editingId.value = row.id
    form.value = { cert_execution_id: row.cert_execution_id, result_date: row.result_date || null, summary: row.summary || '', attachments: row.attachments || '' }
  } else {
    editingId.value = null
    form.value = { cert_execution_id: 1, result_date: null, summary: '', attachments: '' }
  }
  dialogVisible.value = true
}

async function save() {
  saving.value = true
  try {
    if (editingId.value) {
      await api.patch(`/s2/certification-results/${editingId.value}`, form.value)
      ElMessage.success('更新成功')
    } else {
      await api.post('/s2/certification-results', form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally { saving.value = false }
}

async function transitionStatus(row: Record<string, unknown>, newStatus: string) {
  try {
    await api.patch(`/s2/certification-results/${row.id}/status`, { status: newStatus })
    ElMessage.success(`状态已更新为: ${statusLabel(newStatus)}`)
    await fetchData()
  } catch { /* error already shown by interceptor */ }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
