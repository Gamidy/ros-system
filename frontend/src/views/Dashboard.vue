<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6" v-for="stat in stats" :key="stat.title">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon" :style="{ background: stat.color }">
              <el-icon :size="28" color="white">
                <component :is="stat.icon" />
              </el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-title">{{ stat.title }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="mt-20">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>待处理任务</span>
              <el-button text>查看全部</el-button>
            </div>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="task in pendingTasks"
              :key="task.id"
              :type="task.type"
              :timestamp="task.time"
            >
              {{ task.content }}
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>快捷入口</span>
            </div>
          </template>
          <div class="quick-actions">
            <el-button
              v-for="action in quickActions"
              :key="action.path"
              :icon="action.icon"
              type="primary"
              plain
              @click="$router.push(action.path)"
            >
              {{ action.label }}
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Box, Connection, Switch, Folder, Document, Timer } from '@element-plus/icons-vue'

const stats = ref([
  { title: '物料总数', value: '1,234', icon: Box, color: '#409EFF' },
  { title: 'BOM数量', value: '567', icon: Connection, color: '#67C23A' },
  { title: '待审批变更', value: '12', icon: Switch, color: '#E6A23C' },
  { title: '进行中项目', value: '8', icon: Folder, color: '#F56C6C' }
])

const pendingTasks = ref([
  { id: 1, content: 'ECR-2024-00001 待审批', type: 'warning', time: '2024-01-15 10:30' },
  { id: 2, content: '物料 PN-2024001 待发布', type: 'primary', time: '2024-01-15 09:15' },
  { id: 3, content: '项目 PRJ-2024-00001 里程碑到期', type: 'danger', time: '2024-01-14 16:00' },
  { id: 4, content: 'BOM 版本升级审核', type: 'success', time: '2024-01-14 11:20' }
])

const quickActions = ref([
  { label: '新建物料', path: '/materials', icon: Box },
  { label: '新建BOM', path: '/boms', icon: Connection },
  { label: '提交变更', path: '/changes', icon: Switch },
  { label: '新建项目', path: '/projects', icon: Folder }
])
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.mt-20 {
  margin-top: 20px;
}

.stat-card {
  margin-bottom: 20px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  line-height: 1.2;
}

.stat-title {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.quick-actions .el-button {
  flex: 1;
  min-width: 120px;
}
</style>
