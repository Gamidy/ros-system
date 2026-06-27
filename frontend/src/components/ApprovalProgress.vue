<template>
  <div class="approval-progress">
    <el-steps
      :active="activeStepIndex"
      align-center
      finish-status="success"
      process-status="process"
      :direction="direction"
    >
      <el-step
        v-for="(step, idx) in sortedSteps"
        :key="step.seq ?? idx"
        :status="getStepStatus(step)"
        :title="step.name"
      >
        <template #description>
          <div class="step-desc">
            <!-- 角色 -->
            <div class="step-role">{{ getRoleLabel(step.role) }}</div>

            <!-- 状态标签 -->
            <div class="step-badge">
              <el-tag
                :type="getStatusTagType(getStepStatus(step))"
                size="small"
                effect="plain"
              >
                {{ getStatusLabel(getStepStatus(step)) }}
              </el-tag>
            </div>

            <!-- 并行审批决策 (step_meta.decisions) -->
            <div v-if="getDecisions(step).length > 0" class="step-decisions">
              <div
                v-for="dec in getDecisions(step)"
                :key="dec.username"
                class="decision-item"
              >
                <span class="decision-user">{{ dec.username }}</span>
                <el-tag
                  :type="getDecisionTagType(dec.decision)"
                  size="small"
                >
                  {{ getDecisionLabel(dec.decision) }}
                </el-tag>
                <span v-if="dec.comment" class="decision-comment">
                  "{{ dec.comment }}"
                </span>
              </div>
            </div>

            <!-- 审批记录 -->
            <div v-if="getStepRecords(step).length > 0" class="step-records">
              <div
                v-for="rec in getStepRecords(step)"
                :key="rec.approver + (rec.decided_at || '')"
                class="record-item"
              >
                <span class="record-user">{{ rec.approver }}</span>
                <el-tag
                  :type="getDecisionTagType(rec.decision)"
                  size="small"
                >
                  {{ getDecisionLabel(rec.decision) }}
                </el-tag>
                <span v-if="rec.comment" class="record-comment">
                  "{{ rec.comment }}"
                </span>
                <span v-if="rec.decided_at" class="record-time">
                  {{ formatTime(rec.decided_at) }}
                </span>
              </div>
            </div>
          </div>
        </template>
      </el-step>
    </el-steps>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

// ── 内联类型定义 ──

interface ApprovalStepOut {
  seq: number
  role: string
  step_type: string
  name: string
}

interface ApprovalRecordOut {
  approver: string
  decision: string
  comment?: string
  decided_at?: string
  step_seq?: number
}

interface DecisionInfo {
  decision: string
  comment?: string
  role?: string
}

interface StepMeta {
  decisions?: Record<string, DecisionInfo>
  [key: string]: unknown
}

// ── Props ──

const props = withDefaults(
  defineProps<{
    approvalId: number
    steps: ApprovalStepOut[]
    currentStep: number
    stepMeta?: Record<string, StepMeta>
    records?: ApprovalRecordOut[]
    direction?: 'horizontal' | 'vertical'
  }>(),
  {
    stepMeta: () => ({}),
    records: () => [],
    direction: 'vertical',
  },
)

// ── 帮助函数 ──

/** 按 seq 排序后的步骤 */
const sortedSteps = computed(() => {
  return [...props.steps].sort((a, b) => a.seq - b.seq)
})

/** el-steps 需要的 active index（0-based） */
const activeStepIndex = computed(() => {
  if (!props.steps.length) return -1
  // currentStep 是步骤序号，找到其在排序后的索引
  const idx = sortedSteps.value.findIndex((s) => s.seq === props.currentStep)
  return idx >= 0 ? idx : sortedSteps.value.length
})

/** 获取步骤的状态 */
function getStepStatus(step: ApprovalStepOut): 'wait' | 'process' | 'finish' | 'error' | 'success' {
  const stepDecisions = getDecisions(step)
  // 如果有并行决策且有人驳回，标记为 error
  if (stepDecisions.length > 0) {
    const hasRejection = stepDecisions.some((d) => d.decision === 'rejected')
    if (hasRejection) return 'error'
  }
  // 检查审批记录中是否有驳回
  const stepRecs = getStepRecords(step)
  if (stepRecs.some((r) => r.decision === 'rejected')) return 'error'

  if (step.seq < props.currentStep) return 'success'
  if (step.seq === props.currentStep) return 'process'
  return 'wait'
}

/** 获取步骤的并行决策列表 */
function getDecisions(step: ApprovalStepOut): { username: string; decision: string; comment?: string }[] {
  const meta = props.stepMeta[String(step.seq)] ?? props.stepMeta[step.seq]
  if (!meta?.decisions) return []
  return Object.entries(meta.decisions).map(([username, info]) => ({
    username,
    decision: info.decision,
    comment: info.comment,
  }))
}

/** 获取步骤关联的审批记录 */
function getStepRecords(step: ApprovalStepOut): ApprovalRecordOut[] {
  return (props.records ?? []).filter((r) => {
    // 优先通过 step_seq 匹配
    if (r.step_seq !== undefined) return r.step_seq === step.seq
    // 否则看该步骤的决策中是否有此审批人
    const decisions = getDecisions(step)
    return decisions.some((d) => d.username === r.approver)
  })
}

/** 角色标签映射 */
function getRoleLabel(role: string): string {
  const map: Record<string, string> = {
    admin: '管理员',
    engineer: '工程师',
    module_manager: '模块经理',
    rd_director: '研发总监',
    general_manager: '总经理',
    pm: '项目经理',
    qa: '质量工程师',
    sales: '销售',
    purchase: '采购',
    production: '生产',
  }
  return map[role] || role
}

/** 步骤状态 → el-tag 类型 */
function getStatusTagType(status: string): string {
  const map: Record<string, string> = {
    success: 'success',
    finish: 'success',
    process: 'primary',
    wait: 'info',
    error: 'danger',
  }
  return map[status] || 'info'
}

/** 步骤状态 → 中文标签 */
function getStatusLabel(status: string): string {
  const map: Record<string, string> = {
    success: '已完成',
    finish: '已完成',
    process: '进行中',
    wait: '待审批',
    error: '已驳回',
  }
  return map[status] || status
}

/** 审批决策 → el-tag 类型 */
function getDecisionTagType(decision: string): string {
  const map: Record<string, string> = {
    approved: 'success',
    approve: 'success',
    rejected: 'danger',
    reject: 'danger',
    pending: 'warning',
    abstain: 'info',
  }
  return map[decision] || 'info'
}

/** 审批决策 → 中文标签 */
function getDecisionLabel(decision: string): string {
  const map: Record<string, string> = {
    approved: '通过',
    approve: '通过',
    rejected: '驳回',
    reject: '驳回',
    pending: '待审批',
    abstain: '弃权',
  }
  return map[decision] || decision
}

/** 时间格式化 */
function formatTime(iso: string): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch {
    return iso
  }
}
</script>

<style scoped>
.approval-progress {
  width: 100%;
}

.step-desc {
  font-size: 13px;
  line-height: 1.6;
}

.step-role {
  color: #909399;
  font-size: 12px;
  margin-bottom: 2px;
}

.step-badge {
  margin-bottom: 6px;
}

/* ── 并行审批决策 ── */
.step-decisions {
  margin-top: 6px;
  padding: 6px 8px;
  background: #fafafa;
  border-radius: 4px;
  border: 1px solid #f0f0f0;
}

.decision-item {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  padding: 2px 0;
}

.decision-item + .decision-item {
  border-top: 1px dashed #f0f0f0;
  margin-top: 4px;
  padding-top: 6px;
}

.decision-user {
  font-weight: 600;
  color: #303133;
  font-size: 12px;
}

.decision-comment {
  color: #909399;
  font-size: 12px;
  font-style: italic;
}

/* ── 审批记录 ── */
.step-records {
  margin-top: 6px;
  padding: 6px 8px;
  background: #f6ffed;
  border-radius: 4px;
  border: 1px solid #e8f8e0;
}

.record-item {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  padding: 2px 0;
}

.record-item + .record-item {
  border-top: 1px dashed #e8f8e0;
  margin-top: 4px;
  padding-top: 6px;
}

.record-user {
  font-weight: 600;
  color: #303133;
  font-size: 12px;
}

.record-comment {
  color: #909399;
  font-size: 12px;
  font-style: italic;
}

.record-time {
  color: #c0c4cc;
  font-size: 11px;
  margin-left: auto;
}
</style>
