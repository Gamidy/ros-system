<template>
  <div class="return-page">
    <!-- KPI 卡片 -->
    <el-row :gutter="12" class="kpi-row">
      <el-col :span="3" v-for="kpi in kpis" :key="kpi.key">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">{{ kpi.label }}</div>
          <div class="kpi-value" :style="kpi.color ? { color: kpi.color } : {}">
            {{ kpi.prefix }}{{ stats[kpi.key] ?? '-' }}{{ kpi.suffix }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 工具栏 -->
    <div class="filter-bar">
      <el-button @click="fetchData">🔄 刷新</el-button>
      <el-button type="primary" @click="openCreate">+ 新建退货单</el-button>
      <el-select v-model="filterStatus" placeholder="状态" clearable style="width:140px" @change="fetchData">
        <el-option label="全部" value="" />
        <el-option label="草稿" value="draft" />
        <el-option label="待审批" value="pending_approval" />
        <el-option label="已审批" value="approved" />
        <el-option label="已退货" value="returned" />
        <el-option label="已退款" value="refunded" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-input v-model="keyword" placeholder="搜索退货单号/供应商" clearable style="width:220px" @clear="fetchData" @keyup.enter="fetchData" />
    </div>

    <!-- 表格 -->
    <el-table :data="list" border stripe v-loading="loading" style="width:100%">
      <el-table-column prop="return_no" label="退货单号" width="160" sortable />
      <el-table-column prop="supplier_name" label="供应商" min-width="120" />
      <el-table-column label="来源类型" width="100">
        <template #default="{ row }">{{ sourceLabel(row.source_type) }}</template>
      </el-table-column>
      <el-table-column label="退货原因" width="130">
        <template #default="{ row }">{{ reasonLabel(row.return_reason) }}</template>
      </el-table-column>
      <el-table-column prop="responsibility" label="责任方" width="90" />
      <el-table-column prop="return_qty" label="退货数量" width="80" sortable />
      <el-table-column label="退货金额" width="110" sortable sortable-prop="return_amount">
        <template #default="{ row }">¥{{ (row.return_amount ?? 0).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="logistics_no" label="物流单号" width="130" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_by" label="创建人" width="80" />
      <el-table-column prop="created_at" label="创建时间" width="160" />
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <!-- draft: 提交审批 + 删除 -->
          <el-button size="small" type="primary" link v-if="row.status === 'draft'" @click="submitApproval(row)">提交审批</el-button>
          <el-popconfirm title="确认删除？" @confirm="doDelete(row)">
            <template #reference>
              <el-button size="small" type="danger" link v-if="row.status === 'draft'">删除</el-button>
            </template>
          </el-popconfirm>
          <!-- draft/pending: 编辑 -->
          <el-button size="small" type="primary" link v-if="row.status === 'draft' || row.status === 'pending_approval'" @click="openEdit(row)">编辑</el-button>
          <!-- pending_approval: 审批通过 -->
          <el-button size="small" type="success" link v-if="row.status === 'pending_approval'" @click="doApprove(row)">审批通过</el-button>
          <!-- approved: 已退货 -->
          <el-button size="small" type="warning" link v-if="row.status === 'approved'" @click="doReturned(row)">已退货</el-button>
          <!-- returned: 已退款 -->
          <el-button size="small" type="primary" link v-if="row.status === 'returned'" @click="promptRefund(row)">已退款</el-button>
          <!-- 查看详情 -->
          <el-button size="small" type="info" link @click="viewDetail(row)">查看详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div style="margin-top:16px;display:flex;justify-content:flex-end">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="fetchData"
      />
    </div>

    <!-- 新建/编辑退货单弹窗 -->
    <el-dialog v-model="formVisible" :title="isEdit ? '编辑退货单' : '新建退货单'" width="750px" destroy-on-close>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="基本信息" name="basic">
          <el-form :model="form" label-width="110px" size="small">
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="来源类型" required>
                  <el-select v-model="form.source_type" placeholder="选择来源" style="width:100%">
                    <el-option label="质检" value="inspection" />
                    <el-option label="直接退货" value="receipt" />
                    <el-option label="手工" value="manual" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="供应商名称">
                  <el-input v-model="form.supplier_name" placeholder="输入供应商名称" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="供应商编码">
                  <el-input v-model="form.supplier_code" placeholder="输入供应商编码" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="退货原因" required>
                  <el-select v-model="form.return_reason" placeholder="选择原因" style="width:100%">
                    <el-option label="品质不合格" value="quality" />
                    <el-option label="逾期到货" value="overdue" />
                    <el-option label="损坏" value="damaged" />
                    <el-option label="其他" value="other" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="原因说明">
              <el-input v-model="form.reason_detail" type="textarea" :rows="2" placeholder="详细说明..." />
            </el-form-item>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="责任方">
                  <el-select v-model="form.responsibility" placeholder="选择责任方" clearable style="width:100%">
                    <el-option label="供应商" value="supplier" />
                    <el-option label="我方" value="internal" />
                    <el-option label="物流" value="logistics" />
                    <el-option label="其他" value="other" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="物流单号">
                  <el-input v-model="form.logistics_no" placeholder="物流单号" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="备注">
              <el-input v-model="form.remark" type="textarea" :rows="2" />
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="退货明细" name="items">
          <div style="margin-bottom:8px">
            <el-button size="small" type="success" @click="addItemRow">+ 添加行</el-button>
          </div>
          <el-table :data="form.items" border size="small" max-height="300" style="width:100%">
            <el-table-column label="#" width="40" type="index" />
            <el-table-column label="物料编码" width="110">
              <template #default="{ row }">
                <el-input v-model="row.part_no" size="small" placeholder="编码" />
              </template>
            </el-table-column>
            <el-table-column label="物料名称" width="130">
              <template #default="{ row }">
                <el-input v-model="row.part_name" size="small" placeholder="名称" />
              </template>
            </el-table-column>
            <el-table-column label="规格" width="100">
              <template #default="{ row }">
                <el-input v-model="row.spec" size="small" placeholder="可选" />
              </template>
            </el-table-column>
            <el-table-column label="单位" width="70">
              <template #default="{ row }">
                <el-input v-model="row.unit" size="small" placeholder="单位" />
              </template>
            </el-table-column>
            <el-table-column label="退货数量" width="90">
              <template #default="{ row }">
                <el-input-number v-model="row.return_qty" :min="0" size="small" style="width:80px" />
              </template>
            </el-table-column>
            <el-table-column label="单价" width="90">
              <template #default="{ row }">
                <el-input-number v-model="row.unit_price" :min="0" :precision="2" size="small" style="width:80px" @change="calcItemTotal(row)" />
              </template>
            </el-table-column>
            <el-table-column label="小计" width="90">
              <template #default="{ row }">
                ¥{{ ((row.unit_price ?? 0) * (row.return_qty ?? 0)).toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60" fixed="right">
              <template #default="{ $index }">
                <el-button size="small" type="danger" link @click="form.items.splice($index, 1)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" @click="doSave" :loading="saving">提交</el-button>
      </template>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="退货详情" width="800px" destroy-on-close>
      <template v-if="detail">
        <div class="detail-header">
          <strong>{{ detail.return_no }}</strong>
          <el-tag :type="statusTag(detail.status)" size="small" style="margin-left:8px">{{ statusLabel(detail.status) }}</el-tag>
        </div>
        <el-descriptions :column="3" size="small" border style="margin-top:12px">
          <el-descriptions-item label="供应商">{{ detail.supplier_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="供应商编码">{{ detail.supplier_code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="来源类型">{{ sourceLabel(detail.source_type) }}</el-descriptions-item>
          <el-descriptions-item label="退货原因">{{ reasonLabel(detail.return_reason) }}</el-descriptions-item>
          <el-descriptions-item label="原因说明">{{ detail.reason_detail || '-' }}</el-descriptions-item>
          <el-descriptions-item label="责任方">{{ detail.responsibility || '-' }}</el-descriptions-item>
          <el-descriptions-item label="退货数量">{{ detail.return_qty ?? 0 }}</el-descriptions-item>
          <el-descriptions-item label="退货金额">¥{{ (detail.return_amount ?? 0).toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="物流单号">{{ detail.logistics_no || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ detail.created_by || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ detail.created_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ detail.remark || '-' }}</el-descriptions-item>
          <el-descriptions-item label="退款金额" v-if="detail.refund_amount != null">¥{{ (detail.refund_amount ?? 0).toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="退款日期" v-if="detail.refund_date">{{ detail.refund_date }}</el-descriptions-item>
          <el-descriptions-item label="退款方式" v-if="detail.refund_method">{{ detail.refund_method }}</el-descriptions-item>
        </el-descriptions>
        <el-divider>退货明细</el-divider>
        <el-table :data="detail.items || []" border size="small" style="width:100%">
          <el-table-column prop="part_no" label="编码" width="100" />
          <el-table-column prop="part_name" label="名称" min-width="120" />
          <el-table-column prop="spec" label="规格" width="90" />
          <el-table-column prop="unit" label="单位" width="60" />
          <el-table-column prop="return_qty" label="数量" width="70" />
          <el-table-column prop="unit_price" label="单价" width="80">
            <template #default="{ row }">¥{{ (row.unit_price ?? 0).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="小计" width="80">
            <template #default="{ row }">¥{{ ((row.unit_price ?? 0) * (row.return_qty ?? 0)).toFixed(2) }}</template>
          </el-table-column>
        </el-table>
      </template>
    </el-dialog>

    <!-- 退款弹窗 -->
    <el-dialog v-model="refundVisible" title="确认退款" width="480px" destroy-on-close>
      <el-form :model="refundForm" label-width="100px" size="small">
        <el-form-item label="退款金额" required>
          <el-input-number v-model="refundForm.refund_amount" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="退款日期" required>
          <el-date-picker v-model="refundForm.refund_date" type="date" placeholder="选择日期" style="width:100%" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="退款方式" required>
          <el-select v-model="refundForm.refund_method" placeholder="选择方式" style="width:100%">
            <el-option label="银行转账" value="bank_transfer" />
            <el-option label="现金" value="cash" />
            <el-option label="冲抵货款" value="offset" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="refundVisible = false">取消</el-button>
        <el-button type="primary" @click="doRefund" :loading="saving">确认退款</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'
import { ElMessage } from 'element-plus'

/* ── 类型 ── */
interface ReturnItem {
  part_no: string; part_name: string; spec?: string; unit?: string
  return_qty: number; unit_price: number
}

interface ReturnForm {
  id?: number; source_type: string; source_id?: number; supplier_name: string
  supplier_code: string; return_reason: string; reason_detail: string
  responsibility: string; logistics_no: string; remark: string; items: ReturnItem[]
}

interface RefundForm {
  refund_amount: number; refund_date: string; refund_method: string
}

/* ── KPI ── */
const kpis = [
  { key: 'total_count', label: '总退货单', suffix: '' },
  { key: 'draft_count', label: '草稿', suffix: '' },
  { key: 'pending_count', label: '待审批', color: '#e6a23c', suffix: '' },
  { key: 'approved_count', label: '已审批', color: '#67c23a', suffix: '' },
  { key: 'returned_count', label: '已退货', color: '#409eff', suffix: '' },
  { key: 'refunded_count', label: '已退款', color: '#909399', suffix: '' },
  { key: 'total_return_amount', label: '退货总金额(¥)', prefix: '¥', color: '#f56c6c', suffix: '' },
]
const stats = ref<Record<string, any>>({})

/* ── 列表 ── */
const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const filterStatus = ref('')

async function fetchStats() {
  try { const r: any = await api.get('/purchases/returns/stats'); stats.value = r?.data ?? r ?? {} }
  catch { stats.value = {} }
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (filterStatus.value) params.status = filterStatus.value
    if (keyword.value) params.supplier_name = keyword.value // search by supplier_name; API also accepts return_no
    const r: any = await api.get('/purchases/returns', { params })
    const data = r?.data ?? r ?? {}
    list.value = Array.isArray(data) ? data : data?.items ?? data?.data ?? []
    total.value = data?.total ?? data?.count ?? list.value.length
  } catch { list.value = []; total.value = 0 }
  finally { loading.value = false }
}

/* ── 映射 ── */
function sourceLabel(s: string): string {
  const m: Record<string, string> = { inspection: '质检', receipt: '直接退货', manual: '手工' }
  return m[s] || s || '-'
}
function reasonLabel(s: string): string {
  const m: Record<string, string> = { quality: '品质不合格', overdue: '逾期到货', damaged: '损坏', other: '其他' }
  return m[s] || s || '-'
}
function statusTag(s: string): string {
  const m: Record<string, string> = {
    draft: 'info', pending_approval: 'warning', approved: 'success',
    returned: 'primary', refunded: 'info', cancelled: 'info',
  }
  return m[s] || 'info'
}
function statusLabel(s: string): string {
  const m: Record<string, string> = {
    draft: '草稿', pending_approval: '待审批', approved: '已审批',
    returned: '已退货', refunded: '已退款', cancelled: '已取消',
  }
  return m[s] || s || '-'
}

/* ── 创建/编辑 ── */
const formVisible = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const activeTab = ref('basic')

const emptyForm = (): ReturnForm => ({
  source_type: 'manual', supplier_name: '', supplier_code: '',
  return_reason: 'quality', reason_detail: '', responsibility: '',
  logistics_no: '', remark: '', items: [],
})

const form = ref<ReturnForm>(emptyForm())

function openCreate() {
  isEdit.value = false
  form.value = emptyForm()
  activeTab.value = 'basic'
  formVisible.value = true
}

function openEdit(row: any) {
  isEdit.value = true
  activeTab.value = 'basic'
  form.value = {
    id: row.id, source_type: row.source_type || 'manual',
    supplier_name: row.supplier_name || '', supplier_code: row.supplier_code || '',
    return_reason: row.return_reason || 'quality', reason_detail: row.reason_detail || '',
    responsibility: row.responsibility || '', logistics_no: row.logistics_no || '',
    remark: row.remark || '', items: (row.items || []).map((i: any) => ({
      part_no: i.part_no || '', part_name: i.part_name || '',
      spec: i.spec || '', unit: i.unit || '',
      return_qty: i.return_qty ?? 0, unit_price: i.unit_price ?? 0,
    })),
  }
  formVisible.value = true
}

function addItemRow() {
  form.value.items.push({ part_no: '', part_name: '', spec: '', unit: '', return_qty: 0, unit_price: 0 })
}
function calcItemTotal(_row: any) { /* auto-bound via template computation */ }

async function doSave() {
  const f = form.value
  if (!f.source_type || !f.return_reason) { ElMessage.warning('请填写基本信息和退货原因'); return }
  if (!f.items.length || f.items.every(i => !i.part_no)) { ElMessage.warning('请添加至少一条退货明细'); return }
  saving.value = true
  try {
    if (isEdit.value && f.id) {
      await api.put(`/purchases/returns/${f.id}`, f)
      ElMessage.success('更新成功')
    } else {
      await api.post('/purchases/returns', f)
      ElMessage.success('创建成功')
    }
    formVisible.value = false
    fetchData(); fetchStats()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') }
  finally { saving.value = false }
}

/* ── 删除 ── */
async function doDelete(row: any) {
  try {
    await api.delete(`/purchases/returns/${row.id}`)
    ElMessage.success('已删除')
    fetchData(); fetchStats()
  } catch { ElMessage.error('删除失败') }
}

/* ── 状态流转 ── */
async function submitApproval(row: any) {
  try {
    await api.patch(`/purchases/returns/${row.id}/status?status=pending_approval`)
    ElMessage.success('已提交审批')
    fetchData(); fetchStats()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') }
}

async function doApprove(row: any) {
  try {
    await api.patch(`/purchases/returns/${row.id}/status?status=approved`)
    ElMessage.success('审批通过')
    fetchData(); fetchStats()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') }
}

async function doReturned(row: any) {
  try {
    await api.patch(`/purchases/returns/${row.id}/status?status=returned`)
    ElMessage.success('已标记为退货')
    fetchData(); fetchStats()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') }
}

/* ── 退款 ── */
const refundVisible = ref(false)
const refundTarget = ref<any>(null)
const refundForm = ref<RefundForm>({ refund_amount: 0, refund_date: '', refund_method: 'bank_transfer' })

function promptRefund(row: any) {
  refundTarget.value = row
  refundForm.value = { refund_amount: row.return_amount ?? 0, refund_date: '', refund_method: 'bank_transfer' }
  refundVisible.value = true
}

async function doRefund() {
  if (!refundForm.value.refund_amount || !refundForm.value.refund_date || !refundForm.value.refund_method) {
    ElMessage.warning('请完整填写退款信息'); return
  }
  saving.value = true
  try {
    await api.patch(`/purchases/returns/${refundTarget.value.id}/status?status=refunded`, refundForm.value)
    ElMessage.success('退款已确认')
    refundVisible.value = false
    fetchData(); fetchStats()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') }
  finally { saving.value = false }
}

/* ── 详情 ── */
const detailVisible = ref(false)
const detail = ref<any>(null)

async function viewDetail(row: any) {
  detailVisible.value = true
  detail.value = null
  try {
    const r: any = await api.get(`/purchases/returns/${row.id}`)
    detail.value = r?.data ?? r ?? {}
  } catch { detail.value = null; ElMessage.error('加载详情失败') }
}

onMounted(() => { fetchData(); fetchStats() })
</script>

<style scoped>
.return-page { padding: 20px; }
.kpi-row { margin-bottom: 16px; }
.kpi-card { border-radius: 12px; border: 1px solid #e8e8ed; }
.kpi-label { font-size: 13px; color: #86868b; margin-bottom: 6px; }
.kpi-value { font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }
.filter-bar { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.detail-header { font-size: 15px; }
</style>
