<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>验证需求管理</span>
          <div>
            <el-button type="warning" @click="generateFromPlan" :loading="generating">从 ProductPlan 生成</el-button>
            <el-button type="primary" @click="openDialog()">新建验证需求</el-button>
          </div>
        </div>
      </template>

      <!-- 筛选栏 -->
      <el-row :gutter="12" style="margin-bottom: 16px">
        <el-col :span="6">
          <el-select v-model="filterCategory" placeholder="分类筛选" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option v-for="(label, key) in categoryMap" :key="key" :label="label" :value="key" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filterSource" placeholder="来源筛选" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option v-for="(label, key) in sourceMap" :key="key" :label="label" :value="key" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filterStatus" placeholder="状态筛选" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="待验证" value="pending" />
            <el-option label="已通过" value="verified" />
            <el-option label="未通过" value="failed" />
            <el-option label="豁免" value="waived" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-input v-model="searchText" placeholder="搜索标题或VR编码" clearable @change="fetchData" />
        </el-col>
      </el-row>

      <el-table :data="items" stripe border v-loading="loading" max-height="550">
        <el-table-column prop="vr_code" label="VR编码" width="150" />
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column label="分类" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ categoryMap[row.category] || row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ sourceMap[row.source_type] || row.source_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_value" label="目标值" width="120">
          <template #default="{ row }">
            {{ row.target_value }}{{ row.unit || '' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
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

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑验证需求' : '新建验证需求'" width="650">
      <el-form :model="form" label-width="110">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="验证需求标题" />
        </el-form-item>
        <el-form-item label="分类" required>
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="(label, key) in categoryMap" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="目标值">
              <el-input v-model="form.target_value" placeholder="如 3.2" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="单位">
              <el-input v-model="form.unit" placeholder="如 kW, dB" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="来源类型" required>
          <el-select v-model="form.source_type" style="width: 100%">
            <el-option v-for="(label, key) in sourceMap" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源ID">
          <el-input v-model="form.source_id" placeholder="关联来源记录ID" />
        </el-form-item>
        <el-form-item label="Gate编号">
          <el-select v-model="form.gate_code" placeholder="选择Gate" clearable style="width: 100%">
            <el-option label="M4" value="M4" />
            <el-option label="M5" value="M5" />
            <el-option label="M6" value="M6" />
            <el-option label="M7" value="M7" />
            <el-option label="M8" value="M8" />
            <el-option label="M9" value="M9" />
          </el-select>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

const items = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const generating = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)

const filterCategory = ref('')
const filterSource = ref('')
const filterStatus = ref('')
const searchText = ref('')

const form = ref<any>({
  title: '', category: '', target_value: '', unit: '',
  source_type: '', source_id: '', gate_code: '', remark: ''
})

const categoryMap: Record<string, string> = {
  performance: '性能测试',
  energy: '能效测试',
  noise: '噪音',
  condensation: '凝露',
  damp_heat: '潮态',
  high_temp_cool: '高温制冷',
  low_temp_heat: '低温制热',
  frost_defrost: '冻结融霜',
  long_run: '长时间运行',
  elec_safety_pre: '电气安全预验证',
}

const sourceMap: Record<string, string> = {
  product_plan: '产品策划',
  customer: '客户要求',
  standard: '标准要求',
  certification: '认证要求',
  gate: 'Gate决策',
}

const statusMap: Record<string, string> = {
  pending: '待验证',
  verified: '已通过',
  failed: '未通过',
  waived: '豁免',
}

const statusTypeMap: Record<string, string> = {
  pending: 'info',
  verified: 'success',
  failed: 'danger',
  waived: 'warning',
}

function statusLabel(s: string) { return statusMap[s] || s }
function statusType(s: string) { return (statusTypeMap[s] || 'info') as any }

async function fetchData() {
  loading.value = true
  try {
    const params: string[] = []
    if (filterCategory.value) params.push(`category=${filterCategory.value}`)
    if (filterSource.value) params.push(`source_type=${filterSource.value}`)
    if (filterStatus.value) params.push(`status=${filterStatus.value}`)
    if (searchText.value) params.push(`search=${encodeURIComponent(searchText.value)}`)
    const url = '/verification-requirements' + (params.length ? '?' + params.join('&') : '')
    const res = await api.get(url)
    items.value = res.data
  } finally { loading.value = false }
}

function openDialog(row?: any) {
  if (row) {
    editingId.value = row.id
    form.value = {
      title: row.title || '',
      category: row.category || '',
      target_value: row.target_value || '',
      unit: row.unit || '',
      source_type: row.source_type || '',
      source_id: row.source_id || '',
      gate_code: row.gate_code || '',
      remark: row.remark || '',
    }
  } else {
    editingId.value = null
    form.value = { title: '', category: '', target_value: '', unit: '', source_type: '', source_id: '', gate_code: '', remark: '' }
  }
  dialogVisible.value = true
}

async function save() {
  saving.value = true
  try {
    if (editingId.value) {
      await api.put(`/verification-requirements/${editingId.value}`, form.value)
      ElMessage.success('更新成功')
    } else {
      await api.post('/verification-requirements', form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally { saving.value = false }
}

async function removeItem(row: any) {
  try {
    await ElMessageBox.confirm('确定删除此验证需求？', '确认', { type: 'warning' })
    await api.delete(`/verification-requirements/${row.id}`)
    ElMessage.success('删除成功')
    await fetchData()
  } catch { /* cancelled */ }
}

async function generateFromPlan() {
  generating.value = true
  try {
    await api.post('/verification-requirements/generate-from-plan')
    ElMessage.success('已从 ProductPlan 生成验证需求')
    await fetchData()
  } finally { generating.value = false }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
