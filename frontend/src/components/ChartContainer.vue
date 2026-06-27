<template>
  <div class="chart-container" :style="{ height: height + 'px' }">
    <!-- 加载态 -->
    <div v-if="loading" class="chart-overlay">
      <el-skeleton :rows="4" animated />
    </div>
    <!-- 空数据态 -->
    <div v-else-if="isEmpty" class="chart-overlay chart-empty">
      <el-empty :description="emptyText" :image-size="80" />
    </div>
    <!-- 错误态 -->
    <div v-else-if="hasError" class="chart-overlay chart-error">
      <el-icon :size="32" color="#f56c6c"><WarningFilled /></el-icon>
      <p class="error-text">{{ errorText }}</p>
      <el-button size="small" @click="$emit('retry')">重试</el-button>
    </div>
    <!-- 图表插槽 -->
    <div v-show="!loading && !isEmpty && !hasError" class="chart-body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { WarningFilled } from '@element-plus/icons-vue'

withDefaults(defineProps<{
  loading?: boolean
  isEmpty?: boolean
  hasError?: boolean
  emptyText?: string
  errorText?: string
  height?: number
}>(), {
  loading: false,
  isEmpty: false,
  hasError: false,
  emptyText: '暂无数据',
  errorText: '数据加载失败',
  height: 320,
})

defineEmits<{
  retry: []
}>()
</script>

<style scoped>
.chart-container {
  position: relative;
  width: 100%;
}
.chart-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.6);
  z-index: 1;
  gap: 8px;
}
.chart-empty {
  background: transparent;
}
.chart-body {
  width: 100%;
  height: 100%;
}
.error-text {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--c-text-secondary, #86868b);
}
</style>
