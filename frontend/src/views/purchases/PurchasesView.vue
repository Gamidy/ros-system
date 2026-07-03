<template>
  <div class="page">
    <h2 class="section-title">
      <el-icon><ShoppingCart /></el-icon> 采购管理
    </h2>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="采购订单" name="orders">
        <div style="margin-bottom: 16px;">
          <el-button type="primary" @click="showCreateDialog = true">新建采购订单</el-button>
        </div>
      <!-- 订单状态流转 -->
      <el-card v-if="selectedOrder" shadow="never" style="margin-bottom:16px;border:1px solid #e8e8ed;border-radius:8px;">
        <template #header>
          <div style="display:flex;align-items:center;gap:8px;font-size:14px;font-weight:600;">
            <span>订单状态</span>
            <el-tag size="small" :type="statusType(selectedOrder.status)">{{ statusLabel(selectedOrder.status) }}</el-tag>
            <span style="font-weight:400;color:#86868b;font-size:13px;">{{ selectedOrder.order_no }}</span>
            <el-button text size="small" style="margin-left:auto;" @click="selectedOrder=null">关闭</el-button>
          </div>
        </template>
        <el-steps :active="orderStep(selectedOrder.status)" align-center finish-status="success" process-status="process" style="padding:8px 0 16px;">
          <el-step title="待审批" description="提交审批" />
          <el-step title="已批准" description="审批通过" />
          <el-step title="生产中" description="开始生产" />
          <el-step title="已发货" description="发货中" />
          <el-step title="已收货" description="已完成" />
        </el-steps>
      </el-card>
        <el-table :data="orders" stripe border max-height="520" v-loading="loading" highlight-current-row @row-click="onOrderSelect">
          <el-table-column prop="order_no" label="订单编号" width="200" />
          <el-table-column prop="supplier_name" label="供应商" width="160" />
          <el-table-column prop="total_amount" label="总金额(元)" width="120">
            <template #default="{ row }">¥{{ row.total_amount?.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="requester" label="申请人" width="100" />
          <el-table-column prop="created_at" label="创建时间" width="160" />
          <el-table-column label="操作" min-width="160">
            <template #default="{ row }">
              <el-button size="small" @click="viewOrder(row)">查看</el-button>
              <el-button size="small" type="primary" v-if="row.status === 'draft'" @click="submitOrder(row)">提交审批</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-model:current-page="page" :page-size="20" :total="total"
          layout="prev, pager, next" @current-change="fetchOrders" style="margin-top: 16px;"
        />
      </el-tab-pane>
      <el-tab-pane label="供应商管理" name="suppliers">
        <div style="margin-bottom: 16px;">
          <el-button type="primary" @click="openAddSupplier">新增供应商</el-button>
        </div>
        <el-table :data="suppliers" stripe border max-height="520">
          <el-table-column prop="code" label="编号" width="120" />
          <el-table-column prop="name" label="名称" width="180" />
          <el-table-column prop="contact" label="联系人" width="100" />
          <el-table-column prop="phone" label="电话" width="130" />
          <el-table-column prop="email" label="邮箱" width="160" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button size="small" @click="viewSupplier(row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 创建订单对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建采购订单" width="700px">
      <el-form :model="newOrder" label-width="100px">
        <el-form-item label="供应商">
          <el-select v-model="newOrder.supplier_code" filterable placeholder="选择供应商" style="width:100%">
            <el-option v-for="s in suppliers" :key="s.code" :label="s.name" :value="s.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="newOrder.remark" type="textarea" rows="3" />
        </el-form-item>
        <el-divider>订单明细</el-divider>
        <div v-for="(item, idx) in newOrder.items" :key="idx" style="display:flex; gap:8px; margin-bottom:8px; align-items:center;">
          <el-input v-model="item.part_no" placeholder="物料编码" style="width:120px;" />
          <el-input v-model="item.part_name" placeholder="物料名称" style="width:140px;" />
          <el-input-number v-model="item.quantity" :min="1" style="width:100px;" />
          <el-input-number v-model="item.unit_price" :min="0" :step="0.01" style="width:130px;" />
          <el-button type="danger" size="small" @click="newOrder.items.splice(idx,1)">×</el-button>
        </div>
        <el-button type="primary" link @click="newOrder.items.push({part_no:'',part_name:'',quantity:1,unit_price:0})">+ 添加行</el-button>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createOrder" :loading="saving">提交</el-button>
      </template>
    </el-dialog>

    <!-- 新增供应商对话框 -->
    <el-dialog v-model="showSupplierDialog" title="新增供应商" width="640px" destroy-on-close>
      <el-form :model="supplierForm" label-width="100px" size="small">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="编码" required>
              <el-input v-model="supplierForm.code" placeholder="自动或手动输入" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="名称" required>
              <el-input v-model="supplierForm.name" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="品类">
              <el-select v-model="supplierForm.category" placeholder="选择品类" clearable style="width:100%">
                <el-option label="电子" value="电子" />
                <el-option label="结构" value="结构" />
                <el-option label="包装" value="包装" />
                <el-option label="辅料" value="辅料" />
                <el-option label="五金" value="五金" />
                <el-option label="塑料" value="塑料" />
                <el-option label="其他" value="其他" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="supplierForm.status" style="width:100%">
                <el-option label="潜在" value="potential" />
                <el-option label="合格" value="qualified" />
                <el-option label="合作中" value="active" />
                <el-option label="暂停" value="suspended" />
                <el-option label="黑名单" value="blacklisted" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="联系人"><el-input v-model="supplierForm.contact" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="电话"><el-input v-model="supplierForm.phone" /></el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="邮箱"><el-input v-model="supplierForm.email" /></el-form-item>
        <el-form-item label="地址"><el-input v-model="supplierForm.address" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSupplierDialog = false">取消</el-button>
        <el-button type="primary" @click="saveSupplier">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ShoppingCart } from '@element-plus/icons-vue'
import api from '../../api'

interface OrderDto {
  id: number
  order_no: string
  supplier_name: string
  total_amount: number
  status: string
  requester: string
  created_at: string
}

interface SupplierDto {
  code: string
  name: string
  contact: string
  phone: string
  email: string
}

interface OrderItemDto {
  part_no: string
  part_name: string
  quantity: number
  unit_price: number
}

interface NewOrderDto {
  supplier_code: string
  remark: string
  items: OrderItemDto[]
}

const activeTab = ref('orders')
const selectedOrder = ref<OrderDto | null>(null)
const loading = ref(false)
const saving = ref(false)
const orders = ref<OrderDto[]>([])
const suppliers = ref<SupplierDto[]>([])
const page = ref(1)
const total = ref(0)
const showCreateDialog = ref(false)
const showSupplierDialog = ref(false)
const savingSupplier = ref(false)
const supplierForm = ref<Record<string, any>>({
  code: '', name: '', category: '', status: 'potential',
  contact: '', phone: '', email: '', address: '',
})

const newOrder = ref<NewOrderDto>({ supplier_code: '', remark: '', items: [{ part_no: '', part_name: '', quantity: 1, unit_price: 0 }] })

function onOrderSelect(row: OrderDto) {
  selectedOrder.value = row
}
function orderStep(status: string): number {
  const m: Record<string, number> = { pending_approval: 0, approved: 1, ordered: 2, received: 4 }
  return m[status] ?? -1
}
function statusType(s: string) {
  const m: Record<string, string> = { draft: 'info', pending_approval: 'warning', approved: 'primary', ordered: 'success', received: '', cancelled: 'danger' }
  return m[s] || 'info'
}
function statusLabel(s: string) {
  const m: Record<string, string> = { draft: '草稿', pending_approval: '待审批', approved: '已批准', ordered: '已下单', received: '已收货', cancelled: '已取消' }
  return m[s] || s
}

async function fetchOrders() {
  loading.value = true
  try {
    const res = await api.get('/purchases/orders', { params: { page: page.value, page_size: 20 } })
    const d = res.data
    orders.value = d.items || d || []
    total.value = d.total || orders.value.length
  } finally { loading.value = false }
}

async function fetchSuppliers() {
  const res = await api.get('/purchases/suppliers')
  suppliers.value = res.data || []
}

async function createOrder() {
  // 校验：至少有一个物料单价 > 0
  if (!newOrder.value.items.some((it: OrderItemDto) => it.unit_price > 0)) {
    ElMessage.warning('请至少为一行明细填写大于 0 的单价')
    return
  }
  saving.value = true
  try {
    await api.post('/purchases/orders', newOrder.value)
    ElMessage.success('创建成功')
    showCreateDialog.value = false
    newOrder.value = { supplier_code: '', remark: '', items: [{ part_no: '', part_name: '', quantity: 1, unit_price: 0 }] }
    fetchOrders()
  } finally { saving.value = false }
}

function viewOrder(row: OrderDto) {
  ElMessage.info(`订单 ${row.order_no} 详情功能开发中`)
}
function submitOrder(row: OrderDto) {
  ElMessageBox.confirm('确认提交审批?', '提示').then(async () => {
    await api.patch(`/purchases/orders/${row.id}`, { status: 'pending_approval' })
    ElMessage.success('已提交审批')
    fetchOrders()
  }).catch(() => {})
}
function viewSupplier(row: SupplierDto) {
  ElMessage.info(`供应商 ${row.name} 详情功能开发中`)
}
function openAddSupplier() {
  supplierForm.value = { code: '', name: '', category: '', status: 'potential', contact: '', phone: '', email: '', address: '' }
  showSupplierDialog.value = true
}
async function saveSupplier() {
  savingSupplier.value = true
  try {
    await api.post('/purchases/suppliers', supplierForm.value)
    ElMessage.success('供应商创建成功')
    showSupplierDialog.value = false
    fetchSuppliers()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '创建供应商失败')
  } finally {
    savingSupplier.value = false
  }
}

onMounted(() => { fetchOrders(); fetchSuppliers() })
</script>

<style scoped>
.page { padding: 0; }
.section-title { display: flex; align-items: center; gap: 8px; font-size: 18px; margin-bottom: 16px; }
</style>
