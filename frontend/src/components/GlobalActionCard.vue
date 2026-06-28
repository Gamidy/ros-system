<template>
  <div class="global-action-card">
    <!-- ═══════ Card Header ═══════ -->
    <div class="card-header">
      <div class="card-header-left">
        <el-icon :size="18" class="card-header-icon"><List /></el-icon>
        <h3 class="card-title">{{ title }}</h3>
      </div>
      <div class="card-header-right">
        <span v-if="!loading && !error" class="card-count">{{ displayItems.length }} 项待办</span>
        <el-tooltip content="刷新">
          <el-button
            :icon="Refresh"
            size="small"
            circle
            plain
            :loading="loading"
            @click="fetchActions"
          />
        </el-tooltip>
      </div>
    </div>

    <!-- ═══════ Loading State ═══════ -->
    <div v-if="loading" class="card-body card-loading">
      <el-skeleton :rows="3" animated>
        <template #template>
          <div class="skeleton-item">
            <el-skeleton-item variant="circle" style="width: 32px; height: 32px" />
            <div style="flex: 1">
              <el-skeleton-item variant="text" style="width: 40%; margin-bottom: 6px" />
              <el-skeleton-item variant="text" style="width: 70%; height: 14px" />
            </div>
          </div>
        </template>
      </el-skeleton>
    </div>

    <!-- ═══════ Error State ═══════ -->
    <div v-else-if="error" class="card-body card-error">
      <el-icon :size="36" color="var(--el-color-danger)"><WarningFilled /></el-icon>
      <p class="error-text">数据加载失败</p>
      <p class="error-hint">请检查网络后重试</p>
      <el-button size="small" type="primary" @click="fetchActions">重新加载</el-button>
    </div>

    <!-- ═══════ Empty State ═══════ -->
    <div v-else-if="filteredItems.length === 0" class="card-body card-empty">
      <el-icon :size="40" class="empty-icon"><CircleCheckFilled /></el-icon>
      <p class="empty-title">太棒了，暂无待办事项！</p>
      <p class="empty-desc">{{ randomCheer }}</p>
    </div>

    <!-- ═══════ Action List ═══════ -->
    <div v-else class="card-body card-list">
      <div
        v-for="item in displayItems"
        :key="item.id"
        class="action-item"
        :class="`action--${item.cardType}`"
        @click="navigateTo(item)"
      >
        <!-- Left Icon -->
        <div class="action-icon" :class="`icon--${item.cardType}`">
          <el-icon :size="18">
            <component :is="typeIcon(item.cardType)" />
          </el-icon>
        </div>

        <!-- Content -->
        <div class="action-content">
          <div class="action-title-row">
            <span class="action-title">{{ item.title }}</span>
            <el-tag
              :type="priorityTagType(item.priority)"
              size="small"
              effect="plain"
              class="action-priority"
            >
              {{ priorityLabel(item.priority) }}
            </el-tag>
          </div>
          <div class="action-desc">{{ item.description }}</div>
          <div class="action-meta">
            <span class="action-plan-name">{{ item.planName }}</span>
            <span v-if="item.deadline" class="action-deadline" :class="{ overdue: isOverdue(item.deadline) }">
              <el-icon :size="12"><Clock /></el-icon>
              {{ countdownLabel(item.deadline) }}
            </span>
          </div>
        </div>

        <!-- Arrow -->
        <div class="action-arrow">
          <el-icon :size="14" color="var(--el-text-color-placeholder)"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- ═══════ Footer (more items indicator) ═══════ -->
    <div v-if="hasMoreItems" class="card-footer">
      <el-button link type="primary" size="small" @click="$emit('view-all')">
        查看全部 {{ filteredItems.length }} 项待办
        <el-icon :size="12"><ArrowRight /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  List,
  Refresh,
  WarningFilled,
  CircleCheckFilled,
  ArrowRight,
  Clock,
} from '@element-plus/icons-vue'
import api from '../api'

// ── Types ──
type CardType = 'blocking' | 'advancing' | 'reminding'
type Priority = 'urgent' | 'important' | 'normal'

interface ActionItem {
  id: string
  cardType: CardType
  priority: Priority
  title: string
  description: string
  planName: string
  planId: string
  deadline: string | null // ISO date string
  route: string
}

/** API 返回的策划数据（product-plan） */
interface PlanAction {
  id: number | string
  name: string
  status?: string
  stage?: string
  deadline?: string
  target_end_date?: string
  target_date?: string
  approval_status?: string
}

/** API 返回的审批请求数据（approval request） */
interface ApprovalRequest {
  id?: number | string
  request_id?: string
  status?: string
  plan_name?: string
  title?: string
  plan_id?: number | string
  deadline?: string
  created_at?: string
}

// ── Props ──
const props = withDefaults(defineProps<{
  title?: string
  maxItems?: number
}>(), {
  title: '策划待办',
  maxItems: 5,
})

// ── Emits ──
defineEmits<{
  'view-all': []
  'item-click': [item: ActionItem]
}>()

// ── State ──
const router = useRouter()
const loading = ref(false)
const error = ref(false)
const plans = ref<PlanAction[]>([])
const approvals = ref<ApprovalRequest[]>([])

// ── Encouraging messages ──
const cheerMessages = [
  '所有产品策划都在正常推进，继续保持！🎉',
  '当前没有积压待办，真高效！✨',
  '一切井然有序，值得表扬！👏',
  '无待办事项，可以专注于更重要的工作 💪',
  '所有任务已处理完毕，享受片刻宁静 😊',
]
const randomCheer = computed(() => {
  const idx = Math.floor(Math.random() * cheerMessages.length)
  return cheerMessages[idx]
})

// ── Compute action items from API data ──
function computeActions(): ActionItem[] {
  const items: ActionItem[] = []

  // 1. Map plans to action items
  for (const plan of plans.value) {
    const planActions = mapPlanToActions(plan)
    items.push(...planActions)
  }

  // 2. Add pending approval items
  for (const approval of approvals.value) {
    const approvalItem = mapApprovalToAction(approval)
    if (approvalItem) items.push(approvalItem)
  }

  // Sort: blocking first, then by deadline urgency
  items.sort((a, b) => {
    const typeOrder: Record<CardType, number> = { blocking: 0, reminding: 1, advancing: 2 }
    const diff = typeOrder[a.cardType] - typeOrder[b.cardType]
    if (diff !== 0) return diff
    // Within same type, sort by priority
    const prioOrder: Record<Priority, number> = { urgent: 0, important: 1, normal: 2 }
    return prioOrder[a.priority] - prioOrder[b.priority]
  })

  return items
}

function mapPlanToActions(plan: PlanAction): ActionItem[] {
  const result: ActionItem[] = []
  const status = plan.status || plan.stage || ''
  const planName = plan.name || '未命名策划'
  const planId = String(plan.id)
  const deadline = plan.deadline || plan.target_end_date || plan.target_date || null

  switch (status) {
    case 'draft':
      result.push({
        id: `plan-draft-${planId}`,
        cardType: 'advancing',
        priority: deadline ? calcPriority(deadline) : 'important',
        title: '草稿待提交',
        description: '产品策划草稿需要提交审核，进入下一阶段',
        planName,
        planId,
        deadline,
        route: `/product-plans/${planId}`,
      })
      break

    case 'costing':
      result.push({
        id: `plan-costing-${planId}`,
        cardType: 'advancing',
        priority: 'important',
        title: '成本待填报',
        description: '需要补充产品目标成本数据',
        planName,
        planId,
        deadline,
        route: `/product-plans/${planId}`,
      })
      break

    case 'project_init':
      // Approval pending - could be reminding or blocking
      // Check if it has a rejected approval
      if (plan.approval_status === 'rejected') {
        result.push({
          id: `plan-rejected-${planId}`,
          cardType: 'blocking',
          priority: 'urgent',
          title: '审批未通过',
          description: '产品策划审批未通过，需修改后重新提交',
          planName,
          planId,
          deadline,
          route: `/product-plans/${planId}`,
        })
      } else {
        result.push({
          id: `plan-approve-${planId}`,
          cardType: 'reminding',
          priority: deadline ? calcPriority(deadline) : 'normal',
          title: '审批待审',
          description: '产品策划正在等待审批处理',
          planName,
          planId,
          deadline,
          route: `/approvals`,
        })
      }
      break

    case 'approved':
      result.push({
        id: `plan-advance-${planId}`,
        cardType: 'advancing',
        priority: deadline ? calcPriority(deadline) : 'normal',
        title: '待推进下阶段',
        description: '策划已批准，可推进到下一阶段',
        planName,
        planId,
        deadline,
        route: `/product-plans/${planId}`,
      })
      break
  }

  return result
}

function mapApprovalToAction(approval: ApprovalRequest): ActionItem | null {
  if (!approval) return null
  // Only show pending approvals as actionable items
  if (approval.status === 'pending' || approval.status === 'submitted') {
    const planName = approval.plan_name || approval.title || '待审批'
    return {
      id: `approval-${approval.id || approval.request_id}`,
      cardType: 'reminding',
      priority: 'urgent',
      title: '审批待审',
      description: `"${planName}" 需要审批`,
      planName,
      planId: String(approval.plan_id ?? ''),
      deadline: approval.deadline || approval.created_at || null,
      route: `/approvals`,
    }
  }
  return null
}

// ── Helpers ──
function calcPriority(deadline: string): Priority {
  const diff = getDayDiff(deadline)
  if (diff <= 3) return 'urgent'
  if (diff <= 7) return 'important'
  return 'normal'
}

function getDayDiff(dateStr: string): number {
  const now = new Date()
  const target = new Date(dateStr)
  const diff = target.getTime() - now.getTime()
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
}

function isOverdue(dateStr: string): boolean {
  return getDayDiff(dateStr) <= 0
}

function countdownLabel(dateStr: string): string {
  const diff = getDayDiff(dateStr)
  if (diff < 0) return `已超期 ${Math.abs(diff)} 天`
  if (diff === 0) return '今天截止'
  if (diff === 1) return '明天截止'
  if (diff <= 7) return `剩余 ${diff} 天`
  return `截止 ${new Date(dateStr).toLocaleDateString('zh-CN')}`
}

function priorityTagType(p: Priority): string {
  const map: Record<Priority, string> = { urgent: 'danger', important: 'primary', normal: 'info' }
  return map[p]
}

function priorityLabel(p: Priority): string {
  const map: Record<Priority, string> = { urgent: '紧急', important: '重要', normal: '普通' }
  return map[p]
}

function typeIcon(type: CardType): string {
  const map: Record<CardType, any> = {
    blocking: 'CircleCloseFilled',
    advancing: 'Promotion',
    reminding: 'AlarmClock',
  }
  return map[type]
}

// ── Computed ──
const allItems = computed<ActionItem[]>(() => computeActions())

const filteredItems = computed(() => allItems.value)

const displayItems = computed(() => filteredItems.value.slice(0, props.maxItems))

const hasMoreItems = computed(() => filteredItems.value.length > props.maxItems)

// ── Navigation ──
function navigateTo(item: ActionItem) {
  if (item.route) {
    router.push(item.route)
  }
}

// ── API fetch ──
async function fetchActions() {
  loading.value = true
  error.value = false
  try {
    // Fetch plans
    const planRes = await api.get('/product-plans', {
      params: { page: 1, page_size: 100 },
    })
    plans.value = planRes.data?.items || (Array.isArray(planRes.data) ? planRes.data : [])

    // Fetch pending approvals
    try {
      const approvalRes = await api.get('/approvals/requests', {
        params: { type: 'proposal' },
      })
      approvals.value = approvalRes.data?.items || (Array.isArray(approvalRes.data) ? approvalRes.data : [])
    } catch {
      // Approvals API is optional; proceed without it
      approvals.value = []
    }
  } catch {
    error.value = true
    plans.value = []
    approvals.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchActions()
})
</script>

<style scoped>
/* ═══════════ Card Container ═══════════ */
.global-action-card {
  background: var(--el-bg-color-overlay, #fff);
  border-radius: var(--el-border-radius-base, 10px);
  border: 1px solid var(--el-border-color, #e5e0da);
  box-shadow: var(--el-box-shadow-light);
  overflow: hidden;
  transition: box-shadow 0.2s ease;
}
.global-action-card:hover {
  box-shadow: var(--el-box-shadow);
}

/* ═══════════ Card Header ═══════════ */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--el-border-color-light, #f0ebe5);
}
.card-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-header-icon {
  color: var(--el-color-primary, #d97757);
}
.card-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary, #1a1917);
}
.card-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-count {
  font-size: 12px;
  color: var(--el-text-color-secondary, #87867f);
}

/* ═══════════ Card Body ═══════════ */
.card-body {
  padding: 8px 0;
}

/* ═══════════ Loading ═══════════ */
.card-loading {
  padding: 20px 16px;
}
.skeleton-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

/* ═══════════ Error ═══════════ */
.card-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 16px;
  text-align: center;
}
.error-text {
  margin: 8px 0 4px;
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary, #1a1917);
}
.error-hint {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary, #87867f);
}

/* ═══════════ Empty ═══════════ */
.card-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 16px;
  text-align: center;
}
.empty-icon {
  color: var(--el-color-success, #2d7d5a);
  margin-bottom: 8px;
}
.empty-title {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary, #1a1917);
}
.empty-desc {
  margin: 0;
  font-size: 12px;
  color: var(--el-text-color-secondary, #87867f);
  line-height: 1.5;
}

/* ═══════════ Action List ═══════════ */
.card-list {
  display: flex;
  flex-direction: column;
}

.action-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.15s ease;
  border-left: 3px solid transparent;
}
.action-item:hover {
  background: rgba(0, 0, 0, 0.02);
}
.action-item:active {
  background: rgba(0, 0, 0, 0.04);
}

/* Card Type border colors */
.action-item.action--blocking {
  border-left-color: var(--el-color-danger, #c04a3a);
}
.action-item.action--advancing {
  border-left-color: var(--el-color-primary, #d97757);
}
.action-item.action--reminding {
  border-left-color: var(--el-color-warning, #b8811c);
}

/* Icon styles */
.action-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  flex-shrink: 0;
}
.icon--blocking {
  background: rgba(192, 74, 58, 0.1);
  color: var(--el-color-danger, #c04a3a);
}
.icon--advancing {
  background: rgba(217, 119, 87, 0.1);
  color: var(--el-color-primary, #d97757);
}
.icon--reminding {
  background: rgba(184, 129, 28, 0.1);
  color: var(--el-color-warning, #b8811c);
}

/* Content area */
.action-content {
  flex: 1;
  min-width: 0;
}
.action-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}
.action-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary, #1a1917);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.action-priority {
  flex-shrink: 0;
}
.action-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary, #87867f);
  line-height: 1.4;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.action-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  color: var(--el-text-color-placeholder, #b5b0a7);
}
.action-plan-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 140px;
}
.action-deadline {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
  white-space: nowrap;
}
.action-deadline.overdue {
  color: var(--el-color-danger, #c04a3a);
  font-weight: 500;
}

/* Arrow */
.action-arrow {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.action-item:hover .action-arrow {
  opacity: 1;
  transform: translateX(2px);
}

/* ═══════════ Footer ═══════════ */
.card-footer {
  border-top: 1px solid var(--el-border-color-light, #f0ebe5);
  padding: 8px 16px;
  text-align: center;
}
</style>
