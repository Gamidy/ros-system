<template>
  <div class="workspace-header">
    <h2>📋 产品经理工作台</h2>
    <div class="header-right">
      <el-radio-group
        :model-value="viewMode"
        size="small"
        @change="$emit('update:viewMode', $event)"
      >
        <el-radio-button value="workspace">📊 工作台</el-radio-button>
        <el-radio-button value="roadmap">🗺️ 路线图</el-radio-button>
      </el-radio-group>
      <span class="header-date">{{ currentDate }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

defineProps<{
  viewMode: 'workspace' | 'roadmap'
}>()

defineEmits<{
  'update:viewMode': [value: 'workspace' | 'roadmap']
}>()

const currentDate = computed(() => {
  const d = new Date()
  const weekDays = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${weekDays[d.getDay()]}`
})
</script>

<style scoped>
.workspace-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.workspace-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-date {
  font-size: 14px;
  color: #909399;
}
</style>
