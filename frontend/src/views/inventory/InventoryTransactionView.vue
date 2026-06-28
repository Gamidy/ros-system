<template>
  <div class="inventory-page">
    <!-- 筛选栏 -->
    <div class="page-toolbar">
      <el-select v-model="filter.warehouse_id" placeholder="仓库" clearable style="width:150px" @change="fetchData">
        <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
      </el-select>
      <el-input v-model="filter.part_no" placeholder="物料编码" clearable style="width:160px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-select v-model="filter.trans_type" placeholder="类型" clearable style="width:110px" @change="fetchData">
        <el-option label="入库" value="in" />
        <el-option label="出库" value="out" />
        <el-option label="调整" value="adjust" />
      </el-select>
      <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width:260px" @change="handleDateChange" />
    </div>

    <!-- 流水列表 -->
    <el-table :data="items" border stripe v-loading="loading" style="width:100%">
      <el-table-column prop="created_at" label="时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column prop="warehouse_name" label="仓库" width="100" />
      <el-table-column prop="part_no" label="物料编码" width="130" />
      <el-table-column prop="part_name" label="物料名称" min-width="140" />
      <el-table-column prop="spec" label="规格" width="120" />
      <el-table-column label="类型" width="70">
        <template #default="{ row }">
          <el-tag v-if="row.trans_type === 'in'" type="success" size="small">入库</el-tag>
          <el-tag v-else-if="row.trans_type === 'out'" type="warning" size="small">出库</el-tag>
          <el-tag v-else type="info" size="small">调整</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="qty" label="变动量" width="90">
        <template #default="{ row }">
          <span :class="row.qty > 0 ? 'text-green' : 'text-red'">
            {{ row.qty > 0 ? '+' + row.qty : row.qty }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="balance_before" label="变动前" width="80" />
      <el-table-column prop="balance_after" label="变动后" width="80" />
      <el-table-column prop="ref_doc_type" label="来源单据" width="100">
        <template #default="{ row }">
          <span v-if="row.ref_doc_type === 'goods_receipt'">收货单</span>
          <span v-else-if="row.ref_doc_type === 'inspection'">质检单</span>
          <span v-else-if="row.ref_doc_type === 'adjustment'">手动调整</span>
          <span v-else>{{ row.ref_doc_type }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="ref_doc_no" label="单据编号" width="150" />
      <el-table-column prop="operator" label="经办人" width="100" />
      <el-table-column prop="remark" label="备注" min-width="160" />
    </el-table>
    <div style="margin-top:12px;text-align:right">
      <el-pagination
        v-model:current-page="page" :page-size="pageSize" :total="total"
        layout="total, prev, pager, next" @current-change="fetchData"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'

interface Transaction {
  id: number; warehouse_id: number; warehouse_name: string
  part_no: string; part_name: string | null; spec: string | null; unit: string
  trans_type: string; qty: number
  balance_before: number; balance_after: number
  ref_doc_type: string | null; ref_doc_id: number | null; ref_doc_no: string | null
  operator: string | null; remark: string | null; created_at: string
}

const items = ref<Transaction[]>([])
const warehouses = ref<{ id: number; name: string }[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filter = ref({ warehouse_id: undefined as number | undefined, part_no: '', trans_type: '' })
const dateRange = ref<[string, string] | null>(null)

function formatTime(t: string) {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 19)
}

function handleDateChange(_val: [string, string] | null) {
  fetchData()
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (filter.value.warehouse_id) params.warehouse_id = filter.value.warehouse_id
    if (filter.value.part_no) params.part_no = filter.value.part_no
    if (filter.value.trans_type) params.trans_type = filter.value.trans_type
    if (dateRange.value) {
      params.date_from = dateRange.value[0]
      params.date_to = dateRange.value[1]
    }
    const res = await api.get('/inventory/transactions', { params })
    items.value = res.data.items
    total.value = res.data.total
  } finally { loading.value = false }
}

async function fetchWarehouses() {
  const res = await api.get('/inventory/warehouses')
  warehouses.value = res.data
}

onMounted(async () => {
  await fetchWarehouses()
  await fetchData()
})
</script>

<style scoped>
.page-toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.text-green { color: #67c23a; font-weight: 600; }
.text-red { color: #f56c6c; font-weight: 600; }
</style>
