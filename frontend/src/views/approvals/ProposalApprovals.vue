<template>
  <div class="approvals-page">
    <el-card shadow="never">
      <template #header>
        <div class="page-header">
          <span>📝 产品立项审批</span>
        </div>
      </template>

      <!-- 筛选栏: 模式 + 状态 + 搜索 -->
      <div class="filter-bar">
        <el-radio-group v-model="filterMode" @change="fetchData">
          <el-radio-button value="pending">待我审批</el-radio-button>
          <el-radio-button value="my">我提交的</el-radio-button>
        </el-radio-group>

        <div class="filter-right">
          <el-select
            v-model="filterStatus"
            placeholder="审批状态"
            clearable
            style="width: 140px"
            @change="fetchData"
          >
            <el-option label="全部" value="" />
            <el-option label="并行审批中" value="pending_parallel" />
            <el-option label="待总监终审" value="pending_director" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
          </el-select>

          <el-input
            v-model="searchKeyword"
            placeholder="搜索项目名称..."
            clearable
            style="width: 200px"
            @keyup.enter="fetchData"
            @clear="fetchData"
          >
            <template #prefix>
              <span>🔍</span>
            </template>
          </el-input>
        </div>
      </div>

      <!-- 空状态引导 -->
      <div v-if="!loading && items.length === 0" class="empty-guide">
        <div class="empty-guide-icon">📋</div>
        <h3 class="empty-guide-title">暂无待审批项</h3>
        <p class="empty-guide-desc">项目提交审批后将在此处显示</p>
        <router-link to="/pm-workspace" class="empty-guide-btn">前往工作台</router-link>
      </div>

      <!-- 列表 -->
      <template v-else>
        <el-table :data="items" stripe border max-height="460" v-loading="loading">
          <el-table-column prop="title" label="项目名称" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              <span>
                <span v-if="isOverdue(row)" class="overdue-dot" title="已逾期超过24小时">🔴</span>
                {{ row.title }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="提交时间" width="170">
            <template #default="{ row }">
              <span :class="{ 'overdue-text': isOverdue(row) }">
                {{ row.created_at || '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="approvalTagType(row.status)" size="small">
                {{ approvalLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column v-if="filterMode === 'my'" label="重新提交" width="80">
            <template #default="{ row }">
              <span v-if="row.resubmit_count">第{{ row.resubmit_count }}次</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <template v-if="canReview(row)">
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
      </template>
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

    <!-- 查看详情对话框 (含修改对比 Tab) -->
    <el-dialog v-model="detailVisible" title="审批详情" width="720px" :close-on-click-modal="false">
      <div v-if="currentProposal" class="detail-body">
        <el-tabs v-model="detailTab">
          <!-- Tab 1: 基本信息 -->
          <el-tab-pane label="📋 基本信息" name="info">
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="项目名称">{{ currentProposal.title }}</el-descriptions-item>
              <el-descriptions-item label="提交时间">{{ currentProposal.created_at || '-' }}</el-descriptions-item>
              <el-descriptions-item label="审批状态">
                <el-tag :type="approvalTagType(currentProposal.status)" size="small">
                  {{ approvalLabel(currentProposal.status) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item v-if="currentProposal.resubmit_count" label="重新提交">
                第 {{ currentProposal.resubmit_count }} 次提交
              </el-descriptions-item>
              <el-descriptions-item label="催办状态">
                <span v-if="currentProposal.reminded || currentProposal.escalated">
                  {{ currentProposal.escalated ? '已升级通知研发总监' : '已催办' }}
                </span>
                <span v-else>未催办</span>
              </el-descriptions-item>
            </el-descriptions>

            <!-- 并行审批人状态 -->
            <div v-if="currentProposal.parallel_reviewers?.length" style="margin-top: 12px">
              <h4>并行审批进度</h4>
              <el-table :data="currentProposal.parallel_reviewers" size="small" border>
                <el-table-column prop="username" label="审批人" width="120" />
                <el-table-column prop="role" label="角色" width="120" />
                <el-table-column label="状态" width="100">
                  <template #default="{ row: r }">
                    <el-tag :type="r.status === 'approved' ? 'success' : r.status === 'rejected' ? 'danger' : 'warning'" size="small">
                      {{ r.status === 'approved' ? '已通过' : r.status === 'rejected' ? '已驳回' : '待审批' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="reason" label="意见" min-width="150" show-overflow-tooltip />
              </el-table>
            </div>

            <!-- 研发总监状态 -->
            <div v-if="currentProposal.director_status" style="margin-top: 8px">
              <el-tag :type="currentProposal.director_status === 'approved' ? 'success' : currentProposal.director_status === 'rejected' ? 'danger' : 'warning'" size="small">
                研发总监: {{ currentProposal.director_status === 'approved' ? '已通过' : currentProposal.director_status === 'rejected' ? '已驳回' : '待审批' }}
              </el-tag>
              <span v-if="currentProposal.director_reason" style="margin-left: 8px; color: #f56c6c;">
                意见: {{ currentProposal.director_reason }}
              </span>
            </div>
          </el-tab-pane>

          <!-- Tab 2: 修改对比 (仅重新提交时显示) -->
          <el-tab-pane label="🔄 修改对比" name="diff" v-if="currentProposal.previous_snapshot">
            <div v-if="!currentProposal.previous_snapshot" class="text-muted">
              无修改记录（首次提交）
            </div>
            <div v-else class="diff-view">
              <div class="diff-legend">
                <span class="diff-old-legend">旧值 (上次提交)</span>
                <span class="diff-new-legend">新值 (本次提交)</span>
              </div>
              <el-table :data="diffRows" size="small" border :show-header="true">
                <el-table-column prop="field" label="字段" width="180" />
                <el-table-column label="旧值 (上次提交)" min-width="200">
                  <template #default="{ row }">
                    <span :class="{ 'diff-old': row.changed, 'diff-same': !row.changed }">
                      {{ formatDiffValue(row.oldValue) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column label="新值 (本次提交)" min-width="200">
                  <template #default="{ row }">
                    <span :class="{ 'diff-new': row.changed, 'diff-same': !row.changed }">
                      {{ formatDiffValue(row.newValue) }}
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

/* ── 筛选 ── */
const filterMode = ref('pending')  // 'pending' | 'my'
const filterStatus = ref('')
const searchKeyword = ref('')

/* ── 详情 Tab ── */
const detailTab = ref('info')

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

/* ── 修改对比数据 ── */
const diffRows = computed(() => {
  const oldSnap = currentProposal.value?.previous_snapshot
  const newSnap = currentProposal.value?.snapshot
  if (!oldSnap || !newSnap) return []

  const ignoreFields = ['id', 'code', 'created_at', 'updated_at', 'is_draft', 'status']
  const rows: any[] = []

  for (const key of Object.keys(newSnap)) {
    if (ignoreFields.includes(key)) continue
    const oldVal = oldSnap[key]
    const newVal = newSnap[key]
    const changed = JSON.stringify(oldVal) !== JSON.stringify(newVal)
    rows.push({
      field: key,
      oldValue: oldVal,
      newValue: newVal,
      changed,
    })
  }
  return rows
})

/* ── 格式化对比值 ── */
function formatDiffValue(val: any): string {
  if (val === null || val === undefined) return '-'
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

/* ── 判断是否逾期 (>24h) ── */
function isOverdue(row: any): boolean {
  if (!row.created_at) return false
  const pendingStatuses = ['pending_parallel', 'pending_director']
  if (!pendingStatuses.includes(row.status)) return false
  const created = new Date(row.created_at)
  const now = new Date()
  const hours = (now.getTime() - created.getTime()) / (1000 * 60 * 60)
  return hours > 24
}

/* ── 判断当前用户可否审批 ── */
function canReview(row: any): boolean {
  // 简化: 只要状态是 pending_parallel 或 pending_director 就显示操作按钮
  // 实际权限由后端校验
  return row.status === 'pending_parallel' || row.status === 'pending_director'
}

/* ── 状态映射 ── */
function approvalTagType(status: string): string {
  const map: Record<string, string> = {
    pending_parallel: 'warning',
    pending_director: 'warning',
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
  }
  return map[status] || 'info'
}

function approvalLabel(status: string): string {
  const map: Record<string, string> = {
    pending_parallel: '并行审批中',
    pending_director: '待总监终审',
    pending: '待审批',
    approved: '已通过',
    rejected: '已驳回',
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
    if (filterStatus.value) {
      params.status = filterStatus.value
    }
    if (searchKeyword.value.trim()) {
      params.keyword = searchKeyword.value.trim()
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
async function viewDetail(row: any) {
  try {
    const res = await api.get(`/approvals/${row.id}`)
    currentProposal.value = res.data
    detailTab.value = 'info'
    detailVisible.value = true
  } catch {
    // fallback: use row data directly
    currentProposal.value = row
    detailTab.value = 'info'
    detailVisible.value = true
  }
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
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}

.filter-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.detail-body {
  max-height: 500px;
  overflow-y: auto;
}

/* ── 逾期标记 ── */
.overdue-dot {
  margin-right: 4px;
  font-size: 12px;
}

.overdue-text {
  color: #f56c6c;
  font-weight: 500;
}

/* ── 修改对比样式 ── */
.diff-view {
  margin-top: 8px;
}

.diff-legend {
  display: flex;
  gap: 16px;
  margin-bottom: 10px;
  font-size: 13px;
}

.diff-old-legend::before {
  content: '';
  display: inline-block;
  width: 12px;
  height: 12px;
  background: #fde2e2;
  border: 1px solid #f56c6c;
  margin-right: 4px;
  vertical-align: middle;
  border-radius: 2px;
}

.diff-new-legend::before {
  content: '';
  display: inline-block;
  width: 12px;
  height: 12px;
  background: #e1f3e1;
  border: 1px solid #67c23a;
  margin-right: 4px;
  vertical-align: middle;
  border-radius: 2px;
}

.diff-old {
  background: #fde2e2;
  color: #c0392b;
  padding: 1px 4px;
  border-radius: 3px;
  display: inline-block;
  max-width: 100%;
  word-break: break-all;
}

.diff-new {
  background: #e1f3e1;
  color: #1a7a1a;
  padding: 1px 4px;
  border-radius: 3px;
  display: inline-block;
  max-width: 100%;
  word-break: break-all;
}

.diff-same {
  color: #909399;
}

.text-muted {
  color: #909399;
  padding: 20px;
  text-align: center;
}

/* ── 空状态引导 (Claude暖纸色风格) ── */
.empty-guide {
  text-align: center;
  padding: 60px 20px;
  background: #fffdf7;
  border-radius: 12px;
  border: 1px dashed #e5e0da;
}
.empty-guide-icon {
  font-size: 48px;
  margin-bottom: 16px;
  line-height: 1;
}
.empty-guide-title {
  font-size: 16px;
  color: #5e5d59;
  margin: 0 0 8px;
  font-weight: 600;
}
.empty-guide-desc {
  font-size: 13px;
  color: #87867f;
  margin: 0 0 20px;
}
.empty-guide-btn {
  display: inline-block;
  padding: 8px 24px;
  background: #d97757;
  color: #fff;
  border-radius: 10px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  transition: background 0.2s, transform 0.2s;
}
.empty-guide-btn:hover {
  background: #c96442;
  transform: translateY(-1px);
}
</style>
