<template>
  <div class="supplier-page">
    <!-- KPI 卡片 -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">供应商总数</div>
          <div class="kpi-value">{{ stats.total_count ?? '-' }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">合格/合作中</div>
          <div class="kpi-value" style="color:#67c23a">{{ (stats.qualified_count ?? 0) + (stats.active_count ?? 0) }}</div>
          <div class="kpi-unit">品类: {{ stats.category_count ?? 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">平均评分</div>
          <div class="kpi-value" :style="{ color: scoreColor(stats.avg_score) }">{{ stats.avg_score ?? '-' }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">低分预警(&lt;60)</div>
          <div class="kpi-value" :style="{ color: (stats.low_score_count ?? 0) > 0 ? '#f56c6c' : '#67c23a' }">{{ stats.low_score_count ?? 0 }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input v-model="keyword" placeholder="搜索名称/编码/联系人" clearable style="width:220px" @clear="fetchSuppliers" @keyup.enter="fetchSuppliers" />
      <el-select v-model="filterStatus" placeholder="状态" clearable style="width:140px" @change="fetchSuppliers">
        <el-option label="潜在" value="potential" />
        <el-option label="合格" value="qualified" />
        <el-option label="合作中" value="active" />
        <el-option label="暂停" value="suspended" />
        <el-option label="黑名单" value="blacklisted" />
      </el-select>
      <el-select v-model="filterCategory" placeholder="品类" clearable style="width:140px" @change="fetchSuppliers">
        <el-option v-for="c in categories" :key="c.category" :label="c.category" :value="c.category" />
      </el-select>
      <el-button type="primary" @click="fetchSuppliers">查询</el-button>
      <el-button type="success" @click="openAdd">+ 新增供应商</el-button>
    </div>

    <!-- 供应商表格 -->
    <el-table :data="suppliers" border stripe v-loading="loading" style="width:100%">
      <el-table-column type="index" width="40" label="#" />
      <el-table-column prop="code" label="编码" width="100" sortable />
      <el-table-column prop="name" label="供应商名称" min-width="140" sortable />
      <el-table-column prop="category" label="品类" width="100" />
      <el-table-column prop="contact" label="联系人" width="90" />
      <el-table-column prop="phone" label="电话" width="120" />
      <el-table-column label="评分" width="80" sortable sortable-prop="overall_score">
        <template #default="{ row }">
          <el-tag :type="scoreTagType(row.overall_score)" size="small">{{ row.overall_score ?? '-' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="认证" width="100">
        <template #default="{ row }">
          <span v-if="row.cert_iso" class="cert-badge">ISO</span>
          <span v-if="row.cert_rohs" class="cert-badge">RoHS</span>
          <span v-if="row.cert_ul" class="cert-badge">UL</span>
          <span v-if="!row.cert_iso && !row.cert_rohs && !row.cert_ul" class="no-cert">-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="openEval(row)">评估</el-button>
          <el-button size="small" type="primary" link @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确认删除？" @confirm="doDelete(row.id)">
            <template #reference>
              <el-button size="small" type="danger" link>删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="formVisible" :title="isEdit ? '编辑供应商' : '新增供应商'" width="640px" destroy-on-close>
      <el-form :model="form" label-width="100px" size="small">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="编码" required>
              <el-input v-model="form.code" placeholder="自动或手动输入" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="名称" required>
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="品类">
              <el-select v-model="form.category" placeholder="选择品类" clearable style="width:100%">
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
              <el-select v-model="form.status" style="width:100%">
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
            <el-form-item label="联系人"><el-input v-model="form.contact" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="电话"><el-input v-model="form.phone" /></el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
        <el-form-item label="地址"><el-input v-model="form.address" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="税号"><el-input v-model="form.tax_id" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="银行信息"><el-input v-model="form.bank_info" /></el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="认证">
          <el-checkbox v-model="form.cert_iso" :true-value="1" :false-value="0">ISO</el-checkbox>
          <el-checkbox v-model="form.cert_rohs" :true-value="1" :false-value="0">RoHS</el-checkbox>
          <el-checkbox v-model="form.cert_ul" :true-value="1" :false-value="0">UL</el-checkbox>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" @click="doSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 评估弹窗 -->
    <el-dialog v-model="evalVisible" title="供应商评估" width="600px" destroy-on-close>
      <template v-if="evalSupplier">
        <div class="eval-header">
          <strong>{{ evalSupplier.name }}</strong> ({{ evalSupplier.code }})
          <el-tag :type="scoreTagType(evalSupplier.overall_score)" style="margin-left:12px">
            当前综合评分: {{ evalSupplier.overall_score ?? '未评' }}
          </el-tag>
        </div>

        <!-- 已有评估记录 -->
        <el-table :data="evalRecords" border size="small" style="width:100%;margin-top:12px" max-height="200">
          <el-table-column prop="dimension_label" label="维度" width="80" />
          <el-table-column prop="score" label="评分" width="70" sortable>
            <template #default="{ row }">
              <el-tag :type="scoreTagType(row.score)" size="small">{{ row.score }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="comment" label="意见" min-width="120" show-overflow-tooltip />
          <el-table-column prop="evaluator" label="评估人" width="80" />
          <el-table-column prop="evaluated_at" label="时间" width="90">
            <template #default="{ row }">{{ formatDate(row.evaluated_at) }}</template>
          </el-table-column>
        </el-table>

        <!-- 新增评估 -->
        <el-divider />
        <div class="eval-form-title">新增评估</div>
        <el-form :model="evalForm" label-width="80px" size="small">
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="维度">
                <el-select v-model="evalForm.dimension" style="width:100%">
                  <el-option label="品质" value="quality" />
                  <el-option label="交期" value="delivery" />
                  <el-option label="成本" value="cost" />
                  <el-option label="服务" value="service" />
                  <el-option label="技术能力" value="technology" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="评分">
                <el-input-number v-model="evalForm.score" :min="0" :max="100" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="权重">
                <el-input-number v-model="evalForm.weight" :min="0" :max="1" :step="0.05" style="width:100%" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="意见">
            <el-input v-model="evalForm.comment" />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="evalVisible = false">关闭</el-button>
        <el-button type="primary" @click="doEval">提交评估</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listSuppliers, getSupplier, createSupplier, updateSupplier, deleteSupplier, listEvaluations, createEvaluation, getSupplierStats, getSupplierCategories } from '../../api/purchase'
import { ElMessage } from 'element-plus'

/* ── 类型 ── */
interface SupplierItem {
  id: number; code: string; name: string; category?: string
  contact?: string; phone?: string; email?: string; address?: string
  tax_id?: string; bank_info?: string; status: string; overall_score: number
  cert_iso: number; cert_rohs: number; cert_ul: number
  remark?: string
}
interface StatsData {
  total_count: number; qualified_count: number; active_count: number
  suspended_count: number; blacklisted_count: number
  avg_score: number; low_score_count: number; category_count: number
}
interface EvalRecord {
  id: number; dimension: string; dimension_label: string
  score: number; weight: number; comment?: string
  evaluator?: string; evaluated_at: string
}

/* ── 状态 ── */
const loading = ref(false)
const suppliers = ref<SupplierItem[]>([])
const stats = ref<StatsData>({} as StatsData)
const categories = ref<{ category: string; count: number }[]>([])
const keyword = ref('')
const filterStatus = ref('')
const filterCategory = ref('')

/* ── 表单 ── */
const formVisible = ref(false)
const isEdit = ref(false)
const editId = ref(0)
const form = ref<Record<string, any>>({
  code: '', name: '', category: '', status: 'potential',
  contact: '', phone: '', email: '', address: '',
  tax_id: '', bank_info: '', cert_iso: 0, cert_rohs: 0, cert_ul: 0,
  remark: '',
})

/* ── 评估 ── */
const evalVisible = ref(false)
const evalSupplier = ref<SupplierItem | null>(null)
const evalRecords = ref<EvalRecord[]>([])
const evalForm = ref({ dimension: 'quality', score: 80, weight: 1.0, comment: '' })

/* ── 辅助 ── */
function scoreColor(s: number | undefined): string {
  if (s == null) return '#909399'
  if (s >= 80) return '#67c23a'
  if (s >= 60) return '#e6a23c'
  return '#f56c6c'
}
function scoreTagType(s: number | undefined): string {
  if (s == null) return 'info'
  if (s >= 80) return 'success'
  if (s >= 60) return 'warning'
  return 'danger'
}
function statusTagType(s: string): string {
  const map: Record<string, string> = { potential: 'info', qualified: 'success', active: 'success', suspended: 'warning', blacklisted: 'danger' }
  return map[s] || 'info'
}
function statusLabel(s: string): string {
  const map: Record<string, string> = { potential: '潜在', qualified: '合格', active: '合作中', suspended: '暂停', blacklisted: '黑名单' }
  return map[s] || s
}
function formatDate(d: string): string {
  if (!d) return '-'
  return d.substring(0, 10)
}

/* ── 数据加载 ── */
async function fetchSuppliers() {
  loading.value = true
  try {
    const params: Record<string, any> = { sort_by: 'overall_score', sort_order: 'desc' }
    if (keyword.value) params.keyword = keyword.value
    if (filterStatus.value) params.status = filterStatus.value
    if (filterCategory.value) params.category = filterCategory.value
    const res: any = await listSuppliers(params)
    suppliers.value = (res?.data ?? res ?? []) as SupplierItem[]
  } catch { suppliers.value = [] }
  finally { loading.value = false }
}

async function fetchStats() {
  try {
    const res: any = await getSupplierStats()
    stats.value = (res?.data ?? res ?? {}) as StatsData
  } catch { stats.value = {} as StatsData }
  try {
    const res2: any = await getSupplierCategories()
    categories.value = (res2?.data ?? res2 ?? []) as { category: string; count: number }[]
  } catch { categories.value = [] }
}

/* ── CRUD ── */
function openAdd() {
  isEdit.value = false; editId.value = 0
  form.value = { code: '', name: '', category: '', status: 'potential', contact: '', phone: '', email: '', address: '', tax_id: '', bank_info: '', cert_iso: 0, cert_rohs: 0, cert_ul: 0, remark: '' }
  formVisible.value = true
}
function openEdit(row: SupplierItem) {
  isEdit.value = true; editId.value = row.id
  form.value = { ...row }
  formVisible.value = true
}
async function doSave() {
  try {
    if (isEdit.value) {
      await updateSupplier(editId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await createSupplier(form.value)
      ElMessage.success('创建成功')
    }
    formVisible.value = false
    fetchSuppliers(); fetchStats()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}
async function doDelete(id: number) {
  try {
    await deleteSupplier(id)
    ElMessage.success('已删除')
    fetchSuppliers(); fetchStats()
  } catch { ElMessage.error('删除失败') }
}

/* ── 评估 ── */
async function openEval(row: SupplierItem) {
  evalSupplier.value = row
  evalForm.value = { dimension: 'quality', score: 80, weight: 1.0, comment: '' }
  evalVisible.value = true
  try {
    const res: any = await listEvaluations(row.id)
    evalRecords.value = (res?.data ?? res ?? []) as EvalRecord[]
  } catch { evalRecords.value = [] }
}
async function doEval() {
  if (!evalSupplier.value) return
  const data = { ...evalForm.value, evaluator: '当前用户' }
  try {
    await createEvaluation(evalSupplier.value.id, data)
    ElMessage.success('评估已提交')
    // 刷新
    const res: any = await listEvaluations(evalSupplier.value.id)
    evalRecords.value = (res?.data ?? res ?? []) as EvalRecord[]
    const supRes: any = await getSupplier(evalSupplier.value.id)
    if (evalSupplier.value) evalSupplier.value.overall_score = (supRes?.data ?? supRes)?.overall_score ?? 0
    fetchSuppliers(); fetchStats()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '评估提交失败')
  }
}

onMounted(() => { fetchSuppliers(); fetchStats() })
</script>

<style scoped>
.supplier-page { padding: 20px; }
.kpi-row { margin-bottom: 16px; }
.kpi-card { border-radius: 12px; border: 1px solid #e8e8ed; }
.kpi-label { font-size: 13px; color: #86868b; margin-bottom: 6px; }
.kpi-value { font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }
.kpi-unit { font-size: 12px; color: #86868b; margin-top: 2px; }
.filter-bar { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
.cert-badge { display: inline-block; background: #ecf5ff; color: #409eff; border-radius: 4px; padding: 0 6px; margin-right: 4px; font-size: 12px; }
.no-cert { color: #c0c4cc; }
.eval-header { padding: 8px 0; font-size: 15px; }
.eval-form-title { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 8px; }
</style>
