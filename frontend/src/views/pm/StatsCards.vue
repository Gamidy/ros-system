<template>
  <el-row :gutter="12" class="stats-cards" v-if="statsData">
    <el-col :span="4">
      <el-card shadow="never" class="stat-card">
        <div class="stat-card-num">{{ statsData.annual_plan_count }}</div>
        <div class="stat-card-label">年度规划</div>
      </el-card>
    </el-col>
    <el-col :span="5">
      <el-card shadow="never" class="stat-card">
        <div class="stat-card-num">{{ statsData.total_projects }}</div>
        <div class="stat-card-label">总项目数</div>
      </el-card>
    </el-col>
    <el-col :span="5">
      <el-card shadow="never" class="stat-card">
        <div class="stat-card-num">¥{{ formatMoney(statsData.total_budget) }}</div>
        <div class="stat-card-label">总预算</div>
      </el-card>
    </el-col>
    <el-col :span="5">
      <el-card shadow="never" class="stat-card">
        <div class="stat-card-num" :style="{ color: statsData.completion_rate >= 60 ? '#67c23a' : '#e6a23c' }">{{ statsData.completion_rate }}%</div>
        <div class="stat-card-label">完成率</div>
      </el-card>
    </el-col>
    <el-col :span="5">
      <el-card shadow="never" class="stat-card">
        <div class="stat-card-num" :style="{ color: statsData.overdue_rate > 0 ? '#f56c6c' : '#67c23a' }">{{ statsData.overdue_rate }}%</div>
        <div class="stat-card-label">逾期率</div>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import type { WorkspaceStats } from './types'
import { formatMoney } from './pm-helpers'

defineProps<{
  statsData: WorkspaceStats | null
}>()
</script>

<style scoped>
.stats-cards {
  margin-bottom: 16px;
}
.stat-card {
  text-align: center;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.stat-card :deep(.el-card__body) {
  padding: 12px 8px;
  width: 100%;
}
.stat-card-num {
  font-size: 26px;
  font-weight: bold;
  color: #303133;
  line-height: 1.2;
}
.stat-card-label {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

/* 移动端响应式 */
@media (max-width: 768px) {
  .stats-cards {
    flex-wrap: wrap;
  }
  .stat-card {
    flex: 1 1 calc(50% - 8px);
    min-width: 0;
  }
}
</style>
