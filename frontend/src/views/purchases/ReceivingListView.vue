<template>
  <div class="receiving-page">
    <!-- KPI -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">收货单总数</div>
          <div class="kpi-value">{{ stats.total ?? '-' }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">待检验</div>
          <div class="kpi-value" style="color:#e6a23c">{{ stats.pending_inspection ?? 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">已检验</div>
          <div class="kpi-value" style="color:#67c23a">{{ stats.inspected ?? 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">退货</div>
          <div class="kpi-value" style="color:#f56c6c">{{ stats.rejected ?? 0 }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input v-model="keyword" placeholder="搜索单号/供应商" clearable style="width:200px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-select v-model="filterStatus" placeholder="状态" clearable style="width:140px" @change="fetchData">
        <el-option label="待检验" value="pending_inspection" />
        <el-option label="已检验" value="inspected" />
        <el-option label="退货" value="rejected" />
      </el-select>
      <el-button type="primary" @click="fetchData">查询</el-button>
      <el-button type="success" @click="openCreate">+ 新建收货</el-button>
    </div>

    <!-- 表格 -->
    <el-table :data="receipts" border stripe v-loading="loading" style="width:100%">
      <el-table-column prop="receipt_no" label="收货单号" width="180" sortable />
      <el-table-column prop="supplier_name" label="供应商" min-width="140" />
      <el-table-column prop="total_qty" label="数量" width="80" sortable />
      <el-table-column prop="total_amount" label="金额(元)" width="120" sortable>
        <template #default="{ row }">¥{{ (row.total_amount ?? 0).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="warehouse" label="仓库" width="100" />
      <el-table-column prop="created_by" label="创建人" width="80" />
      <el-table-column prop="created_at" label="创建时间" width="160" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="viewDetail(row)">详情</el-button>
          <el-button size="small" type="warning" link v-if="row.status === 'pending_inspection'" @click="openInspect(row)">检验</el-button>
          <el-popconfirm title="确认删除?" @confirm="doDelete(row.id)">
            <template #reference>
              <el-button size="small" type="danger" link v-if="row.status === 'pending_inspection'">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建收货弹窗 -->
    <el-dialog v-model="createVisible" title="新建收货单" width="700px" destroy-on-close>
      <el-form :model="form" label-width="100px" size="small">
        <el-form-item label="采购订单" required>
          <el-select v-model="form.order_id" filterable placeholder="选择订单" style="width:100%" @change="onOrderSelect">
            <el-option v-for="o in orderList" :key="o.id" :label="`${o.order_no} - ${o.supplier_name}`" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="仓库"><el-input v-model="form.warehouse" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="库位"><el-input v-model="form.location" /></el-form-item>
          </el-col>
        </el-row>
        <el-divider>收货明细</el-divider>
        <el-table :data="form.items" border size="small" max-height="240" style="width:100%">
          <el-table-column prop="part_no" label="物料编码" width="100" />
          <el-table-column prop="part_name" label="物料名称" min-width="120" />
          <el-table-column prop="ordered_qty" label="PO数量" width="80" />
          <el-table-column label="收货数量" width="100">
            <template #default="{ row }">
              <el-input-number v-model="row.received_qty" :min="0" :max="row.ordered_qty" size="small" style="width:90px" />
            </template>
          </el-table-column>
          <el-table-column prop="unit_price" label="单价" width="80" />
        </el-table>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="doCreate" :loading="saving">确认收货</el-button>
      </template>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="收货详情" width="700px" destroy-on-close>
      <template v-if="detail">
        <div class="detail-header">
          <strong>{{ detail.receipt_no }}</strong>
          <el-tag :type="statusTag(detail.status)" size="small" style="margin-left:8px">{{ statusLabel(detail.status) }}</el-tag>
        </div>
        <el-descriptions :column="3" size="small" border style="margin-top:12px">
          <el-descriptions-item label="供应商">{{ detail.supplier_name }}</el-descriptions-item>
          <el-descriptions-item label="仓库">{{ detail.warehouse || '-' }}</el-descriptions-item>
          <el-descriptions-item label="库位">{{ detail.location || '-' }}</el-descriptions-item>
          <el-descriptions-item label="总数量">{{ detail.total_qty }}</el-descriptions-item>
          <el-descriptions-item label="总金额">¥{{ (detail.total_amount ?? 0).toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ detail.created_by || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ detail.created_at }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ detail.remark || '-' }}</el-descriptions-item>
        </el-descriptions>
        <el-divider>收货明细</el-divider>
        <el-table :data="detail.items || []" border size="small" style="width:100%">
          <el-table-column prop="part_no" label="编码" width="90" />
          <el-table-column prop="part_name" label="名称" min-width="100" />
          <el-table-column prop="ordered_qty" label="PO数" width="70" />
          <el-table-column prop="received_qty" label="收货" width="70" />
          <el-table-column prop="accepted_qty" label="合格" width="70" />
          <el-table-column prop="rejected_qty" label="不合格" width="70" />
          <el-table-column prop="total_price" label="金额" width="80">
            <template #default="{ row }">¥{{ (row.total_price ?? 0).toFixed(2) }}</template>
          </el-table-column>
        </el-table>
        <el-divider>检验记录</el-divider>
        <el-table :data="inspections" border size="small" v-loading="inspLoading" style="width:100%">
          <el-table-column prop="part_no" label="物料" width="90" />
          <el-table-column prop="sample_qty" label="抽检数" width="70" />
          <el-table-column prop="defect_qty" label="缺陷数" width="70" />
          <el-table-column prop="defect_desc" label="缺陷描述" min-width="120" />
          <el-table-column label="结果" width="80">
            <template #default="{ row }">
              <el-tag :type="(row.result === 'reject' ? 'danger' : row.result === 'concession' ? 'warning' : 'success')" size="small">{{ ({pass:'合格',concession:'让步',reject:'退货'} as Record<string,string>)[row.result] || row.result }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="inspector" label="检验员" width="80" />
          <el-table-column prop="inspected_at" label="时间" width="90">
            <template #default="{ row }">{{ (row.inspected_at || '').substring(0,10) }}</template>
          </el-table-column>
        </el-table>
      </template>
    </el-dialog>

    <!-- 检验弹窗 -->
    <el-dialog v-model="inspectVisible" title="来料检验" width="500px" destroy-on-close>
      <template v-if="inspectReceipt">
        <div style="margin-bottom:12px"><strong>{{ inspectReceipt.receipt_no }}</strong> — 供应商: {{ inspectReceipt.supplier_name }}</div>
        <el-form :model="inspectForm" label-width="80px" size="small">
          <el-form-item label="物料">
            <el-select v-model="inspectForm.receipt_item_id" filterable placeholder="选择物料" style="width:100%">
              <el-option v-for="it in (inspectReceipt.items || [])" :key="it.id" :label="`${it.part_no} - ${it.part_name}`" :value="it.id" />
            </el-select>
          </el-form-item>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="抽检数">
                <el-input-number v-model="inspectForm.sample_qty" :min="0" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="缺陷数">
                <el-input-number v-model="inspectForm.defect_qty" :min="0" style="width:100%" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="判定">
            <el-radio-group v-model="inspectForm.result">
              <el-radio value="pass">合格</el-radio>
              <el-radio value="concession">让步接收</el-radio>
              <el-radio value="reject">退货</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="缺陷描述">
            <el-input v-model="inspectForm.defect_desc" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="inspectForm.remark" />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="inspectVisible = false">取消</el-button>
        <el-button type="primary" @click="doInspect" :loading="inspSaving">提交检验</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listReceipts, getReceipt, createReceipt, deleteReceipt, listInspections, createInspection, getReceiptStats } from '../../api/purchase'
import api from '../../api'
import { ElMessage } from 'element-plus'

const loading = ref(false); const saving = ref(false)
const inspLoading = ref(false); const inspSaving = ref(false)
const keyword = ref(''); const filterStatus = ref('')
const receipts = ref<any[]>([]); const stats = ref<Record<string,number>>({})
const createVisible = ref(false); const detailVisible = ref(false)
const inspectVisible = ref(false)
const orderList = ref<any[]>([])
const detail = ref<any>(null); const inspections = ref<any[]>([])
const inspectReceipt = ref<any>(null)

const form = ref<Record<string,any>>({ order_id: '', warehouse: '', location: '', remark: '', items: [] })
const inspectForm = ref({ receipt_item_id: '', sample_qty: 0, defect_qty: 0, result: 'pass', defect_desc: '', remark: '', receipt_id: 0 })

function statusTag(s: string) {
  const m: Record<string,string> = { pending_inspection: 'warning', inspected: 'success', rejected: 'danger', partially_rejected: 'danger' }
  return m[s] || 'info'
}
function statusLabel(s: string) {
  const m: Record<string,string> = { pending_inspection: '待检验', inspected: '已检验', rejected: '退货', partially_rejected: '部分退货' }
  return m[s] || s
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string,any> = {}
    if (keyword.value) params.keyword = keyword.value
    if (filterStatus.value) params.status = filterStatus.value
    const res: any = await listReceipts(params)
    receipts.value = (res?.data ?? res ?? []) as any[]
  } catch { receipts.value = [] }
  finally { loading.value = false }
}
async function fetchStats() {
  try { const r:any = await getReceiptStats(); stats.value = (r?.data ?? r ?? {}) } catch { stats.value = {} }
}

async function fetchOrders() {
  try { const r:any = await api.get('/purchases/orders', { params: { status: 'ordered' } }); orderList.value = (r?.data ?? r ?? []) } catch { orderList.value = [] }
}

function openCreate() {
  form.value = { order_id: '', warehouse: '', location: '', remark: '', items: [] }
  createVisible.value = true
  fetchOrders()
}
function onOrderSelect(orderId: number) {
  const order = orderList.value.find(o => o.id === orderId)
  if (!order) return
  // 加载PO明细
  api.get(`/purchases/orders/${orderId}`).then((res: any) => {
    const data = (res?.data ?? res ?? {}) as any
    const items = (data.items || []).map((i: any) => ({
      order_item_id: i.id, part_no: i.part_no, part_name: i.part_name,
      spec: i.spec, unit: i.unit || '个',
      ordered_qty: i.quantity, received_qty: i.quantity, unit_price: i.unit_price,
    }))
    form.value.items = items
  }).catch(() => {})
}
async function doCreate() {
  if (!form.value.order_id) { ElMessage.warning('请选择采购订单'); return }
  if (!form.value.items.length) { ElMessage.warning('请添加收货明细'); return }
  saving.value = true
  try {
    await createReceipt(form.value)
    ElMessage.success('收货单创建成功')
    createVisible.value = false
    fetchData(); fetchStats()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '创建失败') }
  finally { saving.value = false }
}
async function doDelete(id: number) {
  try { await deleteReceipt(id); ElMessage.success('已删除'); fetchData(); fetchStats() }
  catch { ElMessage.error('删除失败') }
}

async function viewDetail(row: any) {
  detailVisible.value = true
  try {
    const r: any = await getReceipt(row.id); detail.value = (r?.data ?? r ?? {}) as any
  } catch { detail.value = null }
  inspLoading.value = true
  try {
    const r: any = await listInspections(row.id); inspections.value = (r?.data ?? r ?? []) as any[]
  } catch { inspections.value = [] }
  finally { inspLoading.value = false }
}

function openInspect(row: any) {
  inspectReceipt.value = row
  inspectForm.value = { receipt_item_id: '', sample_qty: 10, defect_qty: 0, result: 'pass', defect_desc: '', remark: '', receipt_id: row.id }
  inspectVisible.value = true
}
async function doInspect() {
  if (!inspectForm.value.receipt_item_id) { ElMessage.warning('请选择物料'); return }
  inspSaving.value = true
  try {
    await createInspection(inspectForm.value)
    ElMessage.success('检验完成')
    inspectVisible.value = false
    fetchData(); fetchStats()
    // 刷新详情
    if (detail.value && inspectForm.value.receipt_id === detail.value.id) {
      viewDetail(detail.value)
    }
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '检验失败') }
  finally { inspSaving.value = false }
}

onMounted(() => { fetchData(); fetchStats() })
</script>

<style scoped>
.receiving-page { padding: 20px; }
.kpi-row { margin-bottom: 16px; }
.kpi-card { border-radius: 12px; border: 1px solid #e8e8ed; }
.kpi-label { font-size: 13px; color: #86868b; margin-bottom: 6px; }
.kpi-value { font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }
.filter-bar { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
.detail-header { font-size: 15px; }
</style>
