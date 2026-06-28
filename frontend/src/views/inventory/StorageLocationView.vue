<template>
  <div class="inventory-page">
    <!-- KPI Cards -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :span="4" v-for="kpi in kpiCards" :key="kpi.label">
        <el-card shadow="hover" :body-style="{ padding: '16px' }">
          <div class="kpi-label">{{ kpi.label }}</div>
          <div class="kpi-value" :class="{ 'kpi-danger': kpi.danger }">{{ kpi.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Toolbar -->
    <div class="page-toolbar">
      <el-button @click="fetchData" :loading="loading">刷新</el-button>
      <el-button type="primary" @click="openCreate">新建库位</el-button>
      <el-select v-model="filter.warehouse_id" placeholder="仓库" clearable style="width:150px" @change="fetchData">
        <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
      </el-select>
      <el-input v-model="filter.zone" placeholder="区域" clearable style="width:120px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-select v-model="filter.location_type" placeholder="类型" clearable style="width:120px" @change="fetchData">
        <el-option label="全部" value="" />
        <el-option label="存储" value="storage" />
        <el-option label="收货" value="receiving" />
        <el-option label="拣货" value="picking" />
        <el-option label="退货" value="return" />
        <el-option label="待检" value="quarantine" />
      </el-select>
      <el-select v-model="filter.status" placeholder="状态" clearable style="width:120px" @change="fetchData">
        <el-option label="全部" value="" />
        <el-option label="可用" value="active" />
        <el-option label="已满" value="full" />
        <el-option label="维护中" value="blocked" />
        <el-option label="停用" value="inactive" />
      </el-select>
      <el-input v-model="filter.keyword" placeholder="搜索编码/名称" clearable style="width:180px" @clear="fetchData" @keyup.enter="fetchData" />
    </div>

    <!-- Table -->
    <el-table :data="items" border stripe v-loading="loading" style="width:100%">
      <el-table-column prop="code" label="库位编码" width="130" />
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column prop="warehouse_name" label="所属仓库" width="120" />
      <el-table-column prop="zone" label="区域" width="100" />
      <el-table-column label="排-层-位" width="120">
        <template #default="{ row }">{{ [row.row_label, row.shelf, row.bin].filter(Boolean).join('-') || '-' }}</template>
      </el-table-column>
      <el-table-column label="类型" width="80">
        <template #default="{ row }">{{ typeLabel(row.location_type) }}</template>
      </el-table-column>
      <el-table-column label="容量(已用/最大)" width="120">
        <template #default="{ row }">{{ row.current_occupied ?? 0 }} / {{ row.max_capacity ?? 0 }}</template>
      </el-table-column>
      <el-table-column label="利用率" width="150">
        <template #default="{ row }">
          <el-progress :percentage="Math.round(row.usage_rate ?? 0)" :status="usageBarStatus(row.usage_rate)" :stroke-width="16" />
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="sort_order" label="排序号" width="70" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="(row.current_occupied ?? 0) === 0" link type="danger" size="small" @click="handleDelete(row.id)">删除</el-button>
          <el-button link type="warning" size="small" @click="openOccupyAdjust(row)">调整占用量</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div style="margin-top:12px;text-align:right">
      <el-pagination
        v-model:current-page="page" :page-size="pageSize" :total="total"
        layout="total, prev, pager, next" @current-change="fetchData"
      />
    </div>

    <!-- Create / Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑库位' : '新建库位'" width="620px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="所属仓库" prop="warehouse_id">
              <el-select v-model="form.warehouse_id" placeholder="选择仓库" style="width:100%" filterable>
                <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="库位编码" prop="code">
              <el-input v-model="form.code" :disabled="isEdit" placeholder="编码创建后不可修改" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="名称" prop="name">
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="区域">
              <el-input v-model="form.zone" placeholder="如 A区 / 冷库" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="排-层-位">
          <el-row :gutter="8">
            <el-col :span="8"><el-input v-model="form.row_label" placeholder="排" /></el-col>
            <el-col :span="8"><el-input v-model="form.shelf" placeholder="层" /></el-col>
            <el-col :span="8"><el-input v-model="form.bin" placeholder="位" /></el-col>
          </el-row>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="最大容量">
              <el-input-number v-model="form.max_capacity" :min="0" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="类型" prop="location_type">
              <el-select v-model="form.location_type" style="width:100%">
                <el-option label="存储" value="storage" />
                <el-option label="收货" value="receiving" />
                <el-option label="拣货" value="picking" />
                <el-option label="退货" value="return" />
                <el-option label="待检" value="quarantine" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="可锁定">
              <el-switch v-model="form.is_lockable" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="排序号">
              <el-input-number v-model="form.sort_order" :min="0" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>

        <!-- Detail info section (edit mode only) -->
        <template v-if="isEdit && editId">
          <el-divider content-position="left">详细信息</el-divider>
          <el-row :gutter="16" class="detail-row">
            <el-col :span="8">
              <div class="detail-item">
                <span class="detail-label">当前占用量</span>
                <span class="detail-val">{{ detailInfo.current_occupied }}</span>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="detail-item">
                <span class="detail-label">利用率</span>
                <span class="detail-val">{{ detailInfo.usage_rate }}%</span>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="detail-item">
                <span class="detail-label">状态</span>
                <el-tag :type="statusTag(detailInfo.status)" size="small">{{ statusLabel(detailInfo.status) }}</el-tag>
              </div>
            </el-col>
          </el-row>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- Occupancy Adjustment Dialog -->
    <el-dialog v-model="occupyVisible" title="调整占用量" width="380px">
      <el-form ref="occupyRef" :model="occupyForm" :rules="occupyRules" label-width="90px">
        <el-form-item label="库位">
          <span>{{ occupyForm.code }}</span>
        </el-form-item>
        <el-form-item label="当前占用量">
          <span>{{ occupyForm.current_occupied }}</span>
        </el-form-item>
        <el-form-item label="最大容量">
          <span>{{ occupyForm.max_capacity }}</span>
        </el-form-item>
        <el-form-item label="调整数量" prop="qty">
          <el-input-number v-model="occupyForm.qty" :min="0" :max="occupyForm.max_capacity" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="occupyVisible = false">取消</el-button>
        <el-button type="primary" @click="handleOccupyAdjust" :loading="occupying">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

// --- Types ---
interface Warehouse {
  id: number; name: string; code: string
}
interface StorageLocation {
  id: number; warehouse_id: number; warehouse_name: string
  code: string; name: string; zone: string | null
  row_label: string | null; shelf: string | null; bin: string | null
  location_type: string; max_capacity: number; current_occupied: number
  usage_rate: number; status: string; is_lockable: boolean
  sort_order: number; remark: string | null
}
interface StatsOverview {
  total_locations: number; active_count: number; full_count: number
  blocked_count: number; usage_rate: number
}

// --- Reactive State ---
const items = ref<StorageLocation[]>([])
const warehouses = ref<Warehouse[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filter = ref({
  warehouse_id: undefined as number | undefined,
  zone: '',
  location_type: '',
  status: '',
  keyword: '',
})

const stats = ref<StatsOverview>({
  total_locations: 0,
  active_count: 0,
  full_count: 0,
  blocked_count: 0,
  usage_rate: 0,
})

// --- KPI Cards ---
const kpiCards = computed(() => [
  { label: '总库位数', value: stats.value.total_locations, danger: false },
  { label: '可用', value: stats.value.active_count, danger: false },
  { label: '已满', value: stats.value.full_count, danger: stats.value.full_count > 0 },
  { label: '维护中', value: stats.value.blocked_count, danger: stats.value.blocked_count > 0 },
  { label: '利用率', value: stats.value.usage_rate + '%', danger: stats.value.usage_rate > 90 },
])

// --- Display helpers ---
function typeLabel(t: string): string {
  const map: Record<string, string> = {
    storage: '存储', receiving: '收货', picking: '拣货',
    return: '退货', quarantine: '待检',
  }
  return map[t] || t
}

function statusTag(s: string): string {
  const map: Record<string, string> = {
    active: 'success', full: 'warning', blocked: 'danger', inactive: 'info',
  }
  return map[s] || 'info'
}

function statusLabel(s: string): string {
  const map: Record<string, string> = {
    active: '可用', full: '已满', blocked: '维护中', inactive: '停用',
  }
  return map[s] || s
}

function usageBarStatus(rate: number): string {
  if (rate >= 100) return 'exception'
  if (rate >= 80) return 'warning'
  return 'success'
}

// --- Data Fetching ---
async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (filter.value.warehouse_id) params.warehouse_id = filter.value.warehouse_id
    if (filter.value.zone) params.zone = filter.value.zone
    if (filter.value.location_type) params.location_type = filter.value.location_type
    if (filter.value.status) params.status = filter.value.status
    if (filter.value.keyword) params.keyword = filter.value.keyword
    const res = await api.get('/inventory/locations', { params })
    items.value = res.data.items || res.data
    total.value = res.data.total ?? items.value.length
  } catch { /* error handled by axios interceptor */ }
  finally { loading.value = false }
}

async function fetchStats() {
  try {
    const res = await api.get('/inventory/locations/stats/overview')
    stats.value = res.data
  } catch { /* ignore */ }
}

async function fetchWarehouses() {
  try {
    const res = await api.get('/inventory/warehouses')
    warehouses.value = res.data
  } catch { /* ignore */ }
}

// --- Create / Edit Dialog ---
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref()

const form = ref({
  warehouse_id: undefined as number | undefined,
  code: '',
  name: '',
  zone: '',
  row_label: '',
  shelf: '',
  bin: '',
  max_capacity: 0,
  location_type: 'storage',
  is_lockable: false,
  sort_order: 0,
  remark: '',
})

const detailInfo = ref({ current_occupied: 0, usage_rate: 0, status: '' })

const rules = {
  warehouse_id: [{ required: true, message: '请选择仓库', trigger: 'change' }],
  code: [{ required: true, message: '请输入库位编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入库位名称', trigger: 'blur' }],
  location_type: [{ required: true, message: '请选择库位类型', trigger: 'change' }],
}

function openCreate() {
  isEdit.value = false
  editId.value = null
  form.value = {
    warehouse_id: undefined, code: '', name: '', zone: '',
    row_label: '', shelf: '', bin: '', max_capacity: 0,
    location_type: 'storage', is_lockable: false, sort_order: 0, remark: '',
  }
  detailInfo.value = { current_occupied: 0, usage_rate: 0, status: '' }
  dialogVisible.value = true
}

async function openEdit(row: StorageLocation) {
  isEdit.value = true
  editId.value = row.id
  form.value = {
    warehouse_id: row.warehouse_id,
    code: row.code,
    name: row.name,
    zone: row.zone ?? '',
    row_label: row.row_label ?? '',
    shelf: row.shelf ?? '',
    bin: row.bin ?? '',
    max_capacity: row.max_capacity,
    location_type: row.location_type,
    is_lockable: row.is_lockable,
    sort_order: row.sort_order,
    remark: row.remark ?? '',
  }
  // Fetch full detail for the detail section
  try {
    const res = await api.get(`/inventory/locations/${row.id}`)
    detailInfo.value = {
      current_occupied: res.data.current_occupied ?? 0,
      usage_rate: res.data.usage_rate ?? 0,
      status: res.data.status ?? '',
    }
  } catch { /* ignore */ }
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit.value && editId.value) {
      await api.put(`/inventory/locations/${editId.value}`, form.value)
      ElMessage.success('库位已更新')
    } else {
      await api.post('/inventory/locations', form.value)
      ElMessage.success('库位已创建')
    }
    dialogVisible.value = false
    await fetchData()
    await fetchStats()
  } finally { saving.value = false }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定要删除此库位？此操作不可恢复。', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await api.delete(`/inventory/locations/${id}`)
    ElMessage.success('库位已删除')
    await fetchData()
    await fetchStats()
  } catch { /* cancelled or error */ }
}

// --- Occupancy Adjustment ---
const occupyVisible = ref(false)
const occupying = ref(false)
const occupyRef = ref()

const occupyForm = ref({
  id: 0,
  code: '',
  current_occupied: 0,
  max_capacity: 0,
  qty: 0,
})

const occupyRules = {
  qty: [{ required: true, message: '请输入占用量', trigger: 'blur' }],
}

function openOccupyAdjust(row: StorageLocation) {
  occupyForm.value = {
    id: row.id,
    code: row.code,
    current_occupied: row.current_occupied,
    max_capacity: row.max_capacity,
    qty: row.current_occupied,
  }
  occupyVisible.value = true
}

async function handleOccupyAdjust() {
  const valid = await occupyRef.value?.validate().catch(() => false)
  if (!valid) return
  occupying.value = true
  try {
    await api.patch(`/inventory/locations/${occupyForm.value.id}/occupy?qty=${occupyForm.value.qty}`)
    ElMessage.success('占用量已调整')
    occupyVisible.value = false
    await fetchData()
    await fetchStats()
  } finally { occupying.value = false }
}

onMounted(async () => {
  await fetchStats()
  await fetchWarehouses()
  await fetchData()
})
</script>

<style scoped>
.kpi-row {
  margin-bottom: 16px;
}
.kpi-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 6px;
}
.kpi-value {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
}
.kpi-danger .kpi-value {
  color: #f56c6c;
}
.page-toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.detail-row {
  margin-top: 4px;
}
.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.detail-label {
  font-size: 12px;
  color: #909399;
}
.detail-val {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
</style>
