<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>认证样机管理</span>
          <el-button type="primary" @click="openDialog()">新建认证样机</el-button>
        </div>
      </template>

      <el-table :data="items" stripe border v-loading="loading" max-height="550">
        <el-table-column prop="sample_no" label="样机编号" width="180" />
        <el-table-column label="关联Prototype" width="120">
          <template #default="{ row }">{{ row.prototype_id }}</template>
        </el-table-column>
        <el-table-column label="认证项目" width="180">
          <template #default="{ row }">{{ row.cert_project_id }}</template>
        </el-table-column>
        <el-table-column prop="cert_type" label="认证类型" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="certTagType(row.cert_type)">{{ row.cert_type }}</el-tag>
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
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑认证样机' : '新建认证样机'" width="550">
      <el-form :model="form" label-width="120">
        <el-form-item label="认证项目ID" required>
          <el-input-number v-model="form.cert_project_id" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="Prototype" required>
          <el-select v-model="form.prototype_id" filterable placeholder="必须选择Prototype" style="width: 100%">
            <el-option v-for="p in prototypes" :key="p.id" :label="`${p.proto_no || '#'+p.id} (${p.version || ''})`" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="认证类型">
          <el-select v-model="form.cert_type" style="width: 100%">
            <el-option label="CE" value="CE" />
            <el-option label="CB" value="CB" />
            <el-option label="UL" value="UL" />
            <el-option label="SAA" value="SAA" />
          </el-select>
        </el-form-item>
        <el-form-item label="提交日期">
          <el-date-picker v-model="form.submitted_date" type="date" style="width: 100%" />
        </el-form-item>
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

const items = ref<any[]>([])
const prototypes = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)

const statusMap: Record<string, string> = { pending: '待提交', preparing: '准备中', submitted: '已提交', testing: '测试中', passed: '通过', failed: '失败' }
const statusTypeMap: Record<string, string> = { pending: 'info', preparing: 'warning', submitted: 'primary', testing: 'warning', passed: 'success', failed: 'danger' }
function statusLabel(s: string) { return statusMap[s] || s }
function statusType(s: string) { return (statusTypeMap[s] || 'info') as any }

const form = ref<any>({ cert_project_id: 1, prototype_id: null, cert_type: 'CE', submitted_date: null, remark: '' })

function certTagType(t: string) { const map: Record<string, string> = { CE: 'danger', CB: 'warning', UL: 'primary', SAA: 'success' }; return map[t] || 'info' }
function formatDate(d: string) { if (!d) return ''; return d.slice(0, 10) }

async function fetchData() {
  loading.value = true
  try {
    const res = await api.get('/s2/certification-samples')
    items.value = res.data || []
  } finally { loading.value = false }
}

async function fetchPrototypes() {
  try {
    const res = await api.get('/api/prototypes')
    prototypes.value = res.data || []
  } catch { /* ignore */ }
}

function openDialog(row?: any) {
  if (row) {
    editingId.value = row.id
    form.value = { cert_project_id: row.cert_project_id, prototype_id: row.prototype_id, cert_type: row.cert_type, submitted_date: row.submitted_date || null, remark: row.remark || '' }
  } else {
    editingId.value = null
    form.value = { cert_project_id: 1, prototype_id: null, cert_type: 'CE', submitted_date: null, remark: '' }
  }
  dialogVisible.value = true
}

async function save() {
  saving.value = true
  try {
    if (editingId.value) {
      await api.put(`/s2/certification-samples/${editingId.value}`, form.value)
      ElMessage.success('更新成功')
    } else {
      await api.post('/s2/certification-samples', form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally { saving.value = false }
}

onMounted(() => { fetchData(); fetchPrototypes() })
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
