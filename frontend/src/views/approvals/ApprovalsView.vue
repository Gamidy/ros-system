<template>
  <div class="page">
    <el-card shadow="never">
      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <!-- 我的审批 -->
        <el-tab-pane label="我的审批" name="pending">
          <div v-if="!loading && list.length === 0" class="empty-guide">
            <div class="empty-guide-icon">📋</div>
            <h3 class="empty-guide-title">暂无待审批项</h3>
            <p class="empty-guide-desc">项目提交审批后将在此处显示</p>
            <router-link to="/pm-workspace" class="empty-guide-btn">前往工作台</router-link>
          </div>
          <template v-else>
            <!-- 桌面端表格 -->
            <div class="desktop-table">
              <el-table :data="list" stripe border max-height="420" v-loading="loading">
                <el-table-column prop="id" label="审批编号" width="140" />
                <el-table-column prop="request_type" label="类型" width="110">
                  <template #default="{ row }">
                    <el-tag size="small">{{ typeMap[row.request_type] || row.request_type }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
                <el-table-column prop="applicant" label="申请人" width="100" />
                <el-table-column prop="status" label="状态" width="100">
                  <template #default="{ row }">
                    <el-tag :type="statusType[row.status] || 'info'" size="small">{{ statusMap[row.status] || row.status }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="submitted_at" label="提交时间" width="170" />
                <el-table-column label="操作" width="220" fixed="right">
                  <template #default="{ row }">
                    <el-button link type="primary" size="small" @click="showDetail(row)">详情</el-button>
                    <!-- TODO: 此分支将在后续版本移除 — proposal 重定向已弃用, 改为内联审批 -->
                    <template v-if="row.request_type === 'proposal'">
                      <el-button link type="primary" size="small" @click="goToProposal(row)">查看审批</el-button>
                    </template>
                    <template v-else-if="row.request_type === 'product_plan'">
                      <el-button type="success" size="small" @click="showProductPlanDialog(row)">审批</el-button>
                    </template>
                    <template v-else>
                      <el-button type="success" size="small" @click="handleApprove(row)">通过</el-button>
                      <el-button type="danger" size="small" @click="handleReject(row)">驳回</el-button>
                    </template>
                  </template>
                </el-table-column>
              </el-table>
              <div style="margin-top: 16px; display: flex; justify-content: flex-end;">
                <el-pagination
                  v-model:current-page="page"
                  v-model:page-size="pageSize"
                  :total="total"
                  :page-sizes="[10, 20, 50]"
                  layout="total, sizes, prev, pager, next, jumper"
                  @size-change="fetchList"
                  @current-change="fetchList"
                />
              </div>
            </div>
            <!-- 移动端审批卡片 -->
            <div v-if="isMobile" class="mobile-cards" v-loading="loading">
              <div
                v-for="item in list"
                :key="String(item.id)"
                class="approval-card"
                @click="openMobileDetail(item)"
              >
                <div class="card-header">
                  <span class="card-applicant">{{ (item.applicant as string) || '-' }}</span>
                  <el-tag
                    :type="(statusType[(item.status as string)] as 'warning' | 'success' | 'danger' | 'info') || 'info'"
                    size="small"
                    effect="plain"
                  >
                    {{ (statusMap[(item.status as string)] as string) || (item.status as string) || '-' }}
                  </el-tag>
                </div>
                <div class="card-title">{{ (item.title as string) || '-' }}</div>
                <div class="card-type-label">{{ (typeMap[(item.request_type as string)] as string) || (item.request_type as string) }}</div>
                <div class="card-footer">
                  <span class="card-submitted">{{ (item.submitted_at as string) || '-' }}</span>
                </div>
              </div>
              <div v-if="list.length === 0" class="empty-guide">
                <div class="empty-guide-icon">📋</div>
                <h3 class="empty-guide-title">暂无待审批项</h3>
                <p class="empty-guide-desc">项目提交审批后将在此处显示</p>
              </div>
            </div>
          </template>
        </el-tab-pane>

        <!-- 审批历史 -->
        <el-tab-pane label="审批历史" name="history">
          <div style="margin-bottom: 16px; display: flex; justify-content: space-between;">
            <el-select v-model="statusFilter" placeholder="状态筛选" clearable @change="fetchList" style="width: 160px">
              <el-option label="全部" value="" />
              <el-option label="已通过" value="approved" />
              <el-option label="已驳回" value="rejected" />
            </el-select>
            <div></div>
          </div>
          <div v-if="!loading && list.length === 0" class="empty-guide">
            <div class="empty-guide-icon">📋</div>
            <h3 class="empty-guide-title">暂无审批历史</h3>
            <p class="empty-guide-desc">完成审批的记录将在此处显示</p>
          </div>
          <template v-else>
            <!-- 桌面端表格 -->
            <div class="desktop-table">
              <el-table :data="list" stripe border max-height="420" v-loading="loading">
                <el-table-column prop="id" label="审批编号" width="140" />
                <el-table-column prop="request_type" label="类型" width="110">
                  <template #default="{ row }">
                    <el-tag size="small">{{ typeMap[row.request_type] || row.request_type }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
                <el-table-column prop="applicant" label="申请人" width="100" />
                <el-table-column prop="status" label="状态" width="100">
                  <template #default="{ row }">
                    <el-tag :type="statusType[row.status] || 'info'" size="small">{{ statusMap[row.status] || row.status }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="submitted_at" label="提交时间" width="170" />
                <el-table-column label="操作" width="100" fixed="right">
                  <template #default="{ row }">
                    <el-button link type="primary" size="small" @click="showDetail(row)">查看</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div style="margin-top: 16px; display: flex; justify-content: flex-end;">
                <el-pagination
                  v-model:current-page="page"
                  v-model:page-size="pageSize"
                  :total="total"
                  :page-sizes="[10, 20, 50]"
                  layout="total, sizes, prev, pager, next, jumper"
                  @size-change="fetchList"
                  @current-change="fetchList"
                />
              </div>
            </div>
            <!-- 移动端审批卡片 -->
            <div v-if="isMobile" class="mobile-cards">
              <div
                v-for="item in list"
                :key="String(item.id)"
                class="approval-card"
                @click="openMobileDetail(item)"
              >
                <div class="card-header">
                  <span class="card-applicant">{{ (item.applicant as string) || '-' }}</span>
                  <el-tag
                    :type="(statusType[(item.status as string)] as 'warning' | 'success' | 'danger' | 'info') || 'info'"
                    size="small"
                    effect="plain"
                  >
                    {{ (statusMap[(item.status as string)] as string) || (item.status as string) || '-' }}
                  </el-tag>
                </div>
                <div class="card-title">{{ (item.title as string) || '-' }}</div>
                <div class="card-type-label">{{ (typeMap[(item.request_type as string)] as string) || (item.request_type as string) }}</div>
                <div class="card-footer">
                  <span class="card-submitted">{{ (item.submitted_at as string) || '-' }}</span>
                </div>
              </div>
              <div v-if="list.length === 0" class="empty-guide">
                <div class="empty-guide-icon">📋</div>
                <h3 class="empty-guide-title">暂无审批历史</h3>
                <p class="empty-guide-desc">完成审批的记录将在此处显示</p>
              </div>
            </div>
          </template>
        </el-tab-pane>

        <!-- 审批链配置 -->
        <el-tab-pane label="审批链配置" name="chains">
          <el-table :data="chains" stripe border v-loading="loadingChains">
            <el-table-column prop="code" label="编号" width="140" />
            <el-table-column prop="name" label="名称" min-width="180" />
            <el-table-column label="步骤" min-width="300">
              <template #default="{ row }">
                <el-tag v-for="(s, i) in row.steps" :key="i" size="small" style="margin: 0 4px">
                  {{ s.name }}<span v-if="i < row.steps.length - 1" style="margin: 0 4px">→</span>
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="editChain(row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div style="margin-top: 16px; display: flex; justify-content: flex-end;">
            <el-button type="primary" @click="createChain">新建审批链</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 申请详情弹窗 -->
    <el-dialog v-model="detailVisible" title="申请详情" width="680px">
      <template v-if="detailItem">
        <h3 style="margin: 0 0 12px 0; color: #409eff;">申请信息</h3>
        <div class="detail-grid">
          <span class="detail-label">审批编号:</span><span>{{ detailItem.id }}</span>
          <span class="detail-label">申请类型:</span><span>{{ detailItem.request_type === 'register' ? '账号申请' : detailItem.request_type }}</span>
          <span class="detail-label">标题:</span><span>{{ detailItem.title }}</span>
          <template v-if="detailItem.applicant_info">
            <span class="detail-label">申请人:</span><span>{{ detailItem.requester }}</span>
            <span class="detail-label">真实姓名:</span><span>{{ detailItem.applicant_info.full_name || '-' }}</span>
            <span class="detail-label">部门:</span><span>{{ detailItem.applicant_info.department || '-' }}</span>
            <span class="detail-label">职位:</span><span>{{ detailItem.applicant_info.position || '-' }}</span>
            <span class="detail-label">手机号:</span><span>{{ detailItem.applicant_info.phone || '-' }}</span>
            <span class="detail-label">申请理由:</span><span>{{ detailItem.applicant_info.reason || '-' }}</span>
          </template>
          <span class="detail-label">提交时间:</span><span>{{ detailItem.created_at || '-' }}</span>
        </div>

        <!-- 审批进度可视化 -->
        <template v-if="detailItem.steps && Array.isArray(detailItem.steps) && detailItem.steps.length > 0">
          <h3 style="margin: 20px 0 12px 0; color: #409eff;">审批进度</h3>
          <ApprovalProgress
            :approval-id="Number(detailItem.id)"
            :steps="detailItem.steps as any[]"
            :current-step="Number(detailItem.current_step || 0)"
            :step-meta="(detailItem.step_meta || {}) as Record<string, any>"
            :records="(detailItem.records || []) as any[]"
            direction="vertical"
          />
        </template>
      </template>
      <template #footer>
        <el-button type="primary" size="small" @click="doApprove">✅ 通过</el-button>
        <el-button type="danger" size="small" @click="openRejectDialog">❌ 驳回</el-button>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 驳回意见弹窗 -->
    <el-dialog v-model="rejectVisible" title="驳回意见" width="450px">
      <el-form :model="rejectForm" label-width="80px">
        <el-form-item label="意见" required>
          <el-input v-model="rejectForm.opinion" type="textarea" rows="3" placeholder="请输入驳回原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="primary" :loading="rejecting" @click="doReject">确认驳回</el-button>
      </template>
    </el-dialog>

    <!-- 产品规划审批弹窗 -->
    <el-dialog v-model="productPlanVisible" :title="'产品规划审批 — ' + (productPlanItem?.title || '')" width="520px">
      <template v-if="productPlanItem">
        <div class="detail-grid">
          <span class="detail-label">产品规划名称:</span><span>{{ productPlanItem.title }}</span>
          <span class="detail-label">当前阶段:</span><span>{{ planStageLabel }}</span>
          <span class="detail-label">发起人:</span><span>{{ productPlanItem.applicant || productPlanItem.requester || '-' }}</span>
          <span class="detail-label">申请编号:</span><span>{{ productPlanItem.id }}</span>
          <span class="detail-label">提交时间:</span><span>{{ productPlanItem.submitted_at || productPlanItem.created_at || '-' }}</span>
        </div>
        <el-form style="margin-top: 16px" label-width="80px">
          <el-form-item label="审批意见">
            <el-input v-model="productPlanComment" type="textarea" rows="3" placeholder="请输入审批意见（可选）" maxlength="500" show-word-limit />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button type="danger" :loading="productPlanLoading" @click="rejectProductPlan">❌ 驳回</el-button>
        <el-button type="primary" :loading="productPlanLoading" @click="approveProductPlan">✅ 通过</el-button>
        <el-button @click="productPlanVisible = false">取消</el-button>
      </template>
    </el-dialog>

    <!-- 编辑审批链弹窗 -->
    <el-dialog v-model="chainEditVisible" :title="editingChain ? '编辑审批链' : '新建审批链'" width="600px">
      <el-form :model="chainForm" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="chainForm.name" placeholder="请输入审批链名称" />
        </el-form-item>
        <el-form-item label="步骤">
          <div v-for="(step, idx) in chainForm.steps" :key="idx" class="step-row">
            <el-input v-model="step.name" placeholder="步骤名称" style="width: 160px" />
            <el-select v-model="step.role" placeholder="审批角色" style="width: 180px">
              <el-option label="工程师" value="engineer" />
              <el-option label="模块经理" value="module_manager" />
              <el-option label="研发总监" value="rd_director" />
              <el-option label="总经理" value="general_manager" />
              <el-option label="管理员" value="admin" />
            </el-select>
            <el-button type="danger" size="small" @click="removeStep(idx)" :disabled="chainForm.steps.length <= 1">删除</el-button>
          </div>
          <el-button type="primary" size="small" @click="addStep" style="margin-top: 4px">+ 添加步骤</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="chainEditVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingChain" @click="saveChain">保存</el-button>
      </template>
    </el-dialog>

    <!-- 移动端全屏审批详情抽屉 -->
    <el-drawer
      v-model="mobileDetailVisible"
      direction="btt"
      size="100%"
      :with-header="false"
      class="mobile-detail-drawer"
    >
      <template v-if="detailItem">
        <div class="mobile-detail-header">
          <button class="mobile-detail-back" @click="mobileDetailVisible = false">✕</button>
          <span class="mobile-detail-title">审批详情</span>
        </div>
        <div class="mobile-detail-body">
          <div class="mobile-detail-section">
            <h4 class="mobile-section-title">申请信息</h4>
            <div class="mobile-detail-grid">
              <div class="mobile-detail-row">
                <span class="mobile-detail-label">审批编号</span>
                <span class="mobile-detail-value">{{ detailItem.id }}</span>
              </div>
              <div class="mobile-detail-row">
                <span class="mobile-detail-label">申请类型</span>
                <span class="mobile-detail-value">{{ (typeMap[(detailItem.request_type as string)] as string) || (detailItem.request_type as string) }}</span>
              </div>
              <div class="mobile-detail-row">
                <span class="mobile-detail-label">标题</span>
                <span class="mobile-detail-value">{{ (detailItem.title as string) || '-' }}</span>
              </div>
              <div class="mobile-detail-row">
                <span class="mobile-detail-label">申请人</span>
                <span class="mobile-detail-value">{{ (detailItem.applicant as string) || (detailItem.requester as string) || '-' }}</span>
              </div>
              <template v-if="detailItem.applicant_info">
                <div class="mobile-detail-row">
                  <span class="mobile-detail-label">真实姓名</span>
                  <span class="mobile-detail-value">{{ (detailItem.applicant_info as Record<string, string>).full_name || '-' }}</span>
                </div>
                <div class="mobile-detail-row">
                  <span class="mobile-detail-label">部门</span>
                  <span class="mobile-detail-value">{{ (detailItem.applicant_info as Record<string, string>).department || '-' }}</span>
                </div>
                <div class="mobile-detail-row">
                  <span class="mobile-detail-label">职位</span>
                  <span class="mobile-detail-value">{{ (detailItem.applicant_info as Record<string, string>).position || '-' }}</span>
                </div>
                <div class="mobile-detail-row">
                  <span class="mobile-detail-label">手机号</span>
                  <span class="mobile-detail-value">{{ (detailItem.applicant_info as Record<string, string>).phone || '-' }}</span>
                </div>
                <div class="mobile-detail-row">
                  <span class="mobile-detail-label">申请理由</span>
                  <span class="mobile-detail-value">{{ (detailItem.applicant_info as Record<string, string>).reason || '-' }}</span>
                </div>
              </template>
              <div class="mobile-detail-row">
                <span class="mobile-detail-label">提交时间</span>
                <span class="mobile-detail-value">{{ (detailItem.created_at as string) || (detailItem.submitted_at as string) || '-' }}</span>
              </div>
              <div class="mobile-detail-row">
                <span class="mobile-detail-label">状态</span>
                <span class="mobile-detail-value">
                  <el-tag
                    :type="(statusType[(detailItem.status as string)] as 'warning' | 'success' | 'danger' | 'info') || 'info'"
                    size="small"
                  >
                    {{ (statusMap[(detailItem.status as string)] as string) || (detailItem.status as string) || '-' }}
                  </el-tag>
                </span>
              </div>
            </div>
          </div>

          <!-- 审批进度 -->
          <template v-if="detailItem.steps && Array.isArray(detailItem.steps) && (detailItem.steps as unknown[]).length > 0">
            <div class="mobile-detail-section">
              <h4 class="mobile-section-title">审批进度</h4>
              <ApprovalProgress
                :approval-id="Number(detailItem.id)"
                :steps="detailItem.steps as unknown[]"
                :current-step="Number(detailItem.current_step || 0)"
                :step-meta="(detailItem.step_meta || {}) as Record<string, unknown>"
                :records="(detailItem.records || []) as unknown[]"
                direction="vertical"
              />
            </div>
          </template>
        </div>
      </template>

      <!-- 驳回输入区域 -->
      <div v-if="mobileRejectMode" class="mobile-reject-area">
        <el-input
          v-model="mobileRejectOpinion"
          type="textarea"
          :rows="3"
          placeholder="请输入驳回原因"
          maxlength="500"
          show-word-limit
        />
      </div>

      <!-- 底部固定操作按钮 -->
      <div class="mobile-detail-footer">
        <template v-if="!mobileRejectMode">
          <el-button class="mobile-btn-reject" size="large" @click="mobileRejectMode = true">驳回</el-button>
          <el-button class="mobile-btn-approve" size="large" type="primary" @click="mobileApprove()">通过</el-button>
        </template>
        <template v-else>
          <el-button class="mobile-btn-cancel" size="large" @click="mobileRejectMode = false; mobileRejectOpinion = ''">取消</el-button>
          <el-button class="mobile-btn-confirm-reject" size="large" type="danger" @click="mobileDoReject()">确认驳回</el-button>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../../api'
import ApprovalProgress from '../../components/ApprovalProgress.vue'
import type { TableRow } from '@/types/common'

const router = useRouter()

interface ChainForm {
  name: string
  steps: { name: string; role: string }[]
  id?: number
  code?: string
}

const activeTab = ref('pending')
const loading = ref(false)
const list = ref<TableRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const statusFilter = ref('')

// ── 移动端响应式状态 ──
const isMobile = ref(window.innerWidth < 768)
const mobileDetailVisible = ref(false)
const mobileRejectMode = ref(false)
const mobileRejectOpinion = ref('')
let resizeHandler: (() => void) | null = null

function onResize(): void {
  isMobile.value = window.innerWidth < 768
}

onMounted(() => {
  resizeHandler = onResize
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  if (resizeHandler) window.removeEventListener('resize', onResize)
})

const statusMap: Record<string, string> = { pending: '待审批', approved: '已通过', rejected: '已驳回' }
const statusType: Record<string, string> = { pending: 'warning', approved: 'success', rejected: 'danger' }
const typeMap: Record<string, string> = { ecr: 'ECR变更', ecn: 'ECN变更', bom: 'BOM变更', certification: '认证', proposal: '立项审批', product_plan: '产品规划' }

// Detail dialog
const detailVisible = ref(false)
const detailItem = ref<TableRow | null>(null)

// Reject dialog
const rejectVisible = ref(false)
const rejectForm = ref({ opinion: '' })
const rejecting = ref(false)

// Chain management
const chains = ref<TableRow[]>([])
const loadingChains = ref(false)
const chainEditVisible = ref(false)
const editingChain = ref<TableRow | null>(null)
const savingChain = ref(false)
const chainForm = ref<ChainForm>({ name: '', steps: [{ name: '', role: '' }] })

function resetPage() { page.value = 1; fetchList() }

async function fetchList() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize.value }
    if (activeTab.value === 'pending') {
      const res = await api.get('/approval/requests/pending', { params })
      list.value = res.data.items ?? res.data ?? []
      total.value = res.data.total ?? list.value.length
    } else {
      if (statusFilter.value) params.status = statusFilter.value
      const res = await api.get('/approval/requests', { params })
      list.value = res.data.items ?? res.data ?? []
      total.value = res.data.total ?? list.value.length
    }
  } catch { ElMessage.error('获取审批列表失败') }
  finally { loading.value = false }
}

function onTabChange() { resetPage() }

// 详情弹窗
function showDetail(row: TableRow) {
  detailItem.value = row
  detailVisible.value = true
}

// ── 移动端详情抽屉 ──
function openMobileDetail(row: TableRow): void {
  mobileRejectMode.value = false
  mobileRejectOpinion.value = ''
  detailItem.value = row
  mobileDetailVisible.value = true
}

function mobileApprove(): void {
  if (!detailItem.value) return
  const id = detailItem.value.id
  api.post(`/approval/requests/${id}/approve`)
    .then(() => {
      ElMessage.success('审批通过')
      mobileDetailVisible.value = false
      detailItem.value = null
      fetchList()
      window.dispatchEvent(new CustomEvent('approval-updated'))
    })
    .catch(() => { ElMessage.error('审批操作失败') })
}

function mobileDoReject(): void {
  if (!mobileRejectOpinion.value.trim()) {
    ElMessage.warning('请输入驳回意见')
    return
  }
  if (!detailItem.value) return
  const id = detailItem.value.id
  api.post(`/approval/requests/${id}/reject`, { opinion: mobileRejectOpinion.value })
    .then(() => {
      ElMessage.success('已驳回')
      mobileDetailVisible.value = false
      detailItem.value = null
      mobileRejectOpinion.value = ''
      fetchList()
      window.dispatchEvent(new CustomEvent('approval-updated'))
    })
    .catch(() => { ElMessage.error('驳回操作失败') })
}

// 通过
async function handleApprove(row: TableRow) {
  detailItem.value = row
  detailVisible.value = true
}
function doApprove() {
  if (!detailItem.value) return
  const id = detailItem.value.id
  api.post(`/approval/requests/${id}/approve`)
    .then(() => {
      ElMessage.success('审批通过')
      detailVisible.value = false
      detailItem.value = null
      fetchList()
      // 刷新通知计数
      window.dispatchEvent(new CustomEvent('approval-updated'))
    })
    .catch(() => { ElMessage.error('审批操作失败') })
}

// 驳回
function handleReject(row: TableRow) {
  detailItem.value = row
  openRejectDialog()
}
function openRejectDialog() {
  rejectForm.value = { opinion: '' }
  rejectVisible.value = true
}
async function doReject() {
  if (!rejectForm.value.opinion.trim()) {
    ElMessage.warning('请输入驳回意见')
    return
  }
  if (!detailItem.value) return
  rejecting.value = true
  try {
    await api.post(`/approval/requests/${detailItem.value.id}/reject`, { opinion: rejectForm.value.opinion })
    ElMessage.success('已驳回')
    rejectVisible.value = false
    detailVisible.value = false
    detailItem.value = null
    fetchList()
    window.dispatchEvent(new CustomEvent('approval-updated'))
  } catch { ElMessage.error('驳回操作失败') }
  finally { rejecting.value = false }
}

// ⚠️ 已废弃: proposal 重定向将在后续版本移除, 改为内联审批弹窗
function goToProposal(_row: TableRow) {
  router.push('/approvals/proposals')
}

// 产品规划审批弹窗
const productPlanVisible = ref(false)
const productPlanItem = ref<TableRow | null>(null)
const productPlanComment = ref('')
const productPlanLoading = ref(false)

const planStageMap: Record<string, string> = {
  draft: '草稿',
  competitor: '竞品分析',
  definition: '规格定义',
  costing: '成本核算',
  tech_input: '技术输入',
  project_init: '项目启动',
  approved: '已通过',
  released: '已发布',
}

const planStageLabel = computed(() => {
  const raw = productPlanItem.value?.stage || productPlanItem.value?.status || ''
  return planStageMap[raw] || raw || '-'
})

function showProductPlanDialog(row: TableRow) {
  productPlanItem.value = row
  productPlanComment.value = ''
  productPlanVisible.value = true
}

async function approveProductPlan() {
  if (!productPlanItem.value) return
  productPlanLoading.value = true
  try {
    await api.post(`/approval/requests/${productPlanItem.value.id}/approve`, { comment: productPlanComment.value || '' })
    ElMessage.success('审批通过')
    productPlanVisible.value = false
    productPlanItem.value = null
    productPlanComment.value = ''
    fetchList()
    window.dispatchEvent(new CustomEvent('approval-updated'))
  } catch { ElMessage.error('审批操作失败') }
  finally { productPlanLoading.value = false }
}

async function rejectProductPlan() {
  if (!productPlanItem.value) return
  productPlanLoading.value = true
  try {
    await api.post(`/approval/requests/${productPlanItem.value.id}/reject`, { opinion: productPlanComment.value || '驳回' })
    ElMessage.success('已驳回')
    productPlanVisible.value = false
    productPlanItem.value = null
    productPlanComment.value = ''
    fetchList()
    window.dispatchEvent(new CustomEvent('approval-updated'))
  } catch { ElMessage.error('驳回操作失败') }
  finally { productPlanLoading.value = false }
}

// 审批链管理
async function fetchChains() {
  loadingChains.value = true
  try {
    const res = await api.get('/approval/chains')
    chains.value = res.data ?? []
  } catch { ElMessage.error('获取审批链失败') }
  finally { loadingChains.value = false }
}

function editChain(chain: TableRow) {
  editingChain.value = chain
  chainForm.value = {
    id: chain.id,
    code: chain.code,
    name: chain.name,
    steps: (chain.steps || []).map((s: TableRow) => ({ ...s })),
  }
  chainEditVisible.value = true
}

function createChain() {
  editingChain.value = null
  chainForm.value = { name: '', steps: [{ name: '', role: '' }] }
  chainEditVisible.value = true
}

function addStep() { chainForm.value.steps.push({ name: '', role: '' }) }
function removeStep(idx: number) { chainForm.value.steps.splice(idx, 1) }

async function saveChain() {
  if (!chainForm.value.name.trim()) {
    ElMessage.warning('请输入审批链名称')
    return
  }
  savingChain.value = true
  try {
    await api.post('/approval/chains', chainForm.value)
    ElMessage.success('保存成功')
    chainEditVisible.value = false
    await fetchChains()
  } catch { ElMessage.error('保存审批链失败') }
  finally { savingChain.value = false }
}

onMounted(() => { fetchList(); fetchChains() })
</script>

<style scoped>
.detail-grid {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 8px;
  font-size: 14px;
  line-height: 28px;
}
.detail-label {
  color: #909399;
}
.step-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
}
.page {
  /* ensure consistent layout */
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

/* ═══════════════════════════════════════════
   移动端审批卡片 & 抽屉
   ═══════════════════════════════════════════ */

/* 桌面端表格默认显示，移动端隐藏 */
.desktop-table {
  display: block;
}

/* 移动端卡片列表默认隐藏 */
.mobile-cards {
  display: none;
}

/* ── 审批卡片 ── */
.approval-card {
  background: #fff;
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 10px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.2s;
  -webkit-tap-highlight-color: transparent;
  user-select: none;
}

.approval-card:active {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  transform: translateY(-1px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.card-applicant {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.card-title {
  font-size: 15px;
  color: #606266;
  line-height: 1.4;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.card-type-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-submitted {
  font-size: 12px;
  color: #c0c4cc;
}

/* ── 移动端全屏抽屉 ── */
.mobile-detail-drawer {
  z-index: 2001 !important;
}

.mobile-detail-drawer .el-drawer__body {
  padding: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.mobile-detail-header {
  display: flex;
  align-items: center;
  padding: 16px 16px 12px;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.mobile-detail-back {
  width: 32px;
  height: 32px;
  border: none;
  background: #f5f7fa;
  border-radius: 50%;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  transition: background 0.2s;
}

.mobile-detail-back:active {
  background: #e4e7ed;
}

.mobile-detail-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.mobile-detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  padding-bottom: 140px; /* space for footer + reject area */
}

.mobile-detail-section {
  margin-bottom: 20px;
}

.mobile-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #409eff;
  margin: 0 0 12px;
}

.mobile-detail-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mobile-detail-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.mobile-detail-label {
  font-size: 13px;
  color: #909399;
  flex-shrink: 0;
  min-width: 60px;
}

.mobile-detail-value {
  font-size: 13px;
  color: #303133;
  text-align: right;
  word-break: break-all;
}

/* 驳回输入区域 */
.mobile-reject-area {
  flex-shrink: 0;
  padding: 12px 16px;
  border-top: 1px solid #ebeef5;
  background: #fff;
}

/* 底部固定操作按钮 */
.mobile-detail-footer {
  flex-shrink: 0;
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  padding-bottom: calc(12px + env(safe-area-inset-bottom, 8px));
  border-top: 1px solid #ebeef5;
  background: #fff;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.06);
}

.mobile-detail-footer .el-button {
  flex: 1;
  border-radius: 8px;
  font-weight: 500;
}

.mobile-btn-reject {
  color: #f56c6c !important;
  border-color: #f56c6c !important;
}

.mobile-btn-approve {
  background: #409eff !important;
}

.mobile-btn-cancel {
  color: #909399 !important;
  border-color: #dcdfe6 !important;
}

.mobile-btn-confirm-reject {
  background: #f56c6c !important;
  border-color: #f56c6c !important;
}

/* ── 响应式媒体查询 ── */
@media (max-width: 767px) {
  .desktop-table {
    display: none;
  }

  .mobile-cards {
    display: block;
  }
}
</style>
