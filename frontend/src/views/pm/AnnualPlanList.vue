<template>
  <el-card shadow="never" class="col-card">
    <template #header>
      <div class="card-header">
        <span>📋 年度产品规划</span>
        <el-button type="primary" size="small" @click="$router.push('/product-plans')">查看全部</el-button>
      </div>
    </template>
    <div v-if="planningItems.length === 0" class="empty-state">
      <el-empty description="暂无年度规划项" :image-size="60" />
    </div>
    <div
      v-for="item in planningItems" :key="item.id"
      class="plan-item"
      @click="$router.push('/product-plans/' + item.id)"
    >
      <div class="plan-item-name">{{ item.name }}</div>
      <div class="plan-item-meta">
        <el-tag size="small" type="warning">{{ item.year }}</el-tag>
        <span class="plan-item-desc">{{ item.description || '暂无描述' }}</span>
      </div>
      <div class="plan-item-count" v-if="item.project_count !== undefined">
        关联项目: {{ item.project_count }} 个
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { PlanningItem } from './types'

defineProps<{
  planningItems: PlanningItem[]
}>()
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

.plan-item {
  padding: 10px 12px;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  border: 1px solid #ebeef5;
  transition: all 0.2s;
}

.plan-item:hover {
  border-color: #409eff;
  background: #ecf5ff;
}

.plan-item-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.plan-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.plan-item-desc {
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plan-item-count {
  font-size: 12px;
  color: #606266;
}
</style>
