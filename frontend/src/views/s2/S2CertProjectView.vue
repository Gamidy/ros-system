<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>认证项目列表</span>
          <el-button type="primary" @click="openDialog()">新建认证项目</el-button>
        </div>
      </template>

      <el-row :gutter="12" style="margin-bottom: 16px">
        <el-col :span="6">
          <el-input v-model="filterProject" placeholder="按项目ID筛选" clearable @change="fetchData" />
        </el-col>
        <el-col :span="6">
          <el-select v-model="filterStatus" placeholder="状态筛选" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option v-for="(label, key) in statusMap" :key="key" :label="label" :value="key" />
          </el-select>
        </el-col>
      </el-row>

      <el-table :data="items" stripe border v-loading="loading" max-height="550">
        <el-table-column prop="code" label="项目编码" width="180" />
        <el-table-column prop="name" label="名称" min-width="200" />
        <el-table-column label="目标市场" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.target_market_id }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="认证类型" width="200">
          <template #default="{ row }">
            <el-tag v-for="t in parseCertTypes(row.cert_types)" :key="t" :type="certTagType(t)" size="small" style="margin-right: 4px">{{ t }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="'创建日期'" width="120">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="$router.push(`/s2/projects/${row.id}`)">详情</el-button>
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑认证项目' : '新建认证项目'" width="600">
      <el-form :model="form" label-width="120">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="认证项目名称" />
        </el-form-item>
        <el-form-item label="关联项目ID" required>
          <el-input-number v-model="form.project_id" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="目标市场ID" required>
          <el-input-number v-model="form.target_market_id" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="认证类型">
          <el-select v-model="form.cert_types_arr" multiple placeholder="选择认证类型" style="width: 100%">
            <el-option label="CE" value="CE" />
            <el-option label="CB" value="CB" />
            <el-option label="UL" value="UL" />
            <el-option label="SAA" value="SAA" />
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="计划开始">
              <el-date-picker v-model="form.planned_start_date" type="date" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计划结束">
              <el-date-picker v-model="form.planned_end_date" type="date" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" />
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
const filterProject = ref('')
const filterStatus = ref('')

const statusMap: Record<string, string> = {
  planning: '计划中', in_progress: '进行中', completed: '已完成',
  failed: '失败', on_hold: '暂停', cancelled: '已取消',
}
const statusTypeMap: Record<string, string> = {
  planning: 'info', in_progress: 'primary', completed: 'success',
  failed: 'danger', on_hold: 'warning', cancelled: 'info',
}
function statusLabel(s: string) { return statusMap[s] || s }
function statusType(s: string) { return (statusTypeMap[s] || 'info') as string }

const form = ref<Record<string, unknown>>({
  name: '', project_id: 1, target_market_id: 1,
  cert_types_arr: [], planned_start_date: null, planned_end_date: null, remark: '',
})

function parseCertTypes(certTypes: string | null): string[] {
  if (!certTypes) return []
  try { return JSON.parse(certTypes) } catch { return [certTypes] }
}

function certTagType(t: string) {
  const map: Record<string, string> = { CE: 'danger', CB: 'warning', UL: 'primary', SAA: 'success' }
  return map[t] || 'info'
}

function formatDate(d: string) {
  if (!d) return ''
  return d.slice(0, 10)
}

async function fetchData() {
  loading.value = true
  try {
    const params: string[] = []
    if (filterProject.value) params.push(`project_id=${filterProject.value}`)
    if (filterStatus.value) params.push(`status=${filterStatus.value}`)
    const url = '/s2/certification-projects' + (params.length ? '?' + params.join('&') : '')
    const res = await api.get(url)
    items.value = res.data || []
  } finally { loading.value = false }
}

function openDialog(row?: Record<string, unknown>) {
  if (row) {
    editingId.value = row.id
    form.value = {
      name: row.name || '',
      project_id: row.project_id,
      target_market_id: row.target_market_id,
      cert_types_arr: parseCertTypes(row.cert_types),
      planned_start_date: row.planned_start_date || null,
      planned_end_date: row.planned_end_date || null,
      remark: row.remark || '',
    }
  } else {
    editingId.value = null
    form.value = { name: '', project_id: 1, target_market_id: 1, cert_types_arr: [], planned_start_date: null, planned_end_date: null, remark: '' }
  }
  dialogVisible.value = true
}

async function save() {
  saving.value = true
  try {
    const payload = {
      ...form.value,
      cert_types: JSON.stringify(form.value.cert_types_arr),
    }
    delete payload.cert_types_arr
    if (editingId.value) {
      await api.put(`/s2/certification-projects/${editingId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      await api.post('/s2/certification-projects', payload)
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
