<template>
  <el-card shadow="never" class="col-card">
    <template #header>
      <div class="card-header">
        <span>📊 我的项目</span>
      </div>
    </template>
    <div class="stats-row">
      <div class="stat-item">
        <div class="stat-num">{{ projects.length }}</div>
        <div class="stat-label">总数</div>
      </div>
      <div class="stat-item">
        <div class="stat-num" style="color:#409eff">{{ stats.running }}</div>
        <div class="stat-label">进行中</div>
      </div>
      <div class="stat-item">
        <div class="stat-num" style="color:#67c23a">{{ stats.completed }}</div>
        <div class="stat-label">已完成</div>
      </div>
      <div class="stat-item">
        <div class="stat-num" style="color:#f56c6c">{{ stats.overdue }}</div>
        <div class="stat-label">超期</div>
      </div>
    </div>
    <div v-if="projects.length === 0" class="empty-state">
      <el-empty description="暂无项目" :image-size="60" />
    </div>
    <div v-for="proj in projects" :key="proj.id" class="project-card" @click="toggleExpand(proj.id)">
      <div class="project-card-header">
        <span class="project-name">{{ proj.name }}</span>
        <div class="project-card-tags">
          <el-tag v-if="proj.approval_status" :type="approvalTagType(proj.approval_status)" size="small">{{ approvalLabel(proj.approval_status) }}</el-tag>
          <el-tag :type="statusTagType(proj.status)" size="small">{{ statusLabel(proj.status) }}</el-tag>
        </div>
      </div>
      <el-progress
        :percentage="proj.progress || 0"
        :color="progressColor(proj.progress || 0)"
        :stroke-width="6"
        style="margin:6px 0"
      />
      <div class="project-card-meta" v-if="proj.budget || proj.market_policy">
        <span v-if="proj.budget">预算: ¥{{ formatMoney(proj.budget) }}</span>
        <span v-if="proj.market_policy">{{ proj.market_policy }}</span>
      </div>
      <div v-if="expandedProjectId === proj.id" class="project-detail">
        <div class="detail-row"><label>项目等级:</label> {{ proj.project_class || '-' }}级</div>
        <div class="detail-row"><label>应用场景:</label> {{ proj.scene || '-' }}</div>
        <div class="detail-row"><label>关联产品:</label> {{ proj.linked_product || '-' }}</div>
        <div class="detail-row"><label>目标日期:</label> {{ proj.target_end_date || '-' }}</div>
        <div class="detail-row"><label>背景:</label> {{ proj.background_basis || '-' }}</div>
        <div class="detail-row"><label>市场政策:</label> {{ proj.market_policy || '-' }}</div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ProjectItem } from './types'
import { formatMoney, statusTagType, statusLabel, approvalTagType, approvalLabel, progressColor } from './pm-helpers'

const props = defineProps<{
  projects: ProjectItem[]
}>()

// 看板统计
const stats = computed(() => {
  const items = props.projects
  const running = items.filter(p => p.status === 'running').length
  const completed = items.filter(p => p.status === 'completed').length
  const overdue = items.filter(p => p.status === 'overdue').length
  return { running, completed, overdue }
})

// 展开的项目ID
const expandedProjectId = ref<number | null>(null)

function toggleExpand(projId: number) {
  expandedProjectId.value = expandedProjectId.value === projId ? null : projId
}
</script>

<style scoped>
.col-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.col-card :deep(.el-card__body) {
  flex: 1;
  overflow-y: auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.empty-state {
  padding: 20px 0;
}

.stats-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.stat-item {
  flex: 1;
  text-align: center;
}

.stat-num {
  font-size: 20px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}

.project-card {
  padding: 10px 12px;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  border: 1px solid #ebeef5;
  transition: all 0.2s;
}

.project-card:hover {
  border-color: #409eff;
  background: #ecf5ff;
}

.project-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.project-card-tags {
  display: flex;
  gap: 4px;
  align-items: center;
}

.project-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  margin-right: 8px;
}

.project-card-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 12px;
}

.project-detail {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #dcdfe6;
  font-size: 12px;
  color: #606266;
}

.detail-row {
  padding: 2px 0;
}

.detail-row label {
  font-weight: 500;
  color: #303133;
  margin-right: 4px;
}
</style>
