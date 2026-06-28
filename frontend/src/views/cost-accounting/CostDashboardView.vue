<template>
  <div class="cost-dashboard">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-select v-model="periodLimit" @change="fetchData" style="width: 180px">
        <el-option :value="6" label="最近 6 期" />
        <el-option :value="12" label="最近 12 期" />
        <el-option :value="24" label="最近 24 期" />
        <el-option :value="48" label="最近 48 期" />
      </el-select>
      <el-button type="primary" @click="fetchData">刷新</el-button>
    </div>

    <!-- KPI 卡片 -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :span="4">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">平均效率评分</div>
          <div class="kpi-value" :style="{ color: scoreColor(kpi.avg_score) }">
            {{ kpi.avg_score ?? '-' }}
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">最高分</div>
          <div class="kpi-value" style="color:#67c23a">{{ kpi.highest_score ?? '-' }}</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">最低分</div>
          <div class="kpi-value" style="color:#f56c6c">{{ kpi.lowest_score ?? '-' }}</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">低效产品(&lt;60分)</div>
          <div class="kpi-value" :style="{ color: kpi.low_efficiency_count > 0 ? '#f56c6c' : '#67c23a' }">
            {{ kpi.low_efficiency_count ?? '-' }}
          </div>
          <div class="kpi-unit">共 {{ kpi.product_count ?? 0 }} 个产品</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">已分析产品数</div>
          <div class="kpi-value">{{ kpi.product_count ?? '-' }}</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">趋势方向</div>
          <div class="kpi-value">
            <el-tag v-if="kpi.trend_direction === 'up'" type="success" size="large">上升 📈</el-tag>
            <el-tag v-else-if="kpi.trend_direction === 'down'" type="danger" size="large">下降 📉</el-tag>
            <el-tag v-else type="info" size="large">持平 ➡️</el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区：趋势 + 分布 -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="14">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <span>各期间平均效率趋势</span>
            <span class="chart-hint">折线=平均评分，60分合格线</span>
          </template>
          <BiChart
            type="line"
            :data="trendData"
            name-key="period_name"
            value-key="avg_score"
            :smooth="true"
            :area="false"
            :loading="loading"
            :empty="trendData.length === 0"
            empty-text="暂无趋势数据"
            :height="300"
          />
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <span>评分分布</span>
            <span class="chart-hint">各分数段产品数量</span>
          </template>
          <BiChart
            type="bar"
            :data="distData"
            name-key="range_label"
            value-key="count"
            :loading="loading"
            :empty="distData.length === 0"
            empty-text="暂无分布数据"
            :height="300"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 产品系列成本分布 -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="24">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <span>产品系列成本分布</span>
            <span class="chart-hint">各系列的平均成本和效率评分对比</span>
          </template>
          <BiChart
            type="bar"
            :data="seriesData"
            name-key="series"
            value-key="avg_score"
            :series="[{ name: '平均评分', key: 'avg_score' }, { name: '平均成本(元)', key: 'avg_cost' }]"
            :loading="loading"
            :empty="seriesData.length === 0"
            empty-text="暂无系列数据"
            :height="280"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 排名表 -->
    <el-row :gutter="16" class="table-row">
      <el-col :span="12">
        <el-card shadow="never" class="table-card">
          <template #header><span>🏆 最高效 Top 10</span></template>
          <el-table :data="topRanking" border stripe size="small" v-loading="loading" style="width:100%" max-height="360">
            <el-table-column type="index" width="40" label="#" />
            <el-table-column prop="plan_name" label="产品名称" min-width="120" show-overflow-tooltip />
            <el-table-column prop="plan_series" label="系列" width="80" />
            <el-table-column prop="cost_efficiency_score" label="评分" width="80" sortable>
              <template #default="{ row }">
                <el-tag :type="scoreTagType(row.cost_efficiency_score)" size="small">{{ row.cost_efficiency_score }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="variance_pct" label="差异率" width="80">
              <template #default="{ row }">
                <span :class="row.variance_pct > 0 ? 'over' : 'under'">{{ row.variance_pct > 0 ? '+' : '' }}{{ row.variance_pct }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="matched_btu" label="BTU" width="60" />
            <el-table-column prop="period_name" label="期间" width="100" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="table-card">
          <template #header><span>⚠️ 最低效 Top 10</span></template>
          <el-table :data="bottomRanking" border stripe size="small" v-loading="loading" style="width:100%" max-height="360">
            <el-table-column type="index" width="40" label="#" />
            <el-table-column prop="plan_name" label="产品名称" min-width="120" show-overflow-tooltip />
            <el-table-column prop="plan_series" label="系列" width="80" />
            <el-table-column prop="cost_efficiency_score" label="评分" width="80" sortable>
              <template #default="{ row }">
                <el-tag :type="scoreTagType(row.cost_efficiency_score)" size="small">{{ row.cost_efficiency_score }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="variance_pct" label="差异率" width="80">
              <template #default="{ row }">
                <span :class="row.variance_pct > 0 ? 'over' : 'under'">{{ row.variance_pct > 0 ? '+' : '' }}{{ row.variance_pct }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="actual_cost" label="实际成本" width="90">
              <template #default="{ row }">{{ formatMoney(row.actual_cost) }}</template>
            </el-table-column>
            <el-table-column prop="period_name" label="期间" width="100" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import BiChart from '../../components/BiChart.vue'
import { getCostDashboard } from '../../api/costAccounting'

/* ── 类型 ── */
interface KpiData {
  avg_score: number
  highest_score: number
  lowest_score: number
  product_count: number
  low_efficiency_count: number
  trend_direction: string
}
interface TrendItem { period_name: string; avg_score: number; product_count: number; avg_variance_pct: number }
interface SeriesItem { series: string; product_count: number; avg_cost: number; avg_score: number; avg_variance_pct: number }
interface RankingItem {
  product_plan_id: string; plan_name: string; plan_series: string
  cost_efficiency_score: number; variance_pct: number; matched_btu: string
  period_name: string; actual_cost: number; baseline_cost: number
}
interface DistItem { range_label: string; count: number; low: number; high: number }

/* ── 状态 ── */
const loading = ref(false)
const periodLimit = ref(12)
const kpi = ref<KpiData>({} as KpiData)
const trendData = ref<TrendItem[]>([])
const seriesData = ref<SeriesItem[]>([])
const topRanking = ref<RankingItem[]>([])
const bottomRanking = ref<RankingItem[]>([])
const distData = ref<DistItem[]>([])

/* ── 辅助 ── */
function scoreColor(s: number | undefined): string {
  if (s == null) return '#909399'
  if (s >= 80) return '#67c23a'
  if (s >= 60) return '#e6a23c'
  return '#f56c6c'
}
function scoreTagType(s: number): string {
  if (s >= 80) return 'success'
  if (s >= 60) return 'warning'
  return 'danger'
}
function formatMoney(v: number | undefined): string {
  if (v == null) return '-'
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/* ── 数据 ── */
async function fetchData() {
  loading.value = true
  try {
    const res: any = await getCostDashboard({ period_limit: periodLimit.value })
    const data = res?.data ?? res ?? {}
    kpi.value = data.kpi ?? {}
    trendData.value = (data.trend_by_period ?? []).map((d: TrendItem) => ({
      ...d,
      avg_score: Number(d.avg_score ?? 0),
    }))
    seriesData.value = (data.series_breakdown ?? []).map((d: SeriesItem) => ({
      ...d,
      avg_cost: Number(d.avg_cost ?? 0),
      avg_score: Number(d.avg_score ?? 0),
      avg_variance_pct: Number(d.avg_variance_pct ?? 0),
    }))
    const rank = data.ranking ?? {}
    topRanking.value = (rank.top ?? []).map(normalizeRank)
    bottomRanking.value = (rank.bottom ?? []).map(normalizeRank)
    distData.value = (data.distribution ?? []).map((d: DistItem) => ({
      ...d,
      count: Number(d.count ?? 0),
    }))
  } catch (e: unknown) {
    console.error('成本看板加载失败', e)
    kpi.value = {} as KpiData
    trendData.value = []
    seriesData.value = []
    topRanking.value = []
    bottomRanking.value = []
    distData.value = []
  } finally {
    loading.value = false
  }
}

function normalizeRank(d: RankingItem): RankingItem {
  return {
    ...d,
    cost_efficiency_score: Number(d.cost_efficiency_score ?? 0),
    variance_pct: Number(d.variance_pct ?? 0),
    actual_cost: Number(d.actual_cost ?? 0),
    baseline_cost: Number(d.baseline_cost ?? 0),
  }
}

onMounted(fetchData)
</script>

<style scoped>
.cost-dashboard {
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
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.5px;
}
.kpi-unit {
  font-size: 12px;
  color: #86868b;
  margin-top: 2px;
}
.chart-row {
  margin-bottom: 16px;
}
.chart-card {
  border-radius: 12px;
  border: 1px solid #e8e8ed;
}
.chart-hint {
  font-size: 12px;
  color: #86868b;
  margin-left: 12px;
  font-weight: normal;
}
.table-row {
  margin-bottom: 16px;
}
.table-card {
  border-radius: 12px;
  border: 1px solid #e8e8ed;
}
.over {
  color: #f56c6c;
  font-weight: 500;
}
.under {
  color: #67c23a;
  font-weight: 500;
}
</style>
