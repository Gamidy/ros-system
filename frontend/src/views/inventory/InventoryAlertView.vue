<template>
  <div class="inventory-page">
    <!-- KPI 卡片 -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :span="6">
        <el-card shadow="hover" :body-style="{ padding: '16px' }">
          <div class="kpi-label">总预警数</div>
          <div class="kpi-value">{{ stats.total }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" :body-style="{ padding: '16px' }">
          <div class="kpi-label">低库存预警</div>
          <div class="kpi-value" :class="{ 'kpi-danger': stats.low_stock > 0 }">{{ stats.low_stock }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" :body-style="{ padding: '16px' }">
          <div class="kpi-label">再订货提醒</div>
          <div class="kpi-value" :class="{ 'kpi-danger': stats.reorder > 0 }">{{ stats.reorder }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" :body-style="{ padding: '16px' }">
          <div class="kpi-label">已处理</div>
          <div class="kpi-value">{{ stats.resolved }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 工具栏 -->
    <div class="page-toolbar">
      <el-button @click="fetchData" :disabled="loading">刷新</el-button>
      <el-button type="warning" @click="handleAlertCheck" :loading="checking">检查库存</el-button>
      <el-select v-model="filter.alert_type" placeholder="预警类型" clearable style="width:150px" @change="fetchData">
        <el-option label="全部" value="" />
        <el-option label="低库存" value="low_stock" />
        <el-option label="再订货" value="reorder" />
      </el-select>
      <el-checkbox v-model="filter.is_resolved" label="已处理" @change="fetchData" />
    </div>

    <!-- 预警列表 -->
    <el-table :data="items" border stripe v-loading="loading" style="width:100%">
      <el-table-column prop="part_no" label="物料编码" width="130" />
      <el-table-column prop="part_name" label="物料名称" min-width="150" />
      <el-table-column prop="warehouse_name" label="仓库" width="110" />
      <el-table-column prop="current_qty" label="当前库存" width="90" />
      <el-table-column prop="min_stock" label="最低库存线" width="100" />
      <el-table-column prop="reorder_point" label="再订货点" width="100" />
      <el-table-column label="预警类型" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.alert_type === 'low_stock'" type="danger" size="small">紧急</el-tag>
          <el-tag v-else-if="row.alert_type === 'reorder'" type="warning" size="small">警告</el-tag>
          <el-tag v-else type="info" size="small">提示</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="message" label="预警消息" min-width="200" show-overflow-tooltip />
      <el-table-column label="预警时间" width="170">
        <template #default="{ row }">{{ formatTime(row.alert_time) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.is_resolved" type="success" size="small">已处理</el-tag>
          <el-tag v-else type="danger" size="small">待处理</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="110" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="!row.is_resolved"
            type="primary"
            size="small"
            @click="handleResolve(row)"
          >
            标记已处理
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <div style="margin-top:12px;text-align:right">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchData"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

interface AlertItem {
  id: number
  part_no: string
  part_name: string | null
  warehouse_name: string
  current_qty: number
  min_stock: number
  reorder_point: number
  alert_type: string   // 'low_stock' | 'reorder'
  severity?: string    // 'critical' | 'warning' | 'info'
  message: string
  alert_time: string
  is_resolved: boolean
}

interface StatsData {
  total: number
  low_stock: number
  reorder: number
  resolved: number
}

const items = ref<AlertItem[]>([])
const loading = ref(false)
const checking = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const stats = ref<StatsData>({ total: 0, low_stock: 0, reorder: 0, resolved: 0 })
const filter = reactive({
  alert_type: '',
  is_resolved: false,
})

function formatTime(t: string): string {
  if (!t) return ''
  // Return ISO string as-is; the backend sends formatted datetime
  return t.replace('T', ' ').substring(0, 19)
}

async function fetchStats() {
  try {
    const res = await api.post('/inventory/alert-check')
    const data = res.data
    stats.value.total = data.total_checked ?? 0
    stats.value.low_stock = data.low_stock_count ?? 0
    stats.value.reorder = data.reorder_count ?? 0
  } catch {
    // alert-check may fail if no inventory items exist; start with zeroes
    stats.value.total = 0
    stats.value.low_stock = 0
    stats.value.reorder = 0
  }
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (filter.alert_type) params.alert_type = filter.alert_type
    if (filter.is_resolved) params.is_resolved = true
    const res = await api.get('/inventory/alerts', { params })
    items.value = res.data.items ?? []
    total.value = res.data.total ?? 0

    // Update resolved count from totals if available
    if (res.data.resolved_count !== undefined) {
      stats.value.resolved = res.data.resolved_count
    }
  } catch {
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function handleAlertCheck() {
  checking.value = true
  try {
    const res = await api.post('/inventory/alert-check')
    const data = res.data
    stats.value.total = data.total_checked ?? 0
    stats.value.low_stock = data.low_stock_count ?? 0
    stats.value.reorder = data.reorder_count ?? 0

    if (data.alerts_created > 0) {
      ElMessage.success(`库存检查完成，新增 ${data.alerts_created} 条预警`)
    } else {
      ElMessage.info('库存检查完成，未发现新预警')
    }

    // Refresh the table after check
    await fetchData()
  } catch (e: unknown) {
    ElMessage.error('库存检查失败')
  } finally {
    checking.value = false
  }
}

async function handleResolve(row: AlertItem) {
  try {
    await api.patch(`/inventory/alerts/${row.id}/resolve`)
    ElMessage.success('已标记为已处理')
    row.is_resolved = true
    stats.value.resolved += 1
    // Refresh to reflect the change
    await fetchData()
  } catch {
    ElMessage.error('操作失败')
  }
}

onMounted(async () => {
  await fetchStats()
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
