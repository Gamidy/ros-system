<template>
  <div class="page">
    <!-- 返回按钮 -->
    <el-button style="margin-bottom: 12px" @click="$router.push('/ecr')">← 返回ECR列表</el-button>

    <!-- 基本信息 -->
    <el-card shadow="never" style="margin-bottom: 16px">
      <template #header>
        <div class="card-header">
          <span>ECR 基本信息</span>
          <div>
            <template v-if="detail.status === 'draft'">
              <el-button size="small" @click="openEditDialog">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete">删除</el-button>
              <el-button size="small" type="warning" @click="handleSubmit">提交审批</el-button>
            </template>
            <template v-else-if="detail.status === 'submitted'">
              <el-button size="small" @click="handleWithdraw">撤回</el-button>
              <el-button size="small" type="primary" @click="handleReview">开始评审</el-button>
              <el-button size="small" type="danger" @click="handleReject">驳回</el-button>
            </template>
            <template v-else-if="detail.status === 'reviewing'">
              <el-button size="small" type="success" @click="handleApprove">批准</el-button>
              <el-button size="small" type="danger" @click="handleReject">驳回</el-button>
            </template>
            <template v-else-if="detail.status === 'approved'">
              <el-button size="small" type="primary" @click="handleConvert">转ECO</el-button>
            </template>
            <template v-else-if="detail.status === 'rejected'">
              <el-button size="small" type="warning" @click="handleResubmit">重新提交</el-button>
            </template>
          </div>
        </div>
      </template>

      <el-descriptions :column="3" border v-loading="loading">
        <el-descriptions-item label="ECR编号" width="160">{{ detail.code }}</el-descriptions-item>
        <el-descriptions-item label="标题">{{ detail.title }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusType(detail.status)" size="small">{{ statusLabel(detail.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="变更类型">
          <el-tag size="small">{{ ecrTypeLabel(detail.ecr_type) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="紧急度">
          <el-tag :type="urgencyType(detail.urgency)" size="small">{{ urgencyLabel(detail.urgency) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="提交人">{{ detail.submitter_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="变更原因" :span="3">{{ detail.reason || '-' }}</el-descriptions-item>
        <el-descriptions-item label="影响产品" :span="3">{{ formatAffected(detail.affected_products) }}</el-descriptions-item>
        <el-descriptions-item label="影响文档" :span="3">{{ formatAffected(detail.affected_documents) }}</el-descriptions-item>
        <el-descriptions-item label="详细描述" :span="3">{{ detail.description || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ detail.created_at?.slice(0, 16) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ detail.updated_at?.slice(0, 16) }}</el-descriptions-item>
        <el-descriptions-item label="附件数量">{{ detail.attachment_count }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 关联ECO（已转ECO时显示） -->
    <el-card v-if="detail.eco_id" shadow="never" style="margin-bottom: 16px">
      <template #header>
        <div class="card-header">
          <span>关联ECO</span>
        </div>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="ECO编号">{{ detail.eco_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="ECO状态">
          <el-tag v-if="detail.eco_status" size="small">{{ detail.eco_status }}</el-tag>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="操作">
          <el-button v-if="detail.eco_id" link type="primary" size="small" @click="$router.push(`/eco/${detail.eco_id}`)">查看详情</el-button>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 状态时间线 -->
    <el-card shadow="never" style="margin-bottom: 16px">
      <template #header>
        <div class="card-header">
          <span>状态流转</span>
        </div>
      </template>
      <el-timeline>
        <el-timeline-item
          v-for="(step, idx) in statusSteps"
          :key="idx"
          :timestamp="step.time"
          :type="step.type"
          :hollow="step.hollow"
          :color="step.color"
        >
          {{ step.label }}
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <!-- 附件列表 -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>附件 ({{ detail.attachments?.length || 0 }})</span>
        </div>
      </template>
      <el-table :data="detail.attachments || []" stripe border v-loading="loading">
        <el-table-column prop="file_name" label="文件名" min-width="200" />
        <el-table-column prop="file_type" label="类型" width="100" />
        <el-table-column label="大小" width="100">
          <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column prop="uploaded_by" label="上传人" width="100" />
        <el-table-column label="上传时间" width="160">
          <template #default="{ row }">{{ row.created_at?.slice(0, 16) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="downloadAttachment(row)">下载</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!detail.attachments?.length" description="暂无附件" :image-size="60" style="padding: 24px" />
    </el-card>

    <!-- 编辑 Dialog -->
    <el-dialog v-model="editDialogVisible" title="编辑ECR" width="650" :close-on-click-modal="false">
      <el-form :model="editForm" label-width="100" :rules="formRules" ref="editFormRef">
        <el-form-item label="标题" prop="title">
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="变更类型" prop="ecr_type">
              <el-select v-model="editForm.ecr_type" style="width: 100%">
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
              <el-select v-model="editForm.urgency" style="width: 100%">
                <el-option label="紧急" value="emergency" />
                <el-option label="高" value="high" />
                <el-option label="中" value="medium" />
                <el-option label="低" value="low" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="变更原因" prop="reason">
          <el-input v-model="editForm.reason" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="影响产品">
          <el-input v-model="editForm.affected_products" placeholder="受影响的产品编码，多个以逗号分隔" />
        </el-form-item>
        <el-form-item label="影响文档">
          <el-input v-model="editForm.affected_documents" placeholder="受影响的文档名称，多个以逗号分隔" />
        </el-form-item>
        <el-form-item label="详细描述">
          <el-input v-model="editForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 驳回 Dialog -->
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
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchECR, updateECR, deleteECR, submitECR, withdrawECR,
  reviewECR, approveECR, rejectECR, convertToECO
} from '../../api/ecr'
import type { ECRDetailOut, ECRUpdate } from '../../api/ecr'

const route = useRoute()
const ecrId = computed(() => Number(route.params.id))

const detail = ref<ECRDetailOut>({} as ECRDetailOut)
const loading = ref(false)
const saving = ref(false)

const editDialogVisible = ref(false)
const editFormRef = ref()
const editForm = reactive({
  title: '',
  ecr_type: 'design_change',
  reason: '',
  urgency: 'medium',
  affected_products: '',
  affected_documents: '',
  description: ''
})

const rejectDialogVisible = ref(false)
const rejectForm = reactive({ reason: '' })
const rejecting = ref(false)

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
function statusType(s: string): string { return statusTypeMap[s] || 'info' }
function ecrTypeLabel(s: string) { return ecrTypeMap[s] || s }
function urgencyLabel(s: string) { return urgencyMap[s] || s }
function urgencyType(s: string): string { return urgencyTypeMap[s] || 'info' }

// ====== 状态时间线 ======
const statusSteps = computed(() => {
  const steps: Array<{ label: string; time: string; type: string; hollow?: boolean; color?: string }> = []
  const d = detail.value

  if (d.created_at) {
    steps.push({
      label: '创建草稿',
      time: d.created_at,
      type: 'info'
    })
  }

  // 根据状态构建流转
  const statusOrder = ['submitted', 'reviewing', 'approved', 'rejected', 'converted']
  const currentIdx = statusOrder.indexOf(d.status)
  for (let i = 0; i <= currentIdx; i++) {
    const s = statusOrder[i]
    if (s === 'approved') {
      steps.push({
        label: statusLabel(s),
        time: d.updated_at || d.created_at,
        type: 'success'
      })
    } else if (s === 'rejected') {
      steps.push({
        label: statusLabel(s),
        time: d.updated_at || d.created_at,
        type: 'danger'
      })
    } else {
      steps.push({
        label: statusLabel(s),
        time: d.updated_at || d.created_at,
        type: 'primary'
      })
    }
  }

  if (d.status === 'converted') {
    steps.push({
      label: '已转ECO' + (d.eco_code ? ` (${d.eco_code})` : ''),
      time: d.updated_at || d.created_at,
      type: 'primary'
    })
  }

  return steps
})

// ====== 工具函数 ======
function formatAffected(val: unknown): string {
  if (!val) return '-'
  if (typeof val === 'string') return val
  try { return JSON.stringify(val) } catch { return String(val) }
}

function formatFileSize(bytes: number): string {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function downloadAttachment(row: Record<string, unknown>) {
  window.open(row.file_path as string, '_blank')
}

// ====== 数据获取 ======
async function fetchDetail() {
  loading.value = true
  try {
    const res = await fetchECR(ecrId.value)
    detail.value = res
  } finally {
    loading.value = false
  }
}

// ====== 编辑 ======
function openEditDialog() {
  const d = detail.value
  editForm.title = d.title
  editForm.ecr_type = d.ecr_type
  editForm.reason = d.reason
  editForm.urgency = d.urgency
  editForm.affected_products = typeof d.affected_products === 'string' ? d.affected_products : JSON.stringify(d.affected_products || '')
  editForm.affected_documents = typeof d.affected_documents === 'string' ? d.affected_documents : JSON.stringify(d.affected_documents || '')
  editForm.description = d.description || ''
  editDialogVisible.value = true
}

async function saveEdit() {
  if (!editFormRef.value) return
  const valid = await editFormRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const payload: ECRUpdate = {
      title: editForm.title,
      ecr_type: editForm.ecr_type,
      reason: editForm.reason,
      urgency: editForm.urgency,
      affected_products: editForm.affected_products || undefined,
      affected_documents: editForm.affected_documents || undefined,
      description: editForm.description || undefined
    }
    await updateECR(ecrId.value, payload)
    ElMessage.success('更新成功')
    editDialogVisible.value = false
    await fetchDetail()
  } finally {
    saving.value = false
  }
}

// ====== 状态操作 ======
async function handleDelete() {
  try {
    await ElMessageBox.confirm(`确定删除ECR「${detail.value.title}」吗？`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await deleteECR(ecrId.value)
    ElMessage.success('删除成功')
    window.history.back()
  } catch {
    // cancelled
  }
}

async function handleSubmit() {
  try {
    await ElMessageBox.confirm(`确定提交ECR「${detail.value.title}」进入审批？`, '确认提交', {
      type: 'info',
      confirmButtonText: '提交',
      cancelButtonText: '取消'
    })
    await submitECR(ecrId.value)
    ElMessage.success('已提交审批')
    await fetchDetail()
  } catch {
    // cancelled
  }
}

async function handleWithdraw() {
  try {
    await ElMessageBox.confirm(`确定撤回ECR「${detail.value.title}」？`, '确认撤回', {
      type: 'warning',
      confirmButtonText: '撤回',
      cancelButtonText: '取消'
    })
    await withdrawECR(ecrId.value)
    ElMessage.success('已撤回')
    await fetchDetail()
  } catch {
    // cancelled
  }
}

async function handleReview() {
  try {
    await ElMessageBox.confirm(`确定开始评审ECR「${detail.value.title}」？`, '确认评审', {
      type: 'info',
      confirmButtonText: '开始评审',
      cancelButtonText: '取消'
    })
    await reviewECR(ecrId.value)
    ElMessage.success('已进入评审状态')
    await fetchDetail()
  } catch {
    // cancelled
  }
}

async function handleApprove() {
  try {
    await ElMessageBox.confirm(`确定批准ECR「${detail.value.title}」？`, '确认批准', {
      type: 'success',
      confirmButtonText: '批准',
      cancelButtonText: '取消'
    })
    await approveECR(ecrId.value)
    ElMessage.success('已批准')
    await fetchDetail()
  } catch {
    // cancelled
  }
}

function handleReject() {
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
    await rejectECR(ecrId.value, rejectForm.reason)
    ElMessage.success('已驳回')
    rejectDialogVisible.value = false
    await fetchDetail()
  } finally {
    rejecting.value = false
  }
}

function handleResubmit() {
  handleSubmit()
}

async function handleConvert() {
  try {
    await ElMessageBox.confirm(`确定将ECR「${detail.value.title}」转为ECO？`, '确认转ECO', {
      type: 'info',
      confirmButtonText: '转ECO',
      cancelButtonText: '取消'
    })
    await convertToECO(ecrId.value)
    ElMessage.success('已转为ECO')
    await fetchDetail()
  } catch {
    // cancelled
  }
}

onMounted(fetchDetail)
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
