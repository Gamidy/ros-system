<template>
  <div class="ecr-page">
    <div class="page-header">
      <h2>工程变更申请 (ECR)</h2>
      <el-button type="primary" @click="showCreate = true">+ 新建 ECR</el-button>
    </div>

    <!-- Filters -->
    <div class="filters">
      <el-select v-model="filterStatus" placeholder="按状态筛选" clearable style="width: 160px">
        <el-option label="草稿" value="draft" />
        <el-option label="已提交" value="submitted" />
        <el-option label="审批中" value="reviewing" />
        <el-option label="已通过" value="approved" />
        <el-option label="已驳回" value="rejected" />
        <el-option label="已转换" value="converted" />
      </el-select>
      <el-select v-model="filterType" placeholder="按类型筛选" clearable style="width: 160px">
        <el-option label="设计变更" value="design_change" />
        <el-option label="工艺变更" value="process_change" />
        <el-option label="物料变更" value="material_change" />
        <el-option label="品质整改" value="quality_fix" />
        <el-option label="降本" value="cost_reduction" />
        <el-option label="法规要求" value="regulatory" />
        <el-option label="其他" value="other" />
      </el-select>
    </div>

    <!-- Table -->
    <el-table :data="ecrList" v-loading="loading" stripe>
      <el-table-column prop="code" label="编号" width="200" />
      <el-table-column prop="title" label="标题" min-width="200" />
      <el-table-column prop="ecr_type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag size="small">{{ typeLabel(row.ecr_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="urgency" label="紧急度" width="80">
        <template #default="{ row }">
          <el-tag :type="urgencyType(row.urgency)" size="small">{{ urgencyLabel(row.urgency) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="submitter_name" label="提交人" width="100" />
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ new Date(row.created_at).toLocaleString('zh-CN') }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="viewDetail(row.id)">详情</el-button>
          <el-button
            v-if="row.status === 'draft'"
            size="small"
            type="success"
            @click="submitEcr(row.id)"
          >提交</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Pagination -->
    <div class="pagination">
      <el-pagination
        v-model:current-page="page"
        :page-size="20"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchList"
      />
    </div>

    <!-- Create Dialog -->
    <el-dialog v-model="showCreate" title="新建 ECR" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="变更标题" />
        </el-form-item>
        <el-form-item label="变更类型">
          <el-select v-model="form.ecr_type" style="width: 100%">
            <el-option label="设计变更" value="design_change" />
            <el-option label="工艺变更" value="process_change" />
            <el-option label="物料变更" value="material_change" />
            <el-option label="品质整改" value="quality_fix" />
            <el-option label="降本" value="cost_reduction" />
            <el-option label="法规要求" value="regulatory" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="变更原因" required>
          <el-input v-model="form.reason" type="textarea" :rows="3" placeholder="详细描述变更原因" />
        </el-form-item>
        <el-form-item label="紧急度">
          <el-radio-group v-model="form.urgency">
            <el-radio value="critical">紧急</el-radio>
            <el-radio value="high">高</el-radio>
            <el-radio value="medium">中</el-radio>
            <el-radio value="low">低</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="详细描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="doCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- Detail Dialog -->
    <el-dialog v-model="showDetail" title="ECR 详情" width="700px">
      <el-descriptions v-if="currentEcr" :column="2" border>
        <el-descriptions-item label="编号">{{ currentEcr.code }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusType(currentEcr.status)">{{ statusLabel(currentEcr.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="标题" :span="2">{{ currentEcr.title }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ typeLabel(currentEcr.ecr_type) }}</el-descriptions-item>
        <el-descriptions-item label="紧急度">{{ urgencyLabel(currentEcr.urgency) }}</el-descriptions-item>
        <el-descriptions-item label="原因" :span="2">{{ currentEcr.reason }}</el-descriptions-item>
        <el-descriptions-item label="提交人">{{ currentEcr.submitter_name }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ new Date(currentEcr.created_at).toLocaleString('zh-CN') }}</el-descriptions-item>
        <el-descriptions-item v-if="currentEcr.rejection_reason" label="驳回原因" :span="2">
          <span style="color: #f56c6c">{{ currentEcr.rejection_reason }}</span>
        </el-descriptions-item>
      </el-descriptions>

      <!-- Actions for reviewer -->
      <div v-if="currentEcr && (currentEcr.status === 'submitted' || currentEcr.status === 'reviewing')" class="detail-actions">
        <el-input v-model="rejectionReason" type="textarea" :rows="2" placeholder="驳回原因（选填）" style="margin-bottom: 8px" />
        <el-button type="success" @click="approveEcr(currentEcr.id)">通过</el-button>
        <el-button type="danger" @click="rejectEcr(currentEcr.id)">驳回</el-button>
      </div>
      <template #footer>
        <el-button @click="showDetail = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ecrApi, type ECRItem, type ECRDetail } from '../api/ecr'

const ecrList = ref<ECRItem[]>([])
const loading = ref(false)
const creating = ref(false)
const page = ref(1)
const total = ref(0)
const filterStatus = ref('')
const filterType = ref('')
const showCreate = ref(false)
const showDetail = ref(false)
const currentEcr = ref<ECRDetail | null>(null)
const rejectionReason = ref('')
const form = ref({
  title: '',
  ecr_type: 'other',
  reason: '',
  urgency: 'medium',
  description: '',
})

onMounted(() => fetchList())
watch([filterStatus, filterType], () => { page.value = 1; fetchList() })

async function fetchList() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { skip: (page.value - 1) * 20, limit: 20 }
    if (filterStatus.value) params.status = filterStatus.value
    if (filterType.value) params.ecr_type = filterType.value
    const { data } = await ecrApi.list(params)
    ecrList.value = data as unknown as ECRItem[]
    total.value = data.length >= 20 ? (page.value * 20 + 1) : page.value * 20
  } finally {
    loading.value = false
  }
}

async function doCreate() {
  creating.value = true
  try {
    await ecrApi.create(form.value)
    ElMessage.success('ECR 创建成功')
    showCreate.value = false
    form.value = { title: '', ecr_type: 'other', reason: '', urgency: 'medium', description: '' }
    fetchList()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ElMessage.error(err?.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

async function viewDetail(id: number) {
  try {
    const { data } = await ecrApi.get(id)
    currentEcr.value = data as unknown as ECRDetail
    rejectionReason.value = ''
    showDetail.value = true
  } catch {
    ElMessage.error('加载 ECR 详情失败')
  }
}

async function submitEcr(id: number) {
  try {
    await ecrApi.submit(id)
    ElMessage.success('ECR 已提交')
    fetchList()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ElMessage.error(err?.response?.data?.detail || '提交失败')
  }
}

async function approveEcr(id: number) {
  try {
    await ecrApi.review(id, { action: 'approve' })
    ElMessage.success('ECR 已通过')
    showDetail.value = false
    fetchList()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ElMessage.error(err?.response?.data?.detail || '审批失败')
  }
}

async function rejectEcr(id: number) {
  try {
    await ecrApi.review(id, { action: 'reject', rejection_reason: rejectionReason.value })
    ElMessage.success('ECR 已驳回')
    showDetail.value = false
    fetchList()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ElMessage.error(err?.response?.data?.detail || '驳回失败')
  }
}

function typeLabel(t: string) {
  const map: Record<string, string> = {
    design_change: '设计变更', process_change: '工艺变更',
    material_change: '物料变更', quality_fix: '品质整改',
    cost_reduction: '降本', regulatory: '法规', other: '其他',
  }
  return map[t] || t
}

function urgencyLabel(u: string) {
  const map: Record<string, string> = { critical: '紧急', high: '高', medium: '中', low: '低' }
  return map[u] || u
}

function urgencyType(u: string) {
  const map: Record<string, string> = { critical: 'danger', high: 'warning', medium: 'info', low: '' }
  return map[u] || ''
}

function statusLabel(s: string) {
  const map: Record<string, string> = {
    draft: '草稿', submitted: '已提交', reviewing: '审批中',
    approved: '已通过', rejected: '已驳回', converted: '已转换',
  }
  return map[s] || s
}

function statusType(s: string) {
  const map: Record<string, string> = {
    draft: 'info', submitted: 'warning', reviewing: '',
    approved: 'success', rejected: 'danger', converted: 'success',
  }
  return map[s] || ''
}
</script>

<style scoped>
.ecr-page { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.filters { display: flex; gap: 12px; margin-bottom: 16px; }
.pagination { margin-top: 16px; display: flex; justify-content: flex-end; }
.detail-actions { margin-top: 16px; display: flex; gap: 8px; align-items: flex-start; }
.detail-actions .el-button { margin-top: 0; }
</style>
