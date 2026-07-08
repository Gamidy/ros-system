<template>
  <div class="roadmap-panel">
    <div v-if="!items || items.length === 0" class="roadmap-empty">
      <el-empty description="暂无路线图数据" :image-size="60" />
    </div>

    <div v-for="group in items" :key="group.year" class="roadmap-group">
      <!-- 年度标题 -->
      <div class="roadmap-year-header">
        <span class="roadmap-year-label">{{ group.is_other ? '其他' : group.year + '年' }}</span>
        <span class="roadmap-year-count">
          {{ group.plans.length }}个规划 · {{ group.projects.length }}个项目
        </span>
      </div>

      <!-- 规划列表 -->
      <div v-if="group.plans.length > 0" class="roadmap-plans">
        <div v-for="plan in group.plans" :key="plan.id" class="roadmap-plan-item">
          <span class="plan-name">{{ plan.name }}</span>
          <span v-if="plan.description" class="plan-desc">{{ plan.description }}</span>
        </div>
      </div>

      <!-- 项目甘特图 -->
      <div v-if="group.projects.length > 0" class="roadmap-gantt">
        <!-- 月份刻度 -->
        <div class="gantt-month-row">
          <div class="gantt-label-col">项目</div>
          <div class="gantt-timeline">
            <div
              v-for="m in 12"
              :key="m"
              class="gantt-month-cell"
              :class="{ 'gantt-month-alt': m % 2 === 0 }"
            >{{ m }}月</div>
          </div>
        </div>

        <!-- 项目行 -->
        <div
          v-for="proj in group.projects"
          :key="proj.id"
          class="gantt-row"
          :class="{ 'gantt-row-overdue': isOverdue(proj) }"
        >
          <div class="gantt-label-col">
            <div class="gantt-project-name" :title="proj.name">{{ proj.name }}</div>
            <div class="gantt-project-meta">
              <el-tag :type="statusTagType(proj.status)" size="small" effect="plain">{{ statusLabel(proj.status) }}</el-tag>
              <span v-if="proj.project_class" class="gantt-project-class">{{ proj.project_class }}</span>
            </div>
          </div>
          <div class="gantt-timeline">
            <!-- 背景网格 -->
            <div
              v-for="m in 12"
              :key="'grid-' + m"
              class="gantt-grid-cell"
              :class="{ 'gantt-grid-alt': m % 2 === 0 }"
            ></div>
            <!-- 项目时间条 -->
            <div
              v-if="proj.start_date"
              class="gantt-bar"
              :class="'gantt-bar-' + barStatus(proj)"
              :style="barStyle(proj)"
            >
              <span class="gantt-bar-label">{{ proj.name.substring(0, 12) }}{{ proj.name.length > 12 ? '..' : '' }}</span>
            </div>
            <div v-else class="gantt-no-date">（日期未填）</div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="roadmap-no-projects">暂无关联项目</div>
    </div>
  </div>
</template>

<script setup lang="ts">

interface RoadmapProject {
  id: number
  name: string
  status: string
  start_date: string | null
  target_end_date: string | null
  actual_end_date: string | null
  budget: number | null
  project_class: string | null
  annual_planning_ref: string | null
}

interface RoadmapPlan {
  id: number
  name: string
  description: string | null
}

interface RoadmapGroup {
  year: number
  plans: RoadmapPlan[]
  projects: RoadmapProject[]
  is_other?: boolean
}

const props = defineProps<{
  items: RoadmapGroup[]
}>()

// 工具函数
function statusTagType(status: string): string {
  const map: Record<string, string> = {
    planning: 'info', running: '', completed: 'success',
    paused: 'warning', cancelled: 'danger', draft: 'info', overdue: 'danger',
    submitted: 'primary',
  }
  return map[status] || 'info'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    planning: '规划中', running: '进行中', completed: '已完成',
    paused: '暂停', cancelled: '已取消', draft: '草稿', overdue: '超期',
    submitted: '已提交',
  }
  return map[status] || status
}

function isOverdue(proj: RoadmapProject): boolean {
  if (proj.status === 'completed' || proj.status === 'cancelled') return false
  if (!proj.target_end_date) return false
  const today = new Date()
  return new Date(proj.target_end_date) < today
}

function barStatus(proj: RoadmapProject): string {
  if (isOverdue(proj)) return 'overdue'
  if (proj.status === 'completed') return 'completed'
  if (proj.status === 'running' || proj.status === 'submitted') return 'running'
  if (proj.status === 'planning' || proj.status === 'draft') return 'planning'
  if (proj.status === 'cancelled' || proj.status === 'paused') return 'cancelled'
  return 'planning'
}

/**
 * 计算项目时间条的位置和宽度
 * 基于月份：left = (startMonth - 1) * (100/12)%
 * width = (endMonth - startMonth + 1) * (100/12)%
 */
function barStyle(proj: RoadmapProject): Record<string, string> {
  const monthCount = 12
  const cellPct = 100 / monthCount

  let startMonth = 1
  let endMonth = 12

  if (proj.start_date) {
    const sd = new Date(proj.start_date)
    startMonth = sd.getMonth() + 1  // 1-12
  }

  if (proj.target_end_date) {
    const ed = new Date(proj.target_end_date)
    endMonth = ed.getMonth() + 1
  }

  // 钳制
  startMonth = Math.max(1, Math.min(12, startMonth))
  endMonth = Math.max(startMonth, Math.min(12, endMonth))

  const left = (startMonth - 1) * cellPct
  const width = (endMonth - startMonth + 1) * cellPct

  return {
    left: left + '%',
    width: width + '%',
  }
}
</script>

<style scoped>
.roadmap-panel {
  padding: 4px 0;
}

.roadmap-empty {
  padding: 40px 0;
}

/* ── 年度分组 ── */
.roadmap-group {
  margin-bottom: 24px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow: hidden;
}

.roadmap-year-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
}

.roadmap-year-label {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.roadmap-year-count {
  font-size: 12px;
  color: #909399;
}

/* ── 规划列表 ── */
.roadmap-plans {
  padding: 8px 16px;
  background: #fafafa;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.roadmap-plan-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  border-radius: 4px;
  padding: 3px 10px;
  font-size: 12px;
}

.plan-name {
  font-weight: 600;
  color: #409eff;
}

.plan-desc {
  color: #909399;
  font-size: 11px;
}

.roadmap-no-projects {
  padding: 24px;
  text-align: center;
  color: #c0c4cc;
  font-size: 13px;
}

/* ── 甘特图容器 ── */
.roadmap-gantt {
  overflow-x: auto;
}

/* ── 行 ── */
.gantt-month-row,
.gantt-row {
  display: flex;
  border-bottom: 1px solid #f2f2f2;
}

.gantt-row:last-child {
  border-bottom: none;
}

.gantt-row:hover {
  background: #f5f7fa;
}

.gantt-row-overdue {
  background: #fef0f0;
}
.gantt-row-overdue:hover {
  background: #fde2e2;
}

/* ── 标签列 ── */
.gantt-label-col {
  flex: 0 0 200px;
  padding: 8px 12px;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 44px;
}

.gantt-project-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gantt-project-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.gantt-project-class {
  font-size: 11px;
  color: #909399;
}

/* ── 时间线列 ── */
.gantt-timeline {
  flex: 1;
  position: relative;
  display: flex;
  min-height: 44px;
  align-items: center;
}

/* ── 月份刻度行 ── */
.gantt-month-row .gantt-label-col {
  font-size: 12px;
  color: #909399;
  font-weight: 500;
}

.gantt-month-cell {
  flex: 1;
  text-align: center;
  font-size: 11px;
  color: #909399;
  padding: 6px 0;
  border-right: 1px solid #f2f2f2;
}

.gantt-month-cell:last-child {
  border-right: none;
}

.gantt-month-alt {
  background: #fafafa;
}

/* ── 网格 ── */
.gantt-grid-cell {
  flex: 1;
  border-right: 1px solid #f5f5f5;
  height: 100%;
}

.gantt-grid-cell:last-child {
  border-right: none;
}

.gantt-grid-alt {
  background: #fafafa;
}

/* ── 项目时间条 ── */
.gantt-bar {
  position: absolute;
  top: 8px;
  bottom: 8px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  padding: 0 6px;
  transition: opacity 0.2s;
  z-index: 2;
  overflow: hidden;
}

.gantt-bar:hover {
  opacity: 0.85;
}

.gantt-bar-label {
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── 状态颜色 ── */
.gantt-bar-planning {
  background: linear-gradient(135deg, #a0cfff, #79bbff);
  color: #fff;
}

.gantt-bar-running {
  background: linear-gradient(135deg, #67c23a, #85ce61);
  color: #fff;
}

.gantt-bar-completed {
  background: linear-gradient(135deg, #b3b3b3, #d0d0d0);
  color: #fff;
}

.gantt-bar-overdue {
  background: linear-gradient(135deg, #f56c6c, #f89898);
  color: #fff;
  animation: gantt-pulse 2s ease-in-out infinite;
}

.gantt-bar-cancelled {
  background: #e0e0e0;
  color: #999;
  opacity: 0.6;
}

@keyframes gantt-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(245, 108, 108, 0.4); }
  50% { box-shadow: 0 0 0 4px rgba(245, 108, 108, 0.1); }
}

/* ── 无日期 ── */
.gantt-no-date {
  font-size: 12px;
  color: #c0c4cc;
  padding-left: 12px;
}
</style>
