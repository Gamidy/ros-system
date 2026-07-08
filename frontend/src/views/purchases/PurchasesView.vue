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
        <el-table :data="orders" stripe border max-height="520" v-loading="loading">
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
          <el-button type="primary" @click="showSupplierDialog = true">新增供应商</el-button>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ShoppingCart } from '@element-plus/icons-vue'
import api from '../../api'

const activeTab = ref('orders')
const loading = ref(false)
const saving = ref(false)
const orders = ref<any[]>([])
const suppliers = ref<any[]>([])
const page = ref(1)
const total = ref(0)
const showCreateDialog = ref(false)
const showSupplierDialog = ref(false)

const newOrder = ref<any>({ supplier_code: '', remark: '', items: [{ part_no: '', part_name: '', quantity: 1, unit_price: 0 }] })

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
  if (!newOrder.value.items.some((it: any) => it.unit_price > 0)) {
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

function viewOrder(row: any) {
  ElMessage.info(`订单 ${row.order_no} 详情功能开发中`)
}
function submitOrder(row: any) {
  ElMessageBox.confirm('确认提交审批?', '提示').then(async () => {
    await api.patch(`/purchases/orders/${row.id}`, { status: 'pending_approval' })
    ElMessage.success('已提交审批')
    fetchOrders()
  }).catch(() => {})
}
function viewSupplier(row: any) {
  ElMessage.info(`供应商 ${row.name} 详情功能开发中`)
}

onMounted(() => { fetchOrders(); fetchSuppliers() })
</script>

<style scoped>
.page { padding: 0; }
.section-title { display: flex; align-items: center; gap: 8px; font-size: 18px; margin-bottom: 16px; }
</style>
