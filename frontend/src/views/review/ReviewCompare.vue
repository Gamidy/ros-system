<template>
  <div class="review-compare">
    <!-- 页面头部 -->
    <div class="compare-header">
      <div>
        <h2 class="compare-title">📊 复盘对比分析</h2>
        <p class="compare-subtitle">
          对比 {{ items.length }} 个复盘的评分、偏差、问题解决率等关键指标
        </p>
      </div>
      <div class="header-actions">
        <el-button size="small" @click="$emit('back')">← 返回看板</el-button>
      </div>
    </div>

    <!-- 对比卡片区域 -->
    <div class="compare-cards-wrapper">
      <div
        v-for="item in items"
        :key="item.review_id"
        class="compare-card"
      >
        <!-- 卡片头部 — 策划名称/系列 -->
        <div class="card-header">
          <div class="card-plan-name" :title="item.plan_name">{{ item.plan_name }}</div>
          <div v-if="item.plan_series" class="card-series">
            <el-tag size="small" effect="plain">{{ item.plan_series }}</el-tag>
          </div>
          <div class="card-date">{{ item.review_date || '—' }}</div>
        </div>

        <el-divider style="margin: 8px 0" />

        <!-- ═══ 评分 ═══ -->
        <div class="metric-section">
          <div class="metric-label">综合评分</div>
          <div class="metric-value-group">
            <el-rate
              :model-value="item.rating ?? 0"
              :max="5"
              disabled
              show-score
              :texts="['很差','较差','一般','较好','很好']"
              score-template="{value}分"
              style="display:inline-flex"
            />
            <DiffBadge
              :value="item.rating"
              :all-values="allRatings"
              higher-better
            />
          </div>
        </div>

        <!-- ═══ 成本偏差 ═══ -->
        <div class="metric-section">
          <div class="metric-label">成本偏差 (%)</div>
          <div class="metric-value">
            <span :class="costClass(item.cost_variance_pct)">
              {{ formatPct(item.cost_variance_pct) }}
            </span>
            <DiffBadge
              :value="item.cost_variance_pct"
              :all-values="allCosts"
              :higher-better="false"
            />
          </div>
        </div>

        <!-- ═══ 进度偏差 ═══ -->
        <div class="metric-section">
          <div class="metric-label">进度偏差 (天)</div>
          <div class="metric-value">
            <span :class="scheduleClass(item.schedule_variance_days)">
              {{ formatDays(item.schedule_variance_days) }}
            </span>
            <DiffBadge
              :value="item.schedule_variance_days"
              :all-values="allSchedules"
              :higher-better="false"
            />
          </div>
        </div>

        <!-- ═══ 改进任务完成率 ═══ -->
        <div class="metric-section">
          <div class="metric-label">改进任务完成率</div>
          <div class="metric-value-group">
            <el-progress
              :percentage="item.task_completion_rate"
              :stroke-width="16"
              :color="completionColor(item.task_completion_rate)"
              style="width:100%;max-width:180px"
            />
            <DiffBadge
              :value="item.task_completion_rate"
              :all-values="allCompletions"
              higher-better
            />
          </div>
          <div class="metric-detail">
            {{ item.task_resolved }} / {{ item.task_total }} 已解决
          </div>
        </div>

        <!-- ═══ 主要问题 ═══ -->
        <div class="metric-section">
          <div class="metric-label">主要问题</div>
          <div class="metric-issues">
            <p v-if="item.main_issues" class="issues-text">{{ item.main_issues }}</p>
            <span v-else class="issues-empty">无记录</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ReviewCompareItem } from '../../api/productPlan'

const props = defineProps<{
  items: ReviewCompareItem[]
}>()

defineEmits<{
  back: []
}>()

// ── 辅助计算：各指标的值数组（用于比较） ──

const allRatings = computed<number[]>(() => props.items.map(i => i.rating ?? 0))
const allCosts = computed<number[]>(() => props.items.map(i => i.cost_variance_pct ?? 0))
const allSchedules = computed<number[]>(() => props.items.map(i => i.schedule_variance_days ?? 0))
const allCompletions = computed<number[]>(() => props.items.map(i => i.task_completion_rate))

// ── 格式化 ──

function formatPct(val: number | null | undefined): string {
  if (val == null) return '—'
  const sign = val > 0 ? '+' : ''
  return `${sign}${val.toFixed(2)}%`
}

function formatDays(val: number | null | undefined): string {
  if (val == null) return '—'
  if (val > 0) return `延迟 ${val} 天`
  if (val < 0) return `提前 ${Math.abs(val)} 天`
  return '准时'
}

// ── 样式类 ──

function costClass(val: number | null | undefined): string {
  if (val == null) return ''
  // 成本偏差越小越好（负偏差 = 节约 = 好）
  return val <= 0 ? 'metric-good' : 'metric-bad'
}

function scheduleClass(val: number | null | undefined): string {
  if (val == null) return ''
  // 进度偏差越小越好（负偏差 = 提前 = 好）
  return val <= 0 ? 'metric-good' : 'metric-bad'
}

function completionColor(val: number): string {
  if (val >= 80) return '#67C23A'
  if (val >= 50) return '#E6A23C'
  return '#F56C6C'
}
</script>

<!-- ═══ DiffBadge 子组件（单文件 Options API） ═══ -->

<script lang="ts">
import { defineComponent, type PropType } from 'vue'

const DiffBadge = defineComponent({
  name: 'DiffBadge',
  props: {
    value: { type: Number as PropType<number | null>, default: null },
    allValues: { type: Array as PropType<number[]>, required: true },
    higherBetter: { type: Boolean, default: true },
  },
  setup(props) {
    const distinctValues = computed<number[]>(() => [...new Set(props.allValues)])
    const rank = computed<number | null>(() => {
      if (props.value == null) return null
      const sorted = [...distinctValues.value].sort((a, b) =>
        props.higherBetter ? b - a : a - b
      )
      const idx = sorted.indexOf(props.value)
      if (idx === -1 || sorted.length <= 1) return null
      return idx + 1
    })
    const isBest = computed<boolean>(() => rank.value === 1)
    const isWorst = computed<boolean>(() => rank.value === distinctValues.value.length && distinctValues.value.length > 1)

    return { rank, isBest, isWorst }
  },
  template: `
    <span
      v-if="rank != null"
      class="diff-badge"
      :class="{ 'badge-best': isBest, 'badge-worst': isWorst }"
    >
      {{ isBest ? '↑ 最优' : isWorst ? '↓ 最差' : '#' + rank }}
    </span>
  `,
})

export default DiffBadge
</script>

<!-- 主样式 -->
<style scoped>
.review-compare {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.compare-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.compare-title {
  font-size: 20px;
  font-weight: 700;
  color: #1d1d1f;
  margin: 0;
}

.compare-subtitle {
  font-size: 13px;
  color: #86868b;
  margin: 4px 0 0;
}

.compare-cards-wrapper {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 16px;
}

.compare-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 20px;
  transition: box-shadow 0.2s;
}

.compare-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.card-header {
  text-align: center;
  margin-bottom: 4px;
}

.card-plan-name {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-series {
  margin-top: 4px;
}

.card-date {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

/* ── 指标分区 ── */

.metric-section {
  margin-top: 14px;
  padding: 0 4px;
}

.metric-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
  font-weight: 500;
}

.metric-value {
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.metric-value-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.metric-detail {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}

.metric-issues {
  margin-top: 2px;
}

.issues-text {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.issues-empty {
  font-size: 12px;
  color: #c0c4cc;
}

/* ── 颜色标识 ── */

.metric-good {
  color: #67C23A;
}

.metric-bad {
  color: #F56C6C;
}
</style>

<!-- DiffBadge 全局样式 -->
<style>
.diff-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 10px;
  background: #f0f2f5;
  color: #606266;
  line-height: 1.6;
}

.diff-badge.badge-best {
  background: #e1f3d8;
  color: #529b2e;
}

.diff-badge.badge-worst {
  background: #fde2e2;
  color: #c45656;
}
</style>
