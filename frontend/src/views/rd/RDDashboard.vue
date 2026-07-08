<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-title">
          <el-icon size="20"><DataAnalysis /></el-icon>
          <span>研发总监仪表盘</span>
        </div>
      </template>
      <el-row :gutter="16">
        <el-col :span="6">
          <div class="stat-card" style="border-left-color: #409eff">
            <div class="stat-value">{{ summaryData?.running_projects ?? '-' }}</div>
            <div class="stat-label">进行中项目数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card" style="border-left-color: #e6a23c">
            <div class="stat-value">{{ summaryData?.pending_approvals ?? '-' }}</div>
            <div class="stat-label">待审批数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card" style="border-left-color: #f56c6c">
            <div class="stat-value">{{ summaryData?.high_risk_projects ?? '-' }}</div>
            <div class="stat-label">高风险项目数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card" style="border-left-color: #67c23a">
            <div class="stat-value">{{ summaryData?.monthly_changes ?? '-' }}</div>
            <div class="stat-label">本月变更数</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 项目 M4/M6 Gate 状态（高风险区） -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-title">
          <el-icon size="20"><TrendCharts /></el-icon>
          <span>项目 M4/M6 Gate 状态 · 高风险区</span>
        </div>
      </template>
      <el-table :data="projectList" stripe style="width: 100%" v-if="projectList.length">
        <el-table-column prop="code" label="项目编号" width="140" />
        <el-table-column prop="name" label="项目名称" min-width="160" />
        <el-table-column label="M4 Gate" width="100">
          <template #default="{ row }">
            <el-tag :type="gateType(row.m4_gate)" size="small">{{ row.m4_gate ?? '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="M6 Gate" width="100">
          <template #default="{ row }">
            <el-tag :type="gateType(row.m6_gate)" size="small">{{ row.m6_gate ?? '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="风险等级" width="100">
          <template #default="{ row }">
            <el-tag :type="riskType(row.risk_level)" size="small">{{ row.risk_level ?? '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_end_date" label="目标完成" width="110" />
      </el-table>
      <el-empty v-else description="暂无项目数据" />
    </el-card>

    <!-- 图表区域 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-title">
          <el-icon size="20"><DataBoard /></el-icon>
          <span>数据概览</span>
        </div>
      </template>
      <el-row :gutter="16">
        <el-col :span="12">
          <div class="chart-placeholder">
            <div class="chart-title">项目分布</div>
            <div class="chart-body">图表占位 — 项目按类别/阶段分布</div>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="chart-placeholder">
            <div class="chart-title">变更趋势</div>
            <div class="chart-body">图表占位 — 本月变更趋势</div>
          </div>
        </el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="12">
          <div class="chart-placeholder">
            <div class="chart-title">Gate 通过率</div>
            <div class="chart-body">图表占位 — M4/M6 Gate 通过统计</div>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="chart-placeholder">
            <div class="chart-title">风险分布</div>
            <div class="chart-body">图表占位 — 项目风险等级分布</div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'

const summaryData = ref<Record<string, any>>({})
const projectList = ref<any[]>([])

async function fetchData() {
  try {
    const [summaryRes, projectRes] = await Promise.all([
      api.get('/dashboard/summary'),
      api.get('/projects', { params: { status: 'running' } }),
    ])
    summaryData.value = summaryRes.data ?? {}
    projectList.value = projectRes.data?.items ?? projectRes.data ?? []
  } catch {
    // Error handled by interceptor
  }
}

function gateType(gate: string) {
  const map: Record<string, string> = {
    passed: 'success',
    pending: 'warning',
    failed: 'danger',
    blocked: 'danger',
    closed: 'info',
  }
  return map[gate] || 'info'
}

function riskType(risk: string) {
  const map: Record<string, string> = {
    low: 'success',
    medium: 'warning',
    high: 'danger',
    critical: 'danger',
  }
  return map[risk] || 'info'
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
.chart-placeholder {
  background: #fafafa;
  border: 1px dashed #dcdfe6;
  border-radius: 4px;
  padding: 32px 16px;
  text-align: center;
  min-height: 160px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.chart-title {
  font-size: 14px;
  font-weight: bold;
  color: #606266;
  margin-bottom: 8px;
}
.chart-body {
  font-size: 12px;
  color: #c0c4cc;
}
</style>
