<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>ECR 变更申请</span>
          <el-button type="primary" @click="openCreateDialog()">新建ECR</el-button>
        </div>
      </template>

      <!-- 筛选栏 -->
      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="5">
          <el-select v-model="filter.status" placeholder="状态" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="草稿" value="draft" />
            <el-option label="已提交" value="submitted" />
            <el-option label="评审中" value="reviewing" />
            <el-option label="已批准" value="approved" />
            <el-option label="已驳回" value="rejected" />
            <el-option label="已转ECO" value="converted" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filter.ecr_type" placeholder="变更类型" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="设计变更" value="design_change" />
            <el-option label="物料变更" value="material_change" />
            <el-option label="工艺变更" value="process_change" />
            <el-option label="认证变更" value="cert_change" />
            <el-option label="标准变更" value="standard_change" />
            <el-option label="BOM变更" value="bom_change" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="filter.urgency" placeholder="紧急度" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="紧急" value="emergency" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-input v-model="filter.keyword" placeholder="搜索标题/编号" clearable @clear="fetchData" @keyup.enter="fetchData">
            <template #append>
              <el-button @click="fetchData">搜索</el-button>
            </template>
          </el-input>
        </el-col>
      </el-row>

      <el-table :data="items" stripe border v-loading="loading" max-height="520">
        <el-table-column prop="code" label="ECR编号" width="160" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="变更类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ ecrTypeLabel(row.ecr_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="紧急度" width="80">
          <template #default="{ row }">
            <el-tag :type="urgencyType(row.urgency)" size="small">{{ urgencyLabel(row.urgency) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="submitter_name" label="提交人" width="90" />
        <el-table-column label="创建时间" width="120">
          <template #default="{ row }">{{ row.created_at?.slice(0, 10) }}</template>
        </el-table-column>
        <el-table-column label="附件" width="60" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.attachment_count > 0" size="small">{{ row.attachment_count }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewDetail(row)">详情</el-button>
            <template v-if="row.status === 'draft'">
              <el-button link type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
              <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
              <el-button link type="warning" size="small" @click="handleSubmit(row)">提交</el-button>
            </template>
            <template v-else-if="row.status === 'submitted'">
              <el-button link type="warning" size="small" @click="handleWithdraw(row)">撤回</el-button>
              <el-button link type="primary" size="small" @click="handleReview(row)">评审</el-button>
              <el-button link type="danger" size="small" @click="handleReject(row)">驳回</el-button>
            </template>
            <template v-else-if="row.status === 'reviewing'">
              <el-button link type="success" size="small" @click="handleApprove(row)">批准</el-button>
              <el-button link type="danger" size="small" @click="handleReject(row)">驳回</el-button>
            </template>
            <template v-else-if="row.status === 'approved'">
              <el-button link type="primary" size="small" @click="handleConvert(row)">转ECO</el-button>
            </template>
            <template v-else-if="row.status === 'rejected'">
              <el-button link type="warning" size="small" @click="handleResubmit(row)">重新提交</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div style="display: flex; justify-content: flex-end; margin-top: 16px">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @change="fetchData"
        />
      </div>
    </el-card>

    <!-- 创建/编辑 Dialog -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑ECR' : '新建ECR'" width="650" :close-on-click-modal="false">
      <el-form :model="form" label-width="100" :rules="formRules" ref="formRef">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入变更标题" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="变更类型" prop="ecr_type">
              <el-select v-model="form.ecr_type" style="width: 100%">
                <el-option label="设计变更" value="design_change" />
                <el-option label="物料变更" value="material_change" />
                <el-option label="工艺变更" value="process_change" />
                <el-option label="认证变更" value="cert_change" />
                <el-option label="标准变更" value="standard_change" />
                <el-option label="BOM变更" value="bom_change" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="紧急度" prop="urgency">
              <el-select v-model="form.urgency" style="width: 100%">
                <el-option label="紧急" value="emergency" />
                <el-option label="高" value="high" />
                <el-option label="中" value="medium" />
                <el-option label="低" value="low" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="变更原因" prop="reason">
          <el-input v-model="form.reason" type="textarea" :rows="2" placeholder="说明变更的原因和背景" />
        </el-form-item>
        <el-form-item label="影响产品">
          <el-input v-model="form.affected_products" placeholder="受影响的产品编码，多个以逗号分隔" />
        </el-form-item>
        <el-form-item label="影响文档">
          <el-input v-model="form.affected_documents" placeholder="受影响的文档名称，多个以逗号分隔" />
        </el-form-item>
        <el-form-item label="详细描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="详细描述变更内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 驳回原因 Dialog -->
    <el-dialog v-model="rejectDialogVisible" title="驳回ECR" width="450">
      <el-form :model="rejectForm" label-width="80">
        <el-form-item label="驳回原因" required>
          <el-input v-model="rejectForm.reason" type="textarea" :rows="3" placeholder="请填写驳回原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="rejecting" @click="confirmReject">确认驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { fetchECRs, createECR, updateECR, deleteECR, submitECR, withdrawECR, reviewECR, approveECR, rejectECR, convertToECO } from '../../api/ecr'
import type { ECROut, ECRCreate, ECRUpdate } from '../../api/ecr'

const router = useRouter()
const items = ref<ECROut[]>([])
const loading = ref(false)
const saving = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref()
const rejectDialogVisible = ref(false)
const rejectTarget = ref<number | null>(null)
const rejectForm = reactive({ reason: '' })
const rejecting = ref(false)

// 筛选条件
const filter = reactive({
  status: '',
  ecr_type: '',
  urgency: '',
  keyword: ''
})

// 表单
const form = reactive<ECRCreate>({
  title: '',
  ecr_type: 'design_change',
  reason: '',
  urgency: 'medium',
  affected_products: '',
  affected_documents: '',
  description: ''
})

// 表单验证规则
const formRules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  ecr_type: [{ required: true, message: '请选择变更类型', trigger: 'change' }],
  urgency: [{ required: true, message: '请选择紧急度', trigger: 'change' }]
}

// ====== 状态映射 ======
const statusMap: Record<string, string> = {
  draft: '草稿',
  submitted: '已提交',
  reviewing: '评审中',
  approved: '已批准',
  rejected: '已驳回',
  converted: '已转ECO'
}
const statusTypeMap: Record<string, string> = {
  draft: 'info',
  submitted: 'warning',
  reviewing: 'primary',
  approved: 'success',
  rejected: 'danger',
  converted: 'info'
}

const ecrTypeMap: Record<string, string> = {
  design_change: '设计变更',
  material_change: '物料变更',
  process_change: '工艺变更',
  cert_change: '认证变更',
  standard_change: '标准变更',
  bom_change: 'BOM变更',
  other: '其他'
}

const urgencyMap: Record<string, string> = {
  emergency: '紧急',
  high: '高',
  medium: '中',
  low: '低'
}
const urgencyTypeMap: Record<string, string> = {
  emergency: 'danger',
  high: 'warning',
  medium: 'primary',
  low: 'info'
}

function statusLabel(s: string) { return statusMap[s] || s }
function statusType(s: string) { return (statusTypeMap[s] || 'info') as any }
function ecrTypeLabel(s: string) { return ecrTypeMap[s] || s }
function urgencyLabel(s: string) { return urgencyMap[s] || s }
function urgencyType(s: string) { return (urgencyTypeMap[s] || 'info') as any }

// ====== 数据获取 ======
async function fetchData() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (filter.status) params.status = filter.status
    if (filter.ecr_type) params.ecr_type = filter.ecr_type
    if (filter.urgency) params.urgency = filter.urgency
    if (filter.keyword) params.keyword = filter.keyword
    const res = await fetchECRs(params)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

// ====== 视图操作 ======
function viewDetail(row: ECROut) {
  router.push(`/ecr/${row.id}`)
}

// ====== 创建/编辑 ======
function openCreateDialog() {
  editingId.value = null
  form.title = ''
  form.ecr_type = 'design_change'
  form.reason = ''
  form.urgency = 'medium'
  form.affected_products = ''
  form.affected_documents = ''
  form.description = ''
  dialogVisible.value = true
}

function openEditDialog(row: ECROut) {
  editingId.value = row.id
  form.title = row.title
  form.ecr_type = row.ecr_type
  form.reason = row.reason
  form.urgency = row.urgency
  form.affected_products = typeof row.affected_products === 'string' ? row.affected_products : JSON.stringify(row.affected_products || '')
  form.affected_documents = typeof row.affected_documents === 'string' ? row.affected_documents : JSON.stringify(row.affected_documents || '')
  form.description = row.description || ''
  dialogVisible.value = true
}

async function save() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const payload: ECRCreate = {
      title: form.title,
      ecr_type: form.ecr_type,
      reason: form.reason,
      urgency: form.urgency,
      affected_products: form.affected_products || undefined,
      affected_documents: form.affected_documents || undefined,
      description: form.description || undefined
    }
    if (editingId.value) {
      await updateECR(editingId.value, payload as ECRUpdate)
      ElMessage.success('更新成功')
    } else {
      await createECR(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally {
    saving.value = false
  }
}

// ====== 状态操作 ======
async function handleDelete(row: ECROut) {
  try {
    await ElMessageBox.confirm(`确定删除ECR「${row.title}」吗？`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await deleteECR(row.id)
    ElMessage.success('删除成功')
    await fetchData()
  } catch {
    // cancelled
  }
}

async function handleSubmit(row: ECROut) {
  try {
    await ElMessageBox.confirm(`确定提交ECR「${row.title}」进入审批？`, '确认提交', {
      type: 'info',
      confirmButtonText: '提交',
      cancelButtonText: '取消'
    })
    await submitECR(row.id)
    ElMessage.success('已提交审批')
    await fetchData()
  } catch {
    // cancelled
  }
}

async function handleWithdraw(row: ECROut) {
  try {
    await ElMessageBox.confirm(`确定撤回ECR「${row.title}」？`, '确认撤回', {
      type: 'warning',
      confirmButtonText: '撤回',
      cancelButtonText: '取消'
    })
    await withdrawECR(row.id)
    ElMessage.success('已撤回')
    await fetchData()
  } catch {
    // cancelled
  }
}

async function handleReview(row: ECROut) {
  try {
    await ElMessageBox.confirm(`确定开始评审ECR「${row.title}」？`, '确认评审', {
      type: 'info',
      confirmButtonText: '开始评审',
      cancelButtonText: '取消'
    })
    await reviewECR(row.id)
    ElMessage.success('已进入评审状态')
    await fetchData()
  } catch {
    // cancelled
  }
}

async function handleApprove(row: ECROut) {
  try {
    await ElMessageBox.confirm(`确定批准ECR「${row.title}」？`, '确认批准', {
      type: 'success',
      confirmButtonText: '批准',
      cancelButtonText: '取消'
    })
    await approveECR(row.id)
    ElMessage.success('已批准')
    await fetchData()
  } catch {
    // cancelled
  }
}

function handleReject(row: ECROut) {
  rejectTarget.value = row.id
  rejectForm.reason = ''
  rejectDialogVisible.value = true
}

async function confirmReject() {
  if (!rejectForm.reason.trim()) {
    ElMessage.warning('请填写驳回原因')
    return
  }
  rejecting.value = true
  try {
    await rejectECR(rejectTarget.value!, rejectForm.reason)
    ElMessage.success('已驳回')
    rejectDialogVisible.value = false
    await fetchData()
  } finally {
    rejecting.value = false
  }
}

function handleResubmit(row: ECROut) {
  handleSubmit(row)
}

async function handleConvert(row: ECROut) {
  try {
    await ElMessageBox.confirm(`确定将ECR「${row.title}」转为ECO？`, '确认转ECO', {
      type: 'info',
      confirmButtonText: '转ECO',
      cancelButtonText: '取消'
    })
    await convertToECO(row.id)
    ElMessage.success('已转为ECO')
    await fetchData()
  } catch {
    // cancelled
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
