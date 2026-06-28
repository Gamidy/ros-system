<template>
  <el-card shadow="never" class="risk-score-card" v-loading="store.riskLoading">
    <template #header>
      <div class="card-header">
        <span>AI 风险评分</span>
        <el-tag
          v-if="store.riskScore"
          :color="levelConfig.color"
          class="level-tag"
        >
          {{ levelConfig.label }}
        </el-tag>
      </div>
    </template>

    <!-- 错误状态 -->
    <el-alert
      v-if="store.riskError"
      :title="store.riskError"
      type="error"
      show-icon
      :closable="false"
    >
      <template #action>
        <el-button size="small" type="danger" @click="handleRetry">重试</el-button>
      </template>
    </el-alert>

    <!-- 空状态 -->
    <el-empty
      v-else-if="!store.riskScore && !store.riskLoading"
      description="暂无风险评分数据"
      :image-size="80"
    />

    <!-- 主要内容 -->
    <template v-else-if="store.riskScore">
      <!-- 评分主区域 -->
      <div class="score-area">
        <span class="score-number">{{ store.riskScore.risk_score }}</span>
        <span class="score-unit">分</span>
        <span class="score-level" :style="{ color: levelConfig.color }">
          · {{ levelConfig.label }}风险
        </span>
      </div>

      <!-- 5 维信号雷达图 -->
      <div ref="radarChartRef" class="radar-chart" />

      <!-- 缓解建议 -->
      <div v-if="store.riskScore.mitigation_suggestions?.length" class="suggestions-section">
        <h4 class="suggestions-title">缓解建议</h4>
        <el-timeline>
          <el-timeline-item
            v-for="(suggestion, idx) in store.riskScore.mitigation_suggestions"
            :key="idx"
            :timestamp="`建议 ${idx + 1}`"
            placement="top"
          >
            {{ suggestion }}
          </el-timeline-item>
        </el-timeline>
      </div>
    </template>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import { useCIEv2Store } from '@/stores/ci_v2'
import { initChart, disposeChart } from '@/utils/chart'
import type { EChartsOption } from '@/utils/chart'

// ── 类型定义 ──────────────────────────────────────────

interface RiskLevelConfig {
  label: string
  color: string
}

interface RadarIndicator {
  name: string
  max: number
}

// ── Props ─────────────────────────────────────────────

const props = defineProps<{
  ecrId: number
}>()

// ── Store ─────────────────────────────────────────────

const store = useCIEv2Store()

// ── Template refs ─────────────────────────────────────

const radarChartRef = ref<HTMLDivElement | null>(null)

// ── 常量 ──────────────────────────────────────────────

const RISK_LEVEL_CONFIG: Record<string, RiskLevelConfig> = {
  LOW: { label: '低', color: '#67C23A' },
  MEDIUM: { label: '中', color: '#E6A23C' },
  HIGH: { label: '高', color: '#E67E22' },
  CRITICAL: { label: '严重', color: '#F56C6C' },
}

const DIMENSION_LABELS: Record<string, string> = {
  bom: 'BOM 变更',
  cert: '认证影响',
  proto: '样机影响',
  cost: '成本影响',
  hist: '历史波动',
}

// ── 计算属性 ──────────────────────────────────────────

const levelConfig = computed<RiskLevelConfig>(() => {
  const level: string = store.riskScore?.risk_level ?? ''
  return RISK_LEVEL_CONFIG[level] ?? { label: level, color: '#909399' }
})

// ── 雷达图 ────────────────────────────────────────────

function buildRadarIndicators(): RadarIndicator[] {
  return Object.entries(DIMENSION_LABELS).map(([, label]) => ({
    name: label,
    max: 100,
  }))
}

function buildRadarData(): number[] {
  const vector: Record<string, number> = store.riskScore?.risk_vector ?? {}
  return Object.keys(DIMENSION_LABELS).map((key: string) => vector[key] ?? 0)
}

function buildRadarOption(): EChartsOption {
  return {
    radar: {
      indicator: buildRadarIndicators(),
      center: ['50%', '50%'],
      radius: '70%',
      shape: 'circle',
      splitNumber: 4,
      axisName: {
        color: '#606266',
        fontSize: 12,
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(0,0,0,0.08)',
        },
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(0,0,0,0.02)', 'rgba(0,0,0,0.04)'],
        },
      },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: buildRadarData(),
            areaStyle: {
              color: 'rgba(91, 143, 249, 0.15)',
            },
            lineStyle: {
              color: '#5B8FF9',
              width: 2,
            },
            itemStyle: {
              color: '#5B8FF9',
            },
          },
        ],
        symbol: 'circle',
        symbolSize: 6,
      },
    ],
    tooltip: {
      trigger: 'item',
    },
  }
}

function renderChart(): void {
  if (!radarChartRef.value || !store.riskScore) return
  initChart(radarChartRef.value, buildRadarOption())
}

// ── 生命周期 ──────────────────────────────────────────

onMounted(() => {
  store.loadRiskScore(props.ecrId)
})

watch(
  () => store.riskScore,
  () => {
    nextTick(() => renderChart())
  },
)

onUnmounted(() => {
  if (radarChartRef.value) {
    disposeChart(radarChartRef.value)
  }
})

// ── 事件处理 ──────────────────────────────────────────

function handleRetry(): void {
  store.loadRiskScore(props.ecrId)
}
</script>

<style scoped>
.risk-score-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: 15px;
}

.level-tag {
  color: #fff;
  border: none;
  font-weight: 600;
}

.score-area {
  display: flex;
  align-items: baseline;
  justify-content: center;
  padding: 24px 0 20px;
}

.score-number {
  font-size: 56px;
  font-weight: 700;
  line-height: 1;
  color: #303133;
}

.score-unit {
  font-size: 20px;
  color: #909399;
  margin-left: 4px;
}

.score-level {
  font-size: 18px;
  font-weight: 500;
  margin-left: 8px;
}

.radar-chart {
  width: 100%;
  height: 300px;
  margin: 8px 0 16px;
}

.suggestions-section {
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.suggestions-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
</style>
