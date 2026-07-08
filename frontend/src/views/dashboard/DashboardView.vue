<template>
  <div class="dashboard">
    <!-- 第1层：系统健康度 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-title">
          <el-icon size="20"><DataAnalysis /></el-icon>
          <span>第1层 · 体系健康度</span>
        </div>
      </template>
      <el-row :gutter="16">
        <el-col :span="6" v-for="(item, key) in L1Cards" :key="key">
          <div class="stat-card" :style="{ borderLeftColor: item.color }">
            <div class="stat-value">{{ healthData?.[key] ?? '-' }}</div>
            <div class="stat-label">{{ item.label }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 第2层：项目运营 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-title">
          <el-icon size="20"><TrendCharts /></el-icon>
          <span>第2层 · 项目运营</span>
        </div>
      </template>
      <el-row :gutter="16">
        <el-col :span="8" v-for="(item, key) in L2Cards" :key="key">
          <div class="stat-card" :style="{ borderLeftColor: item.color }">
            <div class="stat-value">{{ opsData?.[key] ?? '-' }}</div>
            <div class="stat-label">{{ item.label }}</div>
          </div>
        </el-col>
      </el-row>
      <el-table :data="projectList" stripe style="margin-top: 16px" v-if="projectList.length">
        <el-table-column prop="code" label="项目编号" width="140" />
        <el-table-column prop="name" label="项目名称" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_end_date" label="目标完成" width="120" />
        <el-table-column prop="project_class" label="类别" width="80" />
      </el-table>
    </el-card>

    <!-- 第3层：穿透分析 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-title">
          <el-icon size="20"><Search /></el-icon>
          <span>第3层 · 穿透分析</span>
        </div>
      </template>
      <el-empty v-if="!penetrationData" description="暂无穿透数据" />
      <pre v-else>{{ JSON.stringify(penetrationData, null, 2) }}</pre>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'

const L1Cards = {
  total_platforms: { label: '平台总数', color: '#409eff' },
  total_products: { label: '产品总数', color: '#67c23a' },
  total_versions: { label: '版本总数', color: '#e6a23c' },
  active_projects: { label: '进行中项目', color: '#f56c6c' },
}

const L2Cards = {
  project_count: { label: '项目总数', color: '#409eff' },
  on_time_rate: { label: '按时完成率', color: '#67c23a' },
  overdue_count: { label: '超期项目', color: '#f56c6c' },
}

const healthData = ref<Record<string, string>>({})
const opsData = ref<Record<string, string>>({})
const penetrationData = ref(null)
const projectList = ref<any[]>([])

async function fetchDashboard() {
  try {
    const res = await api.get('/dashboard/summary')
    const data = res.data
    healthData.value = data.layer1_system_health ?? {}
    opsData.value = data.layer2_project_ops ?? {}
    penetrationData.value = data.layer3_penetration ?? null
    projectList.value = data.layer2_project_ops?.recent_projects ?? []
  } catch {
    // Error handled by interceptor
  }
}

function statusType(s: string) {
  const map: Record<string, string> = {
    planning: 'info', active: 'primary', delayed: 'warning',
    completed: 'success', cancelled: 'danger',
  }
  return map[s] || 'info'
}

onMounted(fetchDashboard)
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}
.section-card {
  margin-bottom: 16px;
}
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
  font-size: 16px;
}
.stat-card {
  padding: 16px;
  background: #fafafa;
  border-left: 4px solid #409eff;
  border-radius: 4px;
  text-align: center;
}
.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}
.stat-label {
  margin-top: 4px;
  font-size: 13px;
  color: #909399;
}
</style>
