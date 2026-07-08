<template>
  <div class="risk-dashboard">
    <!-- ═══════ 三合一概览卡片 ═══════ -->
    <el-row :gutter="16" class="overview-row">
      <el-col :span="8">
        <el-card shadow="never" class="overview-card">
          <template #header>
            <div class="card-header">
              <el-icon size="18"><WarningFilled /></el-icon>
              <span>物料风险</span>
            </div>
          </template>
          <div class="card-body">
            <div class="risk-badge-row">
              <el-tag type="danger" size="small">高 {{ overview?.mq?.high_count ?? 0 }}</el-tag>
              <el-tag type="warning" size="small">中 {{ overview?.mq?.medium_count ?? 0 }}</el-tag>
              <el-tag type="success" size="small">低 {{ overview?.mq?.low_count ?? 0 }}</el-tag>
            </div>
            <div class="risk-level" v-if="overview?.mq?.risk_level">
              综合风险等级：
              <el-tag :type="riskTagType(overview.mq.risk_level)" effect="dark" size="small">
                {{ overview.mq.risk_level }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never" class="overview-card">
          <template #header>
            <div class="card-header">
              <el-icon size="18"><DataBoard /></el-icon>
              <span>制造就绪度</span>
            </div>
          </template>
          <div class="card-body">
            <div class="progress-ring-area">
              <el-progress
                type="circle"
                :percentage="Math.round((overview?.mrc?.avg_score ?? 0) * 100)"
                :status="progressStatus(overview?.mrc?.avg_score ?? 0)"
                :width="80"
                :stroke-width="8"
              />
              <span class="avg-label">平均分</span>
            </div>
            <div class="level-row" v-if="overview?.mrc?.level_distribution">
              <span v-for="(count, level) in overview.mrc.level_distribution" :key="level" class="level-item">
                {{ level }}: {{ count }}
              </span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never" class="overview-card">
          <template #header>
            <div class="card-header">
              <el-icon size="18"><Stamp /></el-icon>
              <span>认证看板</span>
            </div>
          </template>
          <div class="card-body">
            <div class="cdf-stats">
              <div class="cdf-stat">
                <span class="cdf-stat-value">{{ overview?.cdf?.mandatory_count ?? 0 }}</span>
                <span class="cdf-stat-label">强制认证数</span>
              </div>
              <div class="cdf-stat">
                <span class="cdf-stat-value">{{ overview?.cdf?.estimated_days ?? overview?.cdf?.avg_days ?? '-' }}</span>
                <span class="cdf-stat-label">预估天数</span>
              </div>
            </div>
            <div class="risk-level" v-if="overview?.cdf?.risk_level">
              风险等级：
              <el-tag :type="riskTagType(overview.cdf.risk_level)" effect="dark" size="small">
                {{ overview.cdf.risk_level }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ═══════ 详细面板（Tabs） ═══════ -->
    <el-card shadow="never" class="detail-card">
      <el-tabs v-model="activeTab" class="detail-tabs">
        <el-tab-pane label="物料风险评分 (MQ)" name="mq">
          <MQScorecardPanel />
        </el-tab-pane>
        <el-tab-pane label="制造就绪度 (MRC)" name="mrc">
          <MRCReadinessPanel />
        </el-tab-pane>
        <el-tab-pane label="认证看板 (CDF)" name="cdf">
          <CDFTimelinePanel />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'
import MQScorecardPanel from './MQScorecardPanel.vue'
import MRCReadinessPanel from './MRCReadinessPanel.vue'
import CDFTimelinePanel from './CDFTimelinePanel.vue'

const activeTab = ref('mq')
const overview = ref<Record<string, any>>({})

function riskTagType(level: string): string {
  const map: Record<string, string> = {
    high: 'danger',
    medium: 'warning',
    low: 'success',
    critical: 'danger',
  }
  return map[level?.toLowerCase()] || 'info'
}

function progressStatus(score: number): string {
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'exception'
}

async function fetchOverview() {
  try {
    const res = await api.get('/api/v2/dashboard/overview')
    overview.value = res.data ?? {}
  } catch {
    overview.value = {}
  }
}

onMounted(fetchOverview)
</script>

<style scoped>
.risk-dashboard {
  max-width: 1400px;
  margin: 0 auto;
}
.overview-row {
  margin-bottom: 16px;
}
.overview-card {
  border-radius: 8px;
  height: 100%;
}
.overview-card :deep(.el-card__body) {
  padding: 12px 16px;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 14px;
}
.card-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.risk-badge-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.risk-level {
  font-size: 13px;
  color: #606266;
  display: flex;
  align-items: center;
  gap: 6px;
}
.progress-ring-area {
  display: flex;
  align-items: center;
  gap: 12px;
}
.avg-label {
  font-size: 13px;
  color: #909399;
}
.level-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.level-item {
  font-size: 12px;
  color: #606266;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
}
.cdf-stats {
  display: flex;
  gap: 20px;
}
.cdf-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.cdf-stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}
.cdf-stat-label {
  font-size: 12px;
  color: #909399;
}
.detail-card {
  border-radius: 8px;
}
.detail-tabs {
  min-height: 400px;
}
</style>
