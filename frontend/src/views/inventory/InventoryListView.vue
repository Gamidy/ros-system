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
      <el-select v-model="filter.warehouse_id" placeholder="仓库" clearable style="width:150px" @change="fetchData">
        <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
      </el-select>
      <el-input v-model="filter.part_no" placeholder="物料编码" clearable style="width:160px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-input v-model="filter.part_name" placeholder="物料名称" clearable style="width:160px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-checkbox v-model="filter.low_stock" label="仅低库存" @change="fetchData" />
      <el-button type="primary" @click="openAdjust">库存调整</el-button>
    </div>

    <!-- 库存列表 -->
    <el-table :data="items" border stripe v-loading="loading" style="width:100%" @sort-change="handleSort">
      <el-table-column prop="warehouse_name" label="仓库" width="110" />
      <el-table-column prop="part_no" label="物料编码" width="130" />
      <el-table-column prop="part_name" label="物料名称" min-width="150" />
      <el-table-column prop="spec" label="规格" width="130" />
      <el-table-column prop="unit" label="单位" width="60" />
      <el-table-column prop="qty" label="库存量" width="90" sortable="custom" />
      <el-table-column prop="available_qty" label="可用量" width="90" />
      <el-table-column prop="locked_qty" label="锁定量" width="90" />
      <el-table-column prop="min_stock" label="最低库存" width="90" />
      <el-table-column prop="unit_cost" label="单价" width="100">
        <template #default="{ row }">{{ row.unit_cost?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="total_value" label="库存金额" width="120">
        <template #default="{ row }">{{ row.total_value?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.min_stock > 0 && row.qty <= row.min_stock" type="danger" size="small">低库存</el-tag>
          <el-tag v-else type="success" size="small">正常</el-tag>
        </template>
      </el-table-column>
    </el-table>
    <div style="margin-top:12px;text-align:right">
      <el-pagination
        v-model:current-page="page" :page-size="pageSize" :total="total"
        layout="total, prev, pager, next" @current-change="fetchData"
      />
    </div>

    <!-- 库存调整弹窗 -->
    <el-dialog v-model="adjustVisible" title="库存调整" width="520px">
      <el-form ref="adjustRef" :model="adjustForm" :rules="adjustRules" label-width="100px">
        <el-form-item label="仓库" prop="warehouse_id">
          <el-select v-model="adjustForm.warehouse_id" placeholder="选择仓库" style="width:100%" filterable>
            <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="物料编码" prop="part_no">
          <el-input v-model="adjustForm.part_no" placeholder="输入物料编码" />
        </el-form-item>
        <el-form-item label="物料名称">
          <el-input v-model="adjustForm.part_name" />
        </el-form-item>
        <el-form-item label="规格">
          <el-input v-model="adjustForm.spec" />
        </el-form-item>
        <el-form-item label="操作类型" prop="trans_type">
          <el-radio-group v-model="adjustForm.trans_type">
            <el-radio value="in">入库</el-radio>
            <el-radio value="out">出库</el-radio>
            <el-radio value="adjust">调整(直接设量)</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="数量" prop="qty">
          <el-input-number v-model="adjustForm.qty" :min="0.01" :step="1" :precision="1" style="width:200px" />
        </el-form-item>
        <el-form-item label="单价(成本)">
          <el-input-number v-model="adjustForm.unit_cost" :min="0" :step="0.01" :precision="2" style="width:200px" />
        </el-form-item>
        <el-form-item label="最低库存">
          <el-input-number v-model="adjustForm.set_min_stock" :min="0" :step="1" :precision="1" style="width:200px" />
        </el-form-item>
        <el-form-item label="最高库存">
          <el-input-number v-model="adjustForm.set_max_stock" :min="0" :step="1" :precision="1" style="width:200px" />
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
import { ElMessage } from 'element-plus'
import api from '../../api'

interface Warehouse { id: number; name: string; code: string }
interface InvItem {
  id: number; warehouse_id: number; warehouse_name: string
  part_no: string; part_name: string | null; spec: string | null; unit: string
  qty: number; available_qty: number; locked_qty: number
  min_stock: number; max_stock: number; unit_cost: number; total_value: number
}

const items = ref<InvItem[]>([])
const warehouses = ref<Warehouse[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filter = ref({ warehouse_id: undefined as number | undefined, part_no: '', part_name: '', low_stock: false })

interface StatsData { total_part_count: number; total_qty: number; total_value: number; low_stock_count: number; warehouse_count: number }
const stats = ref<StatsData>({ total_part_count: 0, total_qty: 0, total_value: 0, low_stock_count: 0, warehouse_count: 0 })

const kpiCards = computed(() => [
  { label: '物料总数', value: stats.value.total_part_count, danger: false },
  { label: '总库存量', value: stats.value.total_qty.toFixed(1), danger: false },
  { label: '库存金额', value: '¥' + stats.value.total_value.toFixed(2), danger: false },
  { label: '低库存物料', value: stats.value.low_stock_count, danger: stats.value.low_stock_count > 0 },
  { label: '仓库数', value: stats.value.warehouse_count, danger: false },
])

// Adjust dialog
const adjustVisible = ref(false)
const adjusting = ref(false)
const adjustForm = ref({
  warehouse_id: undefined as number | undefined,
  part_no: '', part_name: '', spec: '', unit: '个',
  trans_type: 'in', qty: 1, unit_cost: 0,
  set_min_stock: 0, set_max_stock: 0, remark: '',
})
const adjustRules = {
  warehouse_id: [{ required: true, message: '请选择仓库' }],
  part_no: [{ required: true, message: '请输入物料编码' }],
  qty: [{ required: true, message: '请输入数量' }],
}

function openAdjust() {
  adjustForm.value = {
    warehouse_id: undefined, part_no: '', part_name: '', spec: '', unit: '个',
    trans_type: 'in', qty: 1, unit_cost: 0,
    set_min_stock: 0, set_max_stock: 0, remark: '',
  }
  adjustVisible.value = true
}

async function handleAdjust() {
  adjusting.value = true
  try {
    await api.post('/inventory/items/adjust', adjustForm.value)
    ElMessage.success('库存调整成功')
    adjustVisible.value = false
    await fetchData()
    await fetchStats()
  } finally { adjusting.value = false }
}

async function fetchStats() {
  const res = await api.get('/inventory/items/stats')
  stats.value = res.data
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (filter.value.warehouse_id) params.warehouse_id = filter.value.warehouse_id
    if (filter.value.part_no) params.part_no = filter.value.part_no
    if (filter.value.part_name) params.part_name = filter.value.part_name
    if (filter.value.low_stock) params.low_stock = true
    const res = await api.get('/inventory/items', { params })
    items.value = res.data.items
    total.value = res.data.total
  } finally { loading.value = false }
}

async function fetchWarehouses() {
  const res = await api.get('/inventory/warehouses')
  warehouses.value = res.data
}

function handleSort() { /* TODO: server-side sort */ }

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
