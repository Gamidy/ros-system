<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>认证门禁规则配置</span>
        </div>
      </template>

      <el-row :gutter="12" style="margin-bottom: 16px">
        <el-col :span="6">
          <el-select v-model="filterGate" placeholder="门禁编号" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option v-for="g in ['M4','M5','M6','M7','M8','M9']" :key="g" :label="g" :value="g" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filterCertType" placeholder="认证类型" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="CE" value="CE" />
            <el-option label="CB" value="CB" />
            <el-option label="UL" value="UL" />
            <el-option label="SAA" value="SAA" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-button type="primary" @click="openDialog()">新建规则</el-button>
        </el-col>
      </el-row>

      <el-table :data="items" stripe border v-loading="loading" max-height="550">
        <el-table-column prop="gate_code" label="门禁编号" width="100" />
        <el-table-column prop="name" label="规则名称" min-width="160" />
        <el-table-column prop="cert_type" label="认证类型" width="100">
          <template #default="{ row }"><el-tag size="small" :type="certTagType(row.cert_type)">{{ row.cert_type }}</el-tag></template>
        </el-table-column>
        <el-table-column label="目标市场" width="120">
          <template #default="{ row }">{{ row.target_market_id || '通配' }}</template>
        </el-table-column>
        <el-table-column label="是否强制" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_required ? 'danger' : 'info'" size="small">{{ row.is_required ? '强制' : '可选' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="自动阻塞" width="100">
          <template #default="{ row }">
            <el-tag :type="row.auto_block ? 'warning' : 'info'" size="small">{{ row.auto_block ? '开启' : '关闭' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="80">
          <template #default="{ row }">{{ row.priority }}</template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status === 'active' ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="removeItem(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑门禁规则' : '新建门禁规则'" width="550">
      <el-form :model="form" label-width="110">
        <el-form-item label="规则名称" required>
          <el-input v-model="form.name" placeholder="规则名称" />
        </el-form-item>
        <el-form-item label="门禁编号" required>
          <el-select v-model="form.gate_code" style="width: 100%">
            <el-option v-for="g in ['M4','M5','M6','M7','M8','M9']" :key="g" :label="g" :value="g" />
          </el-select>
        </el-form-item>
        <el-form-item label="认证类型" required>
          <el-select v-model="form.cert_type" style="width: 100%">
            <el-option label="CE" value="CE" />
            <el-option label="CB" value="CB" />
            <el-option label="UL" value="UL" />
            <el-option label="SAA" value="SAA" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标市场ID">
          <el-input-number v-model="form.target_market_id" :min="0" style="width: 100%" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="是否强制">
              <el-switch v-model="form.is_required" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="自动阻塞">
              <el-switch v-model="form.auto_block" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="优先级">
          <el-input-number v-model="form.priority" :min="1" :max="999" style="width: 100%" />
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
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

const items = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const filterGate = ref('')
const filterCertType = ref('')

const form = ref<any>({ name: '', gate_code: 'M6', cert_type: 'CE', target_market_id: 0, is_required: true, auto_block: false, priority: 100 })

function certTagType(t: string) { const map: Record<string, string> = { CE: 'danger', CB: 'warning', UL: 'primary', SAA: 'success' }; return map[t] || 'info' }

async function fetchData() {
  loading.value = true
  try {
    const params: string[] = []
    if (filterGate.value) params.push(`gate_code=${filterGate.value}`)
    if (filterCertType.value) params.push(`cert_type=${filterCertType.value}`)
    const url = '/s2/gate-rules' + (params.length ? '?' + params.join('&') : '')
    const res = await api.get(url)
    items.value = res.data || []
  } finally { loading.value = false }
}

function openDialog(row?: any) {
  if (row) {
    editingId.value = row.id
    form.value = { name: row.name, gate_code: row.gate_code, cert_type: row.cert_type, target_market_id: row.target_market_id || 0, is_required: row.is_required, auto_block: row.auto_block, priority: row.priority }
  } else {
    editingId.value = null
    form.value = { name: '', gate_code: 'M6', cert_type: 'CE', target_market_id: 0, is_required: true, auto_block: false, priority: 100 }
  }
  dialogVisible.value = true
}

async function save() {
  saving.value = true
  try {
    const payload = { ...form.value }
    if (!payload.target_market_id) delete payload.target_market_id
    if (editingId.value) {
      await api.put(`/s2/gate-rules/${editingId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      await api.post('/s2/gate-rules', payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally { saving.value = false }
}

async function removeItem(row: any) {
  try {
    await ElMessageBox.confirm('确定删除此门禁规则？', '确认', { type: 'warning' })
    await api.delete(`/s2/gate-rules/${row.id}`)
    ElMessage.success('删除成功')
    await fetchData()
  } catch { /* cancelled */ }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
