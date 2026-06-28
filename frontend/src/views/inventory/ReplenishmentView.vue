<template>
  <div class="inventory-page">
    <!-- KPI 卡片 -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :span="4" v-for="kpi in kpiCards" :key="kpi.label">
        <el-card shadow="hover" :body-style="{ padding: '16px' }">
          <div class="kpi-label">{{ kpi.label }}</div>
          <div class="kpi-value" :class="{ 'kpi-danger': kpi.danger }">{{ kpi.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选栏 -->
    <div class="page-toolbar">
      <el-button @click="fetchData" :loading="loading">刷新</el-button>
      <el-button type="primary" @click="handleGenerate" :loading="generating">生成补货建议</el-button>
      <el-button type="success" @click="openCreate">新建补货建议</el-button>
      <el-select v-model="filter.status" placeholder="状态" clearable style="width:140px" @change="fetchData">
        <el-option label="全部" value="" />
        <el-option label="待审批" value="pending" />
        <el-option label="已审批" value="approved" />
        <el-option label="已采购" value="purchased" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-input v-model="filter.part_no" placeholder="物料编码" clearable style="width:160px" @clear="fetchData" @keyup.enter="fetchData" />
    </div>

    <!-- 补货建议列表 -->
    <el-table :data="items" border stripe v-loading="loading" style="width:100%">
      <el-table-column prop="part_no" label="物料编码" width="130" />
      <el-table-column prop="part_name" label="物料名称" min-width="150" />
      <el-table-column prop="warehouse_name" label="仓库" width="110" />
      <el-table-column prop="current_stock" label="当前库存" width="90" />
      <el-table-column prop="reorder_point" label="再订货点" width="90" />
      <el-table-column prop="min_stock" label="最低库存" width="90" />
      <el-table-column prop="daily_consumption" label="日均消耗" width="90">
        <template #default="{ row }">{{ row.daily_consumption?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="suggested_qty" label="建议补货量" width="100" />
      <el-table-column prop="unit" label="单位" width="60" />
      <el-table-column prop="unit_cost" label="单价" width="100">
        <template #default="{ row }">¥{{ row.unit_cost?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="总金额" width="110">
        <template #default="{ row }">¥{{ (row.suggested_qty * row.unit_cost)?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'pending'" type="warning" size="small">待审批</el-tag>
          <el-tag v-else-if="row.status === 'approved'" type="success" size="small">已审批</el-tag>
          <el-tag v-else-if="row.status === 'purchased'" type="info" size="small">已采购</el-tag>
          <el-tag v-else-if="row.status === 'cancelled'" type="info" size="small">已取消</el-tag>
          <el-tag v-else type="danger" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="来源" width="70">
        <template #default="{ row }">{{ row.source === 'auto' ? '自动' : '手动' }}</template>
      </el-table-column>
      <el-table-column prop="operator" label="操作人" width="100" />
      <el-table-column label="创建时间" width="160">
        <template #default="{ row }">{{ row.created_at ? new Date(row.created_at).toLocaleString() : '' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending'" type="success" size="small" @click="handleApprove(row)">审批通过</el-button>
          <el-button v-if="row.status === 'pending'" type="danger" size="small" @click="handleCancel(row)">取消</el-button>
          <el-button v-if="row.status === 'approved'" type="primary" size="small" @click="handlePurchased(row)">已采购</el-button>
          <el-button type="warning" size="small" @click="openAdjust(row)">调整</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div style="margin-top:12px;text-align:right">
      <el-pagination
        v-model:current-page="page" :page-size="pageSize" :total="total"
        layout="total, prev, pager, next" @current-change="fetchData"
      />
    </div>

    <!-- 新建补货建议弹窗 -->
    <el-dialog v-model="createVisible" title="新建补货建议" width="520px">
      <el-form ref="createRef" :model="createForm" :rules="createRules" label-width="110px">
        <el-form-item label="仓库" prop="warehouse_id">
          <el-select v-model="createForm.warehouse_id" placeholder="选择仓库" style="width:100%" filterable>
            <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="物料编码" prop="part_no">
          <el-input v-model="createForm.part_no" placeholder="输入物料编码" />
        </el-form-item>
        <el-form-item label="物料名称">
          <el-input v-model="createForm.part_name" placeholder="输入物料名称" />
        </el-form-item>
        <el-form-item label="建议补货量" prop="suggested_qty">
          <el-input-number v-model="createForm.suggested_qty" :min="1" :step="1" :precision="0" style="width:200px" />
        </el-form-item>
        <el-form-item label="单价">
          <el-input-number v-model="createForm.unit_cost" :min="0" :step="0.01" :precision="2" style="width:200px" />
        </el-form-item>
        <el-form-item label="操作人">
          <el-input v-model="createForm.operator" placeholder="输入操作人" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="createForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">确认新建</el-button>
      </template>
    </el-dialog>

    <!-- 调整补货建议弹窗 -->
    <el-dialog v-model="adjustVisible" title="调整补货建议" width="520px">
      <el-form ref="adjustRef" :model="adjustForm" :rules="adjustRules" label-width="110px">
        <el-form-item label="物料编码">
          <el-input v-model="adjustForm.part_no" disabled />
        </el-form-item>
        <el-form-item label="物料名称">
          <el-input v-model="adjustForm.part_name" disabled />
        </el-form-item>
        <el-form-item label="建议补货量" prop="suggested_qty">
          <el-input-number v-model="adjustForm.suggested_qty" :min="1" :step="1" :precision="0" style="width:200px" />
        </el-form-item>
        <el-form-item label="提前期(天)">
          <el-input-number v-model="adjustForm.lead_time_days" :min="0" :step="1" :precision="0" style="width:200px" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="adjustForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAdjust" :loading="adjusting">确认调整</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

interface Warehouse { id: number; name: string; code: string }
interface ReplenishmentItem {
  id: number
  warehouse_id: number
  warehouse_name: string
  part_no: string
  part_name: string | null
  unit: string
  current_stock: number
  reorder_point: number
  min_stock: number
  daily_consumption: number
  suggested_qty: number
  unit_cost: number
  status: string
  source: string
  operator: string | null
  lead_time_days: number | null
  remark: string | null
  created_at: string
}

interface StatsData {
  pending_count: number
  approved_count: number
  purchased_count: number
  total_suggested_qty: number
  total_cost: number
  urgent_count: number
}

const items = ref<ReplenishmentItem[]>([])
const warehouses = ref<Warehouse[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filter = ref({ status: '', part_no: '' })

const stats = ref<StatsData>({
  pending_count: 0,
  approved_count: 0,
  purchased_count: 0,
  total_suggested_qty: 0,
  total_cost: 0,
  urgent_count: 0,
})

const kpiCards = computed(() => [
  { label: '待审批', value: stats.value.pending_count, danger: stats.value.pending_count > 0 },
  { label: '已审批', value: stats.value.approved_count, danger: false },
  { label: '已采购', value: stats.value.purchased_count, danger: false },
  { label: '紧急', value: stats.value.urgent_count, danger: stats.value.urgent_count > 0 },
  { label: '建议补货总量', value: stats.value.total_suggested_qty.toFixed(1), danger: false },
  { label: '预计总金额', value: '¥' + stats.value.total_cost.toFixed(2), danger: false },
])

// Generate replenishment suggestions
const generating = ref(false)
async function handleGenerate() {
  generating.value = true
  try {
    const res = await api.post('/inventory/replenishments/generate')
    const data = res.data
    ElMessage.success(`生成完成：新建 ${data.created} 条，跳过 ${data.skipped} 条`)
    await fetchStats()
    await fetchData()
  } catch {
    ElMessage.error('生成补货建议失败')
  } finally {
    generating.value = false
  }
}

// Create dialog
const createVisible = ref(false)
const creating = ref(false)
const createForm = ref({
  warehouse_id: undefined as number | undefined,
  part_no: '',
  part_name: '',
  suggested_qty: 1,
  unit_cost: 0,
  operator: '',
  remark: '',
})
const createRules = {
  warehouse_id: [{ required: true, message: '请选择仓库', trigger: 'change' }],
  part_no: [{ required: true, message: '请输入物料编码', trigger: 'blur' }],
  suggested_qty: [{ required: true, message: '请输入建议补货量', trigger: 'blur' }],
}

function openCreate() {
  createForm.value = {
    warehouse_id: undefined,
    part_no: '',
    part_name: '',
    suggested_qty: 1,
    unit_cost: 0,
    operator: '',
    remark: '',
  }
  createVisible.value = true
}

async function handleCreate() {
  creating.value = true
  try {
    await api.post('/inventory/replenishments', createForm.value)
    ElMessage.success('新建补货建议成功')
    createVisible.value = false
    await fetchStats()
    await fetchData()
  } catch {
    ElMessage.error('新建失败')
  } finally {
    creating.value = false
  }
}

// Adjust dialog
const adjustVisible = ref(false)
const adjusting = ref(false)
const adjustForm = ref({
  id: 0,
  part_no: '',
  part_name: '',
  suggested_qty: 1,
  lead_time_days: 0,
  remark: '',
})
const adjustRules = {
  suggested_qty: [{ required: true, message: '请输入建议补货量', trigger: 'blur' }],
}

function openAdjust(row: ReplenishmentItem) {
  adjustForm.value = {
    id: row.id,
    part_no: row.part_no,
    part_name: row.part_name || '',
    suggested_qty: row.suggested_qty,
    lead_time_days: row.lead_time_days || 0,
    remark: row.remark || '',
  }
  adjustVisible.value = true
}

async function handleAdjust() {
  adjusting.value = true
  try {
    const { id, suggested_qty, lead_time_days, remark } = adjustForm.value
    await api.put(`/inventory/replenishments/${id}`, { suggested_qty, lead_time_days, remark })
    ElMessage.success('调整成功')
    adjustVisible.value = false
    await fetchStats()
    await fetchData()
  } catch {
    ElMessage.error('调整失败')
  } finally {
    adjusting.value = false
  }
}

// Status actions
async function handleApprove(row: ReplenishmentItem) {
  try {
    await ElMessageBox.confirm('确认审批通过该补货建议？', '确认')
    await api.patch(`/inventory/replenishments/${row.id}/status?status=approved`)
    ElMessage.success('已审批通过')
    await fetchStats()
    await fetchData()
  } catch {
    // cancelled or error
  }
}

async function handleCancel(row: ReplenishmentItem) {
  try {
    await ElMessageBox.confirm('确认取消该补货建议？', '确认')
    await api.patch(`/inventory/replenishments/${row.id}/status?status=cancelled`)
    ElMessage.success('已取消')
    await fetchStats()
    await fetchData()
  } catch {
    // cancelled or error
  }
}

async function handlePurchased(row: ReplenishmentItem) {
  try {
    await ElMessageBox.confirm('确认该补货建议已采购？', '确认')
    await api.patch(`/inventory/replenishments/${row.id}/status?status=purchased`)
    ElMessage.success('已标记为已采购')
    await fetchStats()
    await fetchData()
  } catch {
    // cancelled or error
  }
}

// Data fetching
async function fetchStats() {
  try {
    const res = await api.get('/inventory/replenishments/stats')
    stats.value = res.data
  } catch {
    // ignore stats error
  }
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (filter.value.status) params.status = filter.value.status
    if (filter.value.part_no) params.part_no = filter.value.part_no
    const res = await api.get('/inventory/replenishments', { params })
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    ElMessage.error('获取补货建议失败')
  } finally {
    loading.value = false
  }
}

async function fetchWarehouses() {
  try {
    const res = await api.get('/inventory/warehouses')
    warehouses.value = res.data
  } catch {
    // ignore
  }
}

onMounted(async () => {
  await fetchStats()
  await fetchWarehouses()
  await fetchData()
})
</script>

<style scoped>
.kpi-row { margin-bottom: 16px; }
.kpi-label { font-size: 13px; color: #909399; margin-bottom: 6px; }
.kpi-value { font-size: 22px; font-weight: 700; color: #303133; }
.kpi-danger .kpi-value { color: #f56c6c; }
.page-toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
</style>
