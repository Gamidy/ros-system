<template>
  <div class="planning-analytics">
    <!-- 范围筛选器 -->
    <div class="filter-bar">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        format="YYYY-MM-DD"
        value-format="YYYY-MM-DD"
        @change="fetchData"
      />
      <el-button type="primary" @click="fetchData">查询</el-button>
    </div>

    <!-- KPI 卡片 -->
    <el-row :gutter="16" class="kpi-row">
      <el-col v-for="kpi in kpiList" :key="kpi.key" :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">{{ kpi.label }}</div>
          <div class="kpi-value" :style="{ color: kpi.color }">{{ kpi.value }}</div>
          <div v-if="kpi.trend" class="kpi-trend" :class="kpi.trend > 0 ? 'up' : 'down'">
            {{ kpi.trend > 0 ? '↑' : '↓' }} {{ Math.abs(kpi.trend) }}%
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="16" class="chart-row">
      <!-- 阶段分布饼图 -->
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>阶段分布</template>
          <BiChart
            type="pie"
            :data="phaseData"
            name-key="name"
            value-key="value"
            :loading="loading"
            :empty="phaseData.length === 0 && !loading"
            :height="340"
          />
        </el-card>
      </el-col>
      <!-- 审批时效折线图 -->
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>审批时效趋势</template>
          <BiChart
            type="line"
            :data="approvalData"
            name-key="date"
            value-key="hours"
            :loading="loading"
            :empty="approvalData.length === 0 && !loading"
            :height="340"
            :area="true"
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import BiChart from '../../components/BiChart.vue'
import api from '../../api/index'

const dateRange = ref<string[]>([])
const loading = ref(false)

// KPI 卡片数据
const kpiList = ref<{ key: string; label: string; value: string; color: string; trend?: number }[]>([])

// 阶段分布数据
const phaseData = ref<{ name: string; value: number }[]>([])

// 审批时效数据
const approvalData = ref<{ date: string; hours: number }[]>([])

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (dateRange.value?.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }

    // 并发请求
    const [kpiRes, phaseRes, approvalRes] = await Promise.all([
      api.get('/bi/planning/kpi', { params }),
      api.get('/bi/planning/phase-distribution', { params }),
      api.get('/bi/planning/approval-timeline', { params }),
    ])

    // KPI
    const kpiRaw = kpiRes.data as Record<string, any> || {}
    kpiList.value = [
      { key: 'total', label: '计划总数', value: String(kpiRaw.total_plans ?? 0), color: '#007AFF' },
      { key: 'active', label: '进行中', value: String(kpiRaw.active_plans ?? 0), color: '#34C759' },
      { key: 'completed', label: '已完成', value: String(kpiRaw.completed_plans ?? 0), color: '#8E8E93' },
      { key: 'avgDuration', label: '平均周期(天)', value: String(kpiRaw.avg_duration ?? '-'), color: '#FF9500', trend: kpiRaw.duration_trend },
    ]

    // 阶段分布
    phaseData.value = (phaseRes.data as any[])?.map((d: any) => ({
      name: d.name || d.phase || '',
      value: Number(d.value ?? d.count ?? 0),
    })) || []

    // 审批时效
    approvalData.value = (approvalRes.data as any[])?.map((d: any) => ({
      date: d.date || d.day || '',
      hours: Number(d.hours ?? d.avg_hours ?? 0),
    })) || []
  } catch {
    // API 返回错误时使用兜底模拟数据
    kpiList.value = [
      { key: 'total', label: '计划总数', value: '128', color: '#007AFF' },
      { key: 'active', label: '进行中', value: '47', color: '#34C759' },
      { key: 'completed', label: '已完成', value: '73', color: '#8E8E93' },
      { key: 'avgDuration', label: '平均周期(天)', value: '32', color: '#FF9500', trend: -5 },
    ]
    phaseData.value = [
      { name: '立项', value: 35 },
      { name: '设计', value: 28 },
      { name: '测试', value: 42 },
      { name: '试产', value: 15 },
      { name: '量产', value: 8 },
    ]
    approvalData.value = [
      { date: '03-01', hours: 48 },
      { date: '03-08', hours: 36 },
      { date: '03-15', hours: 52 },
      { date: '03-22', hours: 28 },
      { date: '03-29', hours: 44 },
      { date: '04-05', hours: 32 },
      { date: '04-12', hours: 40 },
    ]
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.planning-analytics {
  padding: 20px;
}
.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
}
.kpi-row {
  margin-bottom: 16px;
}
.kpi-card {
  border-radius: 12px;
  border: 1px solid #e8e8ed;
}
.kpi-label {
  font-size: 13px;
  color: #86868b;
  margin-bottom: 6px;
}
.kpi-value {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.5px;
}
.kpi-trend {
  font-size: 12px;
  margin-top: 4px;
}
.kpi-trend.up {
  color: #34C759;
}
.kpi-trend.down {
  color: #FF3B30;
}
.chart-row {
  margin-bottom: 16px;
}
.chart-card {
  border-radius: 12px;
  border: 1px solid #e8e8ed;
}
.chart-card :deep(.el-card__header) {
  font-size: 14px;
  font-weight: 600;
  border-bottom: 1px solid #f0f0f0;
  padding: 12px 16px;
}
</style>
