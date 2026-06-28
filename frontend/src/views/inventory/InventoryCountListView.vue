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

    <!-- 操作栏 -->
    <div class="page-toolbar">
      <el-select v-model="filter.status" placeholder="状态" clearable style="width:130px" @change="fetchData">
        <el-option label="草稿" value="draft" />
        <el-option label="待审" value="pending" />
        <el-option label="进行中" value="in_progress" />
        <el-option label="已完成" value="completed" />
      </el-select>
      <el-button type="primary" @click="openCreate">新建盘点</el-button>
    </div>

    <!-- 盘点列表 -->
    <el-table :data="items" border stripe v-loading="loading" style="width:100%">
      <el-table-column prop="count_no" label="盘点单号" width="170" />
      <el-table-column prop="warehouse_name" label="仓库" width="120" />
      <el-table-column label="类型" width="70">
        <template #default="{ row }">{{ row.count_type === 'full' ? '全盘' : '抽盘' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'draft'" size="small">草稿</el-tag>
          <el-tag v-else-if="row.status === 'pending'" type="warning" size="small">待审</el-tag>
          <el-tag v-else-if="row.status === 'in_progress'" type="primary" size="small">进行中</el-tag>
          <el-tag v-else type="success" size="small">已完成</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="total_items" label="总项数" width="70" />
      <el-table-column prop="matched_count" label="一致" width="60" />
      <el-table-column prop="discrepancy_count" label="差异" width="60">
        <template #default="{ row }">
          <span v-if="row.discrepancy_count > 0" class="text-danger">{{ row.discrepancy_count }}</span>
          <span v-else>0</span>
        </template>
      </el-table-column>
      <el-table-column prop="total_discrepancy_value" label="差异金额" width="120">
        <template #default="{ row }">¥{{ row.total_discrepancy_value?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="counted_by" label="盘点人" width="90" />
      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="{ row }">{{ (row.created_at || '').replace('T',' ').slice(0,16) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
          <el-button v-if="row.status === 'draft'" link type="primary" size="small" @click="openSubmit(row)">提交</el-button>
          <el-button v-if="row.status === 'pending'" link type="primary" size="small" @click="openComplete(row)">完成</el-button>
          <el-popconfirm v-if="row.status === 'draft'" title="确定删除此盘点计划？" @confirm="handleDelete(row.id)">
            <template #reference><el-button link type="danger" size="small">删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
    <div style="margin-top:12px;text-align:right">
      <el-pagination
        v-model:current-page="page" :page-size="pageSize" :total="total"
        layout="total, prev, pager, next" @current-change="fetchData"
      />
    </div>

    <!-- 新建盘点弹窗 -->
    <el-dialog v-model="createVisible" title="新建盘点" width="700px">
      <el-form ref="createRef" :model="createForm" label-width="90px">
        <el-form-item label="仓库" prop="warehouse_id" :rules="[{required:true,message:'请选择仓库'}]">
          <el-select v-model="createForm.warehouse_id" filterable style="width:100%" @change="onWarehouseChange">
            <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="盘点类型">
          <el-radio-group v-model="createForm.count_type">
            <el-radio value="partial">抽盘</el-radio>
            <el-radio value="full">全盘</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="盘点人">
          <el-input v-model="createForm.counted_by" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="createForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="saving">创建</el-button>
      </template>
    </el-dialog>

    <!-- 盘点详情弹窗 -->
    <el-dialog v-model="detailVisible" :title="'盘点单: ' + detail.count_no" width="800px">
      <div class="detail-info">
        <span>仓库: {{ detail.warehouse_name }} | </span>
        <span>状态: {{ detail.status }} | </span>
        <span>类型: {{ detail.count_type === 'full' ? '全盘' : '抽盘' }} | </span>
        <span>盘点人: {{ detail.counted_by || '-' }}</span>
      </div>
      <el-table :data="detail.items || []" border stripe size="small" max-height="400" style="margin-top:12px;width:100%">
        <el-table-column prop="part_no" label="物料编码" width="120" />
        <el-table-column prop="part_name" label="物料名称" min-width="130" />
        <el-table-column prop="system_qty" label="系统数" width="70" />
        <el-table-column prop="actual_qty" label="实盘数" width="70" />
        <el-table-column prop="diff_qty" label="差异" width="70">
          <template #default="{ row }">
            <span v-if="row.diff_qty !== 0" :class="row.diff_qty > 0 ? 'text-green' : 'text-danger'">
              {{ row.diff_qty > 0 ? '+' : '' }}{{ row.diff_qty }}
            </span>
            <span v-else>0</span>
          </template>
        </el-table-column>
        <el-table-column prop="diff_value" label="差异金额" width="90">
          <template #default="{ row }">¥{{ row.diff_value?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="70">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'matched'" type="success" size="small">一致</el-tag>
            <el-tag v-else-if="row.status === 'adjusted'" type="primary" size="small">已调</el-tag>
            <el-tag v-else type="danger" size="small">差异</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="100" />
      </el-table>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

interface CountItem {
  id: number; part_no: string; part_name: string | null; system_qty: number
  actual_qty: number; diff_qty: number; diff_value: number; status: string
  unit_cost: number; remark: string | null
}
interface CountRow {
  id: number; count_no: string; warehouse_name: string; count_type: string
  status: string; total_items: number; matched_count: number
  discrepancy_count: number; total_discrepancy_value: number
  counted_by: string | null; created_at: string; items?: CountItem[]
}

const items = ref<CountRow[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filter = ref({ status: '' })
const warehouses = ref<{ id: number; name: string }[]>([])
const createVisible = ref(false)
const detailVisible = ref(false)
const saving = ref(false)
const detail = ref<CountRow>({ id:0,count_no:'',warehouse_name:'',count_type:'',status:'',total_items:0,matched_count:0,discrepancy_count:0,total_discrepancy_value:0,counted_by:null,created_at:'',items:[] })

const stats = ref({ total_counts:0, pending_count:0, completed_count:0, discrepancy_count:0, total_discrepancy_value:0 })

const createForm = ref({ warehouse_id: undefined as number | undefined, count_type: 'partial', counted_by: '', remark: '' })

const kpiCards = computed(() => [
  { label: '盘点总数', value: stats.value.total_counts, danger: false },
  { label: '待处理', value: stats.value.pending_count, danger: stats.value.pending_count > 0 },
  { label: '已完成', value: stats.value.completed_count, danger: false },
  { label: '有差异盘点', value: stats.value.discrepancy_count, danger: stats.value.discrepancy_count > 0 },
  { label: '差异总金额', value: '¥' + stats.value.total_discrepancy_value.toFixed(2), danger: stats.value.total_discrepancy_value > 0 },
])

async function fetchStats() {
  try {
    const res = await api.get('/inventory/counts/stats/overview')
    stats.value = res.data
  } catch {}
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (filter.value.status) params.status = filter.value.status
    const res = await api.get('/inventory/counts', { params })
    items.value = res.data.items
    total.value = res.data.total
  } finally { loading.value = false }
}

async function fetchWarehouses() {
  const res = await api.get('/inventory/warehouses')
  warehouses.value = res.data
}

function onWarehouseChange(_val: number) {}

function openCreate() {
  createForm.value = { warehouse_id: undefined, count_type: 'partial', counted_by: '', remark: '' }
  createVisible.value = true
}

async function handleCreate() {
  if (!createForm.value.warehouse_id) { ElMessage.warning('请选择仓库'); return }
  saving.value = true
  try {
    // 获取仓库全部库存作为盘点项
    let invItems: any[] = []
    try {
      const res = await api.get('/inventory/items', { params: { warehouse_id: createForm.value.warehouse_id, page_size: 500 } })
      invItems = res.data.items || []
    } catch { invItems = [] }

    const payload = {
      ...createForm.value,
      items: invItems.map((i: any) => ({
        inventory_id: i.id,
        part_no: i.part_no,
        part_name: i.part_name,
        spec: i.spec,
        unit: i.unit,
        system_qty: i.qty,
        actual_qty: i.qty,
      })),
    }
    await api.post('/inventory/counts', payload)
    ElMessage.success('盘点计划已创建')
    createVisible.value = false
    await fetchData()
    await fetchStats()
  } finally { saving.value = false }
}

async function openDetail(row: CountRow) {
  const res = await api.get(`/inventory/counts/${row.id}`)
  detail.value = res.data
  detailVisible.value = true
}

async function openSubmit(row: CountRow) {
  await api.post(`/inventory/counts/${row.id}/submit`)
  ElMessage.success('盘点已提交')
  await fetchData()
}

async function openComplete(row: CountRow) {
  await api.post(`/inventory/counts/${row.id}/complete?auto_adjust=true`)
  ElMessage.success('盘点已完成，差异已自动调账')
  await fetchData()
  await fetchStats()
}

async function handleDelete(id: number) {
  await api.delete(`/inventory/counts/${id}`)
  ElMessage.success('盘点计划已删除')
  await fetchData()
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
.page-toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.text-danger { color: #f56c6c; font-weight: 600; }
.text-green { color: #67c23a; font-weight: 600; }
.detail-info { padding: 8px 0; font-size: 14px; color: #606266; }
</style>
