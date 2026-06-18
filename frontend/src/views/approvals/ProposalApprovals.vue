<template>
  <div class="approvals-page">
    <el-card shadow="never">
      <template #header>
        <div class="page-header">
          <span>📝 产品立项审批</span>
        </div>
      </template>

      <!-- 筛选 -->
      <div class="filter-bar">
        <el-radio-group v-model="filterMode" @change="fetchData">
          <el-radio-button value="pending">待我审批</el-radio-button>
          <el-radio-button value="my">我提交的</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 列表 -->
      <el-table :data="items" stripe border max-height="460" v-loading="loading">
        <template #empty>
          <el-empty :description="filterMode === 'pending' ? '暂无待审批项目' : '暂无提交记录'" :image-size="80" />
        </template>
        <el-table-column prop="project_name" label="项目名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="submitter_name" label="提交人" width="100" />
        <el-table-column prop="submitted_at" label="提交时间" width="170" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="approvalTagType(row.status)" size="small">
              {{ approvalLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button type="success" size="small" @click="handleApprove(row)">✅ 通过</el-button>
              <el-button type="danger" size="small" @click="openRejectDialog(row)">❌ 驳回</el-button>
            </template>
            <el-button v-else link type="primary" size="small" @click="viewDetail(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- 驳回对话框 -->
    <el-dialog v-model="rejectDialogVisible" title="驳回意见" width="480px" :close-on-click-modal="false">
      <el-form :model="rejectForm" label-width="80px">
        <el-form-item label="驳回理由" required>
          <el-input
            v-model="rejectForm.reason"
            type="textarea"
            :rows="4"
            placeholder="请填写驳回理由（必填）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="rejecting" @click="handleReject">
          确认驳回
        </el-button>
      </template>
    </el-dialog>

    <!-- 查看详情对话框 -->
    <el-dialog v-model="detailVisible" title="项目摘要" width="560px">
      <div v-if="currentProposal" class="detail-body">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="项目名称">{{ currentProposal.project_name }}</el-descriptions-item>
          <el-descriptions-item label="提交人">{{ currentProposal.submitter_name }}</el-descriptions-item>
          <el-descriptions-item label="提交时间">{{ currentProposal.submitted_at }}</el-descriptions-item>
          <el-descriptions-item label="审批状态">
            <el-tag :type="approvalTagType(currentProposal.status)" size="small">
              {{ approvalLabel(currentProposal.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item v-if="currentProposal.reviewer_name" label="审批人">{{ currentProposal.reviewer_name }}</el-descriptions-item>
          <el-descriptions-item v-if="currentProposal.reviewed_at" label="审批时间">{{ currentProposal.reviewed_at }}</el-descriptions-item>
          <el-descriptions-item v-if="currentProposal.reason" label="驳回理由">
            <span style="color:#f56c6c">{{ currentProposal.reason }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

/* ── 筛选 ── */
const filterMode = ref('pending')  // 'pending' | 'my'

/* ── 列表与分页 ── */
const loading = ref(false)
const items = ref<any[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

/* ── 驳回 ── */
const rejectDialogVisible = ref(false)
const rejectForm = ref({ reason: '' })
const rejectTargetId = ref<number | null>(null)
const rejecting = ref(false)

/* ── 详情 ── */
const detailVisible = ref(false)
const currentProposal = ref<any>(null)

/* ── 状态映射 ── */
function approvalTagType(status: string): string {
  const map: Record<string, string> = {
    pending: 'warning', approved: 'success', rejected: 'danger'
  }
  return map[status] || 'info'
}

function approvalLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '待审批', approved: '已通过', rejected: '已驳回'
  }
  return map[status] || status
}

/* ── 获取数据 ── */
async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: currentPage.value,
      page_size: pageSize.value,
      mode: filterMode.value,
    }
    const res = await api.get('/approvals/proposals', { params })
    const data = res.data
    items.value = data.items ?? []
    total.value = data.total ?? items.value.length
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

/* ── 通过 ── */
async function handleApprove(row: any) {
  try {
    await api.post(`/approvals/${row.id}/review`, { action: 'approved' })
    ElMessage.success('已通过')
    await fetchData()
  } catch {
    // handled by interceptor
  }
}

/* ── 打开驳回对话框 ── */
function openRejectDialog(row: any) {
  rejectTargetId.value = row.id
  rejectForm.value = { reason: '' }
  rejectDialogVisible.value = true
}

/* ── 提交驳回 ── */
async function handleReject() {
  if (!rejectForm.value.reason.trim()) {
    ElMessage.warning('请填写驳回理由')
    return
  }
  rejecting.value = true
  try {
    await api.post(`/approvals/${rejectTargetId.value}/review`, {
      action: 'rejected',
      reason: rejectForm.value.reason,
    })
    ElMessage.success('已驳回')
    rejectDialogVisible.value = false
    await fetchData()
  } catch {
    // handled by interceptor
  } finally {
    rejecting.value = false
  }
}

/* ── 查看详情 ── */
function viewDetail(row: any) {
  currentProposal.value = row
  detailVisible.value = true
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.approvals-page {
  height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-bar {
  margin-bottom: 16px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.detail-body {
  max-height: 400px;
  overflow-y: auto;
}
</style>
