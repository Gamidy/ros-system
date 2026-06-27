<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>变更影响规则管理</span>
          <el-button type="primary" @click="openCreateDialog">新建规则</el-button>
        </div>
      </template>

      <!-- 筛选栏 -->
      <el-row :gutter="12" style="margin-bottom: 16px">
        <el-col :span="5">
          <el-select v-model="filter.trigger_type" placeholder="触发类型" clearable style="width:100%" @change="fetchData(1)">
            <el-option label="全部" value="" />
            <el-option label="ECR变更" value="ecr_change" />
            <el-option label="ECO变更" value="eco_change" />
            <el-option label="样机变更" value="prototype_change" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filter.impact_level" placeholder="影响级别" clearable style="width:100%" @change="fetchData(1)">
            <el-option label="全部" value="" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-input v-model="filter.name" placeholder="规则名称搜索" clearable @change="fetchData(1)" />
        </el-col>
      </el-row>

      <!-- 表格 -->
      <el-table :data="list" stripe border v-loading="loading" style="width:100%">
        <el-table-column prop="name" label="规则名称" min-width="160" show-overflow-tooltip />
        <el-table-column label="触发类型" width="120">
          <template #default="{ row }">
            <el-tag :type="triggerTagType(row.trigger_type)" size="small">
              {{ triggerLabel(row.trigger_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="影响级别" width="100">
          <template #default="{ row }">
            <el-tag :type="levelTagType(row.impact_level)" size="small">
              {{ levelLabel(row.impact_level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="目标证书类型" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="ct in parseCertTypes(row.affected_cert_types)" :key="ct"
              style="margin-right:4px;margin-bottom:2px" size="small">
              {{ ct }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="启用状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="row.is_active"
              @change="(val: boolean) => handleToggleActive(row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div style="display:flex;justify-content:flex-end;margin-top:16px">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData(1)"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- 创建 / 编辑 Dialog -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑规则' : '新建规则'" width="580" :close-on-click-modal="false" destroy-on-close>
      <el-form :model="form" label-width="110" :rules="rules" ref="formRef">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="form.name" placeholder="如: 压缩机变更→影响CE/CB" />
        </el-form-item>
        <el-form-item label="触发类型" prop="trigger_type">
          <el-select v-model="form.trigger_type" placeholder="选择触发类型" style="width:100%">
            <el-option label="ECR变更" value="ecr_change" />
            <el-option label="ECO变更" value="eco_change" />
            <el-option label="样机变更" value="prototype_change" />
          </el-select>
        </el-form-item>
        <el-form-item label="触发值" prop="trigger_value">
          <el-input v-model="form.trigger_value" placeholder="如: compressor / safety_part" />
        </el-form-item>
        <el-form-item label="影响级别" prop="impact_level">
          <el-select v-model="form.impact_level" placeholder="选择影响级别" style="width:100%">
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标证书类型" prop="cert_types">
          <el-select v-model="form.cert_types" multiple placeholder="选择目标证书类型" style="width:100%">
            <el-option label="CE" value="CE" />
            <el-option label="CB" value="CB" />
            <el-option label="CCC" value="CCC" />
            <el-option label="UL" value="UL" />
            <el-option label="FCC" value="FCC" />
            <el-option label="EAC" value="EAC" />
            <el-option label="KC" value="KC" />
            <el-option label="PSE" value="PSE" />
            <el-option label="BSMI" value="BSMI" />
            <el-option label="SAA" value="SAA" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

// ── 类型 ──
interface RuleItem {
  id: number
  name: string
  description?: string | null
  trigger_type: string
  trigger_value: string
  affected_cert_types: string
  impact_level: string
  is_active: boolean
  org_id?: number | null
  created_at: string
  updated_at: string
}

interface RuleForm {
  name: string
  trigger_type: string
  trigger_value: string
  impact_level: string
  cert_types: string[]
  description: string
}

// ── 映射 ──
const triggerMap: Record<string, string> = {
  ecr_change: 'ECR变更',
  eco_change: 'ECO变更',
  prototype_change: '样机变更',
  part_category: '部件类别',
  material_type: '材料类型',
  cdf_type: 'CDF类型',
  market_change: '市场变更',
}

const triggerTypeMap: Record<string, string> = {
  ecr_change: 'warning',
  eco_change: '',
  prototype_change: 'info',
  part_category: 'warning',
  material_type: '',
  cdf_type: 'info',
  market_change: 'danger',
}

const levelMap: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
  critical: '严重',
  major: '较大',
  minor: '轻微',
  none: '无影响',
}

const levelTypeMap: Record<string, string> = {
  high: 'danger',
  medium: 'warning',
  low: 'info',
  critical: 'danger',
  major: 'warning',
  minor: 'info',
  none: 'success',
}

function triggerLabel(s: string) { return triggerMap[s] || s }
function triggerTagType(s: string) { return triggerTypeMap[s] || 'info' }
function levelLabel(s: string) { return levelMap[s] || s }
function levelTagType(s: string) { return levelTypeMap[s] || 'info' }

function parseCertTypes(val: string): string[] {
  try { return JSON.parse(val) }
  catch { return val ? [val] : [] }
}

// ── 数据 ──
const loading = ref(false)
const list = ref<RuleItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filter = reactive({ trigger_type: '', impact_level: '', name: '' })

async function fetchData(p?: number) {
  if (p) page.value = p
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (filter.trigger_type) params.trigger_type = filter.trigger_type
    if (filter.impact_level) params.impact_level = filter.impact_level
    if (filter.name) params.name = filter.name
    const { data } = await api.get('/api/s2/change-impact/rules', { params })
    list.value = data.items || []
    total.value = data.total || 0
  } catch {
    ElMessage.error('加载规则列表失败')
  } finally {
    loading.value = false
  }
}

// ── 创建 / 编辑 ──
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref<any>(null)
const form = reactive<RuleForm>({
  name: '',
  trigger_type: '',
  trigger_value: '',
  impact_level: '',
  cert_types: [],
  description: '',
})

const rules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  trigger_type: [{ required: true, message: '请选择触发类型', trigger: 'change' }],
  trigger_value: [{ required: true, message: '请输入触发值', trigger: 'blur' }],
  impact_level: [{ required: true, message: '请选择影响级别', trigger: 'change' }],
  cert_types: [{ required: true, message: '请选择至少一个目标证书类型', trigger: 'change' }],
}

function openCreateDialog() {
  editingId.value = null
  form.name = ''
  form.trigger_type = ''
  form.trigger_value = ''
  form.impact_level = ''
  form.cert_types = []
  form.description = ''
  dialogVisible.value = true
}

function openEditDialog(row: RuleItem) {
  editingId.value = row.id
  form.name = row.name
  form.trigger_type = row.trigger_type
  form.trigger_value = row.trigger_value
  form.impact_level = row.impact_level
  form.cert_types = parseCertTypes(row.affected_cert_types)
  form.description = row.description || ''
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload: Record<string, any> = {
      name: form.name,
      trigger_type: form.trigger_type,
      trigger_value: form.trigger_value,
      impact_level: form.impact_level,
      affected_cert_types: JSON.stringify(form.cert_types),
      description: form.description || undefined,
    }
    if (editingId.value) {
      await api.put(`/api/s2/change-impact/rules/${editingId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      await api.post('/api/s2/change-impact/rules', payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally {
    saving.value = false
  }
}

// ── 启用/禁用 ──
async function handleToggleActive(row: RuleItem, val: boolean) {
  try {
    await api.put(`/api/s2/change-impact/rules/${row.id}`, { is_active: val })
    row.is_active = val
    ElMessage.success(val ? '已启用' : '已禁用')
  } catch {
    // 错误已由 axios 拦截器处理
  }
}

// ── 删除 ──
async function handleDelete(row: RuleItem) {
  await ElMessageBox.confirm(`确定删除规则「${row.name}」吗？删除后不可恢复。`, '确认删除', { type: 'warning' })
  await api.delete(`/api/s2/change-impact/rules/${row.id}`)
  ElMessage.success('删除成功')
  await fetchData()
}

onMounted(() => fetchData())
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
