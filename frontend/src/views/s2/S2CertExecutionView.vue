<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>认证执行记录</span>
          <el-button type="primary" @click="openDialog()">新建执行记录</el-button>
        </div>
      </template>

      <el-table :data="items" stripe border v-loading="loading" max-height="550">
        <el-table-column prop="id" label="执行ID" width="80" />
        <el-table-column prop="cert_sample_id" label="认证样机ID" width="120" />
        <el-table-column prop="lab" label="实验室" width="150" />
        <el-table-column prop="agency" label="代理机构" width="150" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="开始日期" width="120">
          <template #default="{ row }">{{ row.start_date?.slice(0, 10) }}</template>
        </el-table-column>
        <el-table-column label="结束日期" width="120">
          <template #default="{ row }">{{ row.end_date?.slice(0, 10) }}</template>
        </el-table-column>
        <el-table-column prop="result_summary" label="结果摘要" min-width="200" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑执行记录' : '新建执行记录'" width="550">
      <el-form :model="form" label-width="110">
        <el-form-item label="认证样机ID" required>
          <el-input-number v-model="form.cert_sample_id" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="实验室">
          <el-input v-model="form.lab" placeholder="实验室名称" />
        </el-form-item>
        <el-form-item label="代理机构">
          <el-input v-model="form.agency" placeholder="代理机构名称" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="开始日期"><el-date-picker v-model="form.start_date" type="date" style="width: 100%" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束日期"><el-date-picker v-model="form.end_date" type="date" style="width: 100%" /></el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="结果摘要">
          <el-input v-model="form.result_summary" type="textarea" :rows="3" />
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

const statusMap: Record<string, string> = { pending: '待开始', in_progress: '进行中', completed: '已完成', failed: '失败' }
const statusTypeMap: Record<string, string> = { pending: 'info', in_progress: 'primary', completed: 'success', failed: 'danger' }
function statusLabel(s: string) { return statusMap[s] || s }
function statusType(s: string) { return (statusTypeMap[s] || 'info') as string }

const form = ref<Record<string, unknown>>({ cert_sample_id: 1, lab: '', agency: '', start_date: null, end_date: null, result_summary: '' })

async function fetchData() {
  loading.value = true
  try {
    const res = await api.get('/s2/certification-executions')
    items.value = res.data || []
  } finally { loading.value = false }
}

function openDialog(row?: Record<string, unknown>) {
  if (row) {
    editingId.value = Number(row.id) ?? null
    form.value = { cert_sample_id: row.cert_sample_id, lab: row.lab || '', agency: row.agency || '', start_date: row.start_date || null, end_date: row.end_date || null, result_summary: row.result_summary || '' }
  } else {
    editingId.value = null
    form.value = { cert_sample_id: 1, lab: '', agency: '', start_date: null, end_date: null, result_summary: '' }
  }
  dialogVisible.value = true
}

async function save() {
  saving.value = true
  try {
    if (editingId.value) {
      await api.patch(`/s2/certification-executions/${editingId.value}`, form.value)
      ElMessage.success('更新成功')
    } else {
      await api.post('/s2/certification-executions', form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally { saving.value = false }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
