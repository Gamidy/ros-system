<template>
  <el-card shadow="never">
    <template #header>
      <div class="graph-header">
        <span class="graph-title">变更影响图</span>
        <div class="graph-legend">
          <span
            v-for="item in LEGEND_ITEMS"
            :key="item.type"
            class="legend-item"
          >
            <span class="legend-dot" :style="{ background: item.color }" />
            {{ item.label }}
          </span>
        </div>
      </div>
    </template>

    <!-- 加载状态 -->
    <div v-if="store.graphLoading" class="graph-loading">
      <el-skeleton :rows="3" animated />
    </div>

    <!-- 错误状态 + 重试 -->
    <el-alert
      v-else-if="store.graphError"
      :title="store.graphError"
      type="error"
      show-icon
      :closable="false"
    >
      <template #footer>
        <el-button size="small" type="primary" @click="fetchGraph">重试</el-button>
      </template>
    </el-alert>

    <!-- 空状态 -->
    <el-empty
      v-else-if="!store.graphData || store.graphData.nodes.length === 0"
      description="暂无影响图数据"
      :image-size="80"
    />

    <!-- ECharts 容器 -->
    <div
      v-else
      ref="chartRef"
      class="graph-chart"
    />
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useCIEv2Store } from '../../../stores/ci_v2'
import { initChart, disposeChart } from '../../../utils/chart'
import type { EChartsOption } from 'echarts'

// ── Props ─────────────────────────────────────────────────────────

const props = defineProps<{
  ecrId: number
}>()

// ── Store ─────────────────────────────────────────────────────────

const store = useCIEv2Store()

// ── Refs ──────────────────────────────────────────────────────────

const chartRef = ref<HTMLDivElement>()

// ── 节点类型颜色映射 ────────────────────────────────────────────

interface LegendItemDef {
  type: string
  label: string
  color: string
}

const NODE_TYPE_COLORS: Record<string, string> = {
  ecr: '#007AFF',
  eco: '#34C759',
  prototype: '#FF9500',
  bom: '#AF52DE',
  certification: '#5AC8FA',
  manufacturing: '#FF3B30',
  cost: '#8E8E93',
}

const NODE_TYPE_LABELS: Record<string, string> = {
  ecr: 'ECR',
  eco: 'ECO',
  prototype: '原型',
  bom: 'BOM',
  certification: '认证',
  manufacturing: '制造',
  cost: '成本',
}

const LEGEND_ITEMS: LegendItemDef[] = Object.entries(NODE_TYPE_COLORS).map(
  ([type, color]) => ({
    type,
    color,
    label: NODE_TYPE_LABELS[type] ?? type,
  })
)

// ── ECharts Option 构建 ──────────────────────────────────────────

function buildOption(): EChartsOption {
  const data = store.graphData
  if (!data) return {}

  // categories for legend interaction
  const categories = LEGEND_ITEMS.map((item) => ({
    name: item.label,
    itemStyle: { color: item.color },
  }))

  // nodes
  const nodes = data.nodes.map((node) => {
    const color = NODE_TYPE_COLORS[node.node_type] ?? '#8E8E93'
    const catIdx = LEGEND_ITEMS.findIndex((l) => l.type === node.node_type)
    const score = node.impact_score ?? 0
    return {
      id: node.id,
      name: node.label,
      value: score,
      category: catIdx >= 0 ? catIdx : -1,
      itemStyle: { color },
      symbolSize: Math.max(20, Math.min(60, 20 + score * 6)),
      label: {
        show: true,
        fontSize: 11,
        color: '#333',
        formatter: (p: { name: string }): string => p.name,
      },
    }
  })

  // edges
  const edges = data.edges.map((edge) => ({
    source: edge.source_id,
    target: edge.target_id,
    value: edge.weight ?? 1,
    label: {
      show: edge.label ? true : false,
      formatter: edge.label,
      fontSize: 10,
    },
    lineStyle: {
      width: Math.max(1, (edge.weight ?? 1) * 1.5),
      curveness: 0.3,
    },
  }))

  return {
    tooltip: {
      trigger: 'item',
      formatter(params: unknown): string {
        const d = (params as Record<string, unknown>).data as Record<string, unknown> || {}
        const raw = d.value
        const scoreLabel = typeof raw === 'number' ? raw.toFixed(1) : 'N/A'
        return `<strong>${String(d.name || '')}</strong><br/>影响评分: ${scoreLabel}`
      },
    },
    legend: {
      data: categories,
      top: 0,
      right: 0,
      orient: 'horizontal',
      textStyle: { fontSize: 12 },
      icon: 'circle',
    },
    animationDuration: 800,
    animationEasingUpdate: 'quinticInOut',
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        categories,
        data: nodes,
        edges,
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 10],
        force: {
          repulsion: 500,
          edgeLength: [80, 200],
          layoutAnimation: false,
          friction: 0.1,
          gravity: 0.1,
        },
        lineStyle: {
          color: 'target',
          curveness: 0.3,
          opacity: 0.7,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 3,
            opacity: 1,
          },
        },
        label: {
          show: true,
          position: 'bottom',
          fontSize: 11,
          color: '#555',
        },
      },
    ],
  }
}

// ── 渲染 / 更新 ─────────────────────────────────────────────────

function renderChart(): void {
  if (!chartRef.value || !store.graphData) return
  const option = buildOption()
  initChart(chartRef.value, option)
}

async function fetchGraph(): Promise<void> {
  await store.fetchImpactGraph(props.ecrId)
  // allow DOM to settle before rendering chart
  await new Promise((resolve) => setTimeout(resolve, 50))
  renderChart()
}

// ── Watchers ────────────────────────────────────────────────────

watch(
  () => props.ecrId,
  (newId: number, oldId: number): void => {
    if (newId && newId !== oldId) {
      fetchGraph()
    }
  }
)

// ── Lifecycle ───────────────────────────────────────────────────

onMounted(() => {
  fetchGraph()
})

onBeforeUnmount(() => {
  if (chartRef.value) {
    disposeChart(chartRef.value)
  }
})
</script>

<style scoped>
.graph-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.graph-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
}

.graph-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #606266;
  white-space: nowrap;
}

.legend-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.graph-chart {
  width: 100%;
  height: 420px;
}

.graph-loading {
  padding: 40px 20px;
}
</style>
