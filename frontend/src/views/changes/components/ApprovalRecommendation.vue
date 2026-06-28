<template>
  <el-card
    shadow="never"
    class="approval-rec-card"
    v-loading="store.recLoading"
  >
    <template #header>
      <div class="card-header">
        <span>AI 审批推荐</span>
      </div>
    </template>

    <!-- 错误状态 -->
    <el-alert
      v-if="store.recError"
      :title="store.recError"
      type="error"
      show-icon
      :closable="false"
    >
      <template #action>
        <el-button size="small" type="danger" @click="handleRetry">
          重试
        </el-button>
      </template>
    </el-alert>

    <!-- 空状态 -->
    <el-empty
      v-else-if="!store.recommendation && !store.recLoading"
      description="暂无审批推荐数据"
      :image-size="80"
    />

    <!-- 主要内容 -->
    <template v-else-if="store.recommendation">
      <!-- 推荐动作标签 -->
      <div class="action-section">
        <span class="action-label">推荐动作</span>
        <el-tag
          :type="recTagConfig.type"
          size="large"
          effect="dark"
        >
          {{ recTagConfig.label }}
        </el-tag>
      </div>

      <!-- 置信度进度条 -->
      <div class="confidence-section">
        <div class="confidence-header">
          <span class="section-label">置信度</span>
          <span class="confidence-value">{{ confidencePercent }}%</span>
        </div>
        <el-progress
          :percentage="confidencePercent"
          :color="confidenceColor"
          :stroke-width="12"
          striped
          striped-flow
        />
      </div>

      <!-- AI 解释 -->
      <div class="reason-section">
        <h4 class="section-title">AI 解释</h4>
        <el-text type="info" class="reason-text">
          {{ store.recommendation.reason }}
        </el-text>
      </div>

      <!-- 建议审批人 -->
      <div
        v-if="store.recommendation.required_approvers.length"
        class="approvers-section"
      >
        <h4 class="section-title">建议审批人</h4>
        <el-timeline>
          <el-timeline-item
            v-for="(role, idx) in store.recommendation.required_approvers"
            :key="idx"
            :timestamp="`审批角色 #${idx + 1}`"
            placement="top"
          >
            <div class="approver-item">
              <span class="approver-role">{{ role }}</span>
              <el-text type="info" size="small" class="approver-reason">
                {{ store.recommendation.reason }}
              </el-text>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>
    </template>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useCIEv2Store } from '@/stores/ci_v2'

// ── Props ─────────────────────────────────────────────

const props = defineProps<{
  ecrId: number
}>()

// ── Store ─────────────────────────────────────────────

const store = useCIEv2Store()

// ── 类型定义 ──────────────────────────────────────────

interface RecTagConfig {
  label: string
  type: 'success' | 'warning' | 'primary' | 'danger'
}

// ── 常量 ──────────────────────────────────────────────

const REC_TAG_MAP: Record<string, RecTagConfig> = {
  AUTO_APPROVE: { label: '自动批准', type: 'success' },
  FAST_TRACK: { label: '快速通道', type: 'warning' },
  FULL_APPROVAL: { label: '完整审批', type: 'primary' },
  REJECT_REDESIGN: { label: '退回重设计', type: 'danger' },
}

// ── 计算属性 ──────────────────────────────────────────

const recTagConfig = computed<RecTagConfig>(() => {
  const action: string = store.recommendation?.recommendation ?? ''
  return REC_TAG_MAP[action] ?? { label: action, type: 'primary' }
})

const confidencePercent = computed<number>(() => {
  const c: number = store.recommendation?.confidence ?? 0
  return Math.round(Math.min(c, 1) * 100)
})

const confidenceColor = computed<string>(() => {
  const pct: number = confidencePercent.value
  if (pct >= 80) return '#67C23A'
  if (pct >= 50) return '#E6A23C'
  return '#F56C6C'
})

// ── 生命周期 ──────────────────────────────────────────

onMounted(() => {
  store.loadApprovalRecommendation(props.ecrId)
})

// ── 事件处理 ──────────────────────────────────────────

function handleRetry(): void {
  store.loadApprovalRecommendation(props.ecrId)
}
</script>

<style scoped>
.approval-rec-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: 15px;
}

.action-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0 16px;
}

.action-label {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
}

.confidence-section {
  padding-bottom: 16px;
}

.confidence-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.section-label {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
}

.confidence-value {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.reason-section {
  padding: 16px 0;
  border-top: 1px solid #ebeef5;
}

.section-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.reason-text {
  display: block;
  line-height: 1.6;
  font-size: 13px;
}

.approvers-section {
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.approver-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.approver-role {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.approver-reason {
  line-height: 1.5;
}
</style>
