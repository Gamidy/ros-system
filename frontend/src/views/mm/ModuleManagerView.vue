<template>
  <div class="dashboard">
    <!-- 负责模块概览 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-title">
          <el-icon size="20"><List /></el-icon>
          <span>负责模块概览</span>
        </div>
      </template>
      <el-row :gutter="16">
        <el-col :span="6">
          <div class="stat-card" style="border-left-color: #409eff">
            <div class="stat-value">{{ moduleOverview?.total_modules ?? '-' }}</div>
            <div class="stat-label">负责模块数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card" style="border-left-color: #67c23a">
            <div class="stat-value">{{ moduleOverview?.active_projects ?? '-' }}</div>
            <div class="stat-label">进行中项目</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card" style="border-left-color: #e6a23c">
            <div class="stat-value">{{ moduleOverview?.pending_tasks ?? '-' }}</div>
            <div class="stat-label">待办任务</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card" style="border-left-color: #f56c6c">
            <div class="stat-value">{{ moduleOverview?.overdue_items ?? '-' }}</div>
            <div class="stat-label">逾期项</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 待审批任务列表 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-title">
          <el-icon size="20"><Clock /></el-icon>
          <span>待审批任务列表</span>
        </div>
      </template>
      <el-table :data="pendingList" stripe style="width: 100%" v-if="pendingList.length">
        <el-table-column prop="id" label="编号" width="80" />
        <el-table-column prop="title" label="任务标题" min-width="160" />
        <el-table-column prop="module_name" label="所属模块" width="130" />
        <el-table-column prop="applicant" label="申请人" width="100" />
        <el-table-column prop="created_at" label="申请时间" width="160" />
        <el-table-column label="紧急程度" width="100">
          <template #default="{ row }">
            <el-tag :type="urgencyType(row.urgency)" size="small">{{ row.urgency ?? '普通' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleApprove(row)">审批</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无待审批任务" />
    </el-card>

    <!-- 模块项目进度简表 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-title">
          <el-icon size="20"><DataBoard /></el-icon>
          <span>模块项目进度简表</span>
        </div>
      </template>
      <el-table :data="moduleProjectList" stripe style="width: 100%" v-if="moduleProjectList.length">
        <el-table-column prop="code" label="项目编号" width="140" />
        <el-table-column prop="name" label="项目名称" min-width="160" />
        <el-table-column prop="module_name" label="模块名称" width="130" />
        <el-table-column prop="progress" label="进度" width="120">
          <template #default="{ row }">
            <el-progress :percentage="Number(row.progress) || 0" :status="progressStatus(row.progress)" />
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_end_date" label="目标完成" width="110" />
      </el-table>
      <el-empty v-else description="暂无模块项目数据" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const moduleOverview = ref<Record<string, any>>({})
const pendingList = ref<any[]>([])
const moduleProjectList = ref<any[]>([])

async function fetchData() {
  try {
    const [overviewRes, pendingRes] = await Promise.all([
      api.get('/dashboard/summary'),
      api.get('/approval/requests/pending'),
    ])
    // Extract module-relevant data from summary
    moduleOverview.value = overviewRes.data?.module_overview ?? {}
    pendingList.value = pendingRes.data?.items ?? pendingRes.data ?? []
    // Module project list — if summary doesn't contain it, fallback to projects endpoint
    moduleProjectList.value = overviewRes.data?.module_projects ?? []
  } catch {
    // Error handled by interceptor
  }
}

function urgencyType(u: string) {
  const map: Record<string, string> = {
    low: 'info',
    normal: '',
    medium: 'warning',
    high: 'danger',
    urgent: 'danger',
  }
  return map[u] || ''
}

function progressStatus(p: number) {
  if (p >= 100) return 'success'
  if (p > 0) return 'warning'
  return ''
}

function statusType(s: string) {
  const map: Record<string, string> = {
    planning: 'info',
    running: 'primary',
    delayed: 'warning',
    completed: 'success',
    cancelled: 'danger',
  }
  return map[s] || 'info'
}

function handleApprove(row: any) {
  ElMessage.info(`审批任务：${row.title}（功能待对接）`)
}

onMounted(fetchData)
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
