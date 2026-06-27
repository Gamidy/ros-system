<template>
  <div class="review-dashboard">
    <!-- ═══════════ 页面头部 ═══════════ -->
    <div class="dashboard-header">
      <div>
        <h1 class="page-title">复盘看板</h1>
        <p class="page-subtitle">P4复盘汇总视图 — 评分分布、趋势、常见问题、多版本对比</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" @click="fetchData" :class="{ spinning: loading }">刷新</el-button>
      </div>
    </div>

    <!-- ═══════════ 时间筛选器 ═══════════ -->
    <el-card shadow="never" class="filter-card">
      <div class="filter-bar">
        <span class="filter-label">复盘时间：</span>
        <el-date-picker
          v-model="monthRange"
          type="monthrange"
          range-separator="至"
          start-placeholder="起始月"
          end-placeholder="结束月"
          format="YYYY-MM"
          value-format="YYYY-MM"
          :clearable="true"
          @change="onFilterChange"
          style="width: 300px"
        />
        <el-button :type="hasFilter ? 'primary' : ''" @click="clearFilter" :disabled="!hasFilter">
          重置
        </el-button>
      </div>
    </el-card>

    <!-- ═══════════ 综述 / 对比 切换 ═══════════ -->
    <div class="mode-switch-bar">
      <el-radio-group v-model="viewMode" size="small">
        <el-radio-button value="summary">📈 汇总视图</el-radio-button>
        <el-radio-button value="compare">🔍 对比模式</el-radio-button>
      </el-radio-group>
    </div>

    <!-- ── 对比模式 ── -->
    <template v-if="viewMode === 'compare'">
      <ReviewCompare
        v-if="compareItems.length > 0"
        :items="compareItems"
        @back="exitCompare"
      />
      <div v-else class="compare-select-section">
        <!-- 复盘列表（多选） -->
        <el-card shadow="never" class="select-card">
          <template #header>
            <div class="select-header">
              <span>选择复盘进行对比（至少选 2 个）</span>
              <div class="select-actions">
                <el-button size="small" @click="clearSelection">清空</el-button>
                <el-button size="small" type="primary" :disabled="selectedReviewIds.length < 2" @click="doCompare">
                  对比 ({{ selectedReviewIds.length }})
                </el-button>
              </div>
            </div>
          </template>
          <el-table
            ref="reviewTableRef"
            :data="reviewList"
            stripe
            border
            size="small"
            style="width:100%"
            @selection-change="onSelectionChange"
          >
            <el-table-column type="selection" width="44" />
            <el-table-column prop="plan_name" label="策划名称" min-width="180" show-overflow-tooltip />
            <el-table-column prop="plan_series" label="产品系列" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.plan_series" size="small" effect="plain">{{ row.plan_series }}</el-tag>
                <span v-else class="no-data">—</span>
              </template>
            </el-table-column>
            <el-table-column prop="review_date" label="复盘日期" width="120" />
            <el-table-column prop="rating" label="评分" width="100" align="center">
              <template #default="{ row }">
                <el-rate v-if="row.rating" :model-value="row.rating" disabled :max="5" size="small" />
                <span v-else class="no-data">—</span>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="loadingReviewList" style="text-align:center;padding:24px">
            <el-skeleton :rows="3" animated />
          </div>
          <div v-else-if="reviewList.length === 0" style="text-align:center;padding:24px;color:#909399;font-size:13px">
            暂无复盘记录
          </div>
        </el-card>
      </div>
    </template>

    <!-- ── 汇总视图（原有） ── -->
    <template v-if="viewMode === 'summary'">
      <!-- KPI 卡片 -->
      <el-row :gutter="16" class="kpi-row">
        <el-col :span="6">
          <el-card shadow="never" class="kpi-card">
            <div class="kpi-label">复盘总数</div>
            <div class="kpi-value">{{ summary.totalReviews ?? '-' }}</div>
            <div class="kpi-subtitle">已提交的复盘记录</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never" class="kpi-card">
            <div class="kpi-label">平均评分</div>
            <div class="kpi-value" :style="{ color: avgRatingColor }">{{ summary.avgRating ?? '-' }}</div>
            <div class="kpi-subtitle">满分 5.0</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never" class="kpi-card">
            <div class="kpi-label">完成率</div>
            <div class="kpi-value" :style="{ color: completionColor }">{{ completionRateText }}</div>
            <div class="kpi-subtitle">已复盘/应复盘</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never" class="kpi-card">
            <div class="kpi-label">常见问题</div>
            <div class="kpi-value">{{ summary.topIssueCount ?? '-' }}</div>
            <div class="kpi-subtitle">TOP 关键词数</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 图表区域 -->
      <el-row :gutter="16" class="chart-row">
        <el-col :span="12">
          <el-card shadow="never" class="chart-card">
            <template #header>
              <div class="chart-header">
                <span class="chart-title">评分分布</span>
                <span class="chart-desc">各评分等级数量（1-5分）</span>
              </div>
            </template>
            <BiChart
              type="bar"
              :data="ratingChartData"
              name-key="label"
              value-key="value"
              :loading="loading"
              :empty="ratingChartData.length === 0 && !loading"
              empty-text="暂无复盘评分数据"
              :height="340"
            />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never" class="chart-card">
            <template #header>
              <div class="chart-header">
                <span class="chart-title">月度评分趋势</span>
                <span class="chart-desc">每月平均评分变化</span>
              </div>
            </template>
            <BiChart
              type="line"
              :data="trendChartData"
              name-key="month"
              value-key="avg_rating"
              :loading="loading"
              :empty="trendChartData.length === 0 && !loading"
              empty-text="暂无月度趋势数据"
              :height="340"
              :area="true"
              :smooth="true"
            />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="chart-row">
        <el-col :span="8">
          <el-card shadow="never" class="chart-card">
            <template #header>
              <div class="chart-header">
                <span class="chart-title">完成率</span>
                <span class="chart-desc">已复盘数 / 应复盘数</span>
              </div>
            </template>
            <BiChart
              type="pie"
              :data="completionChartData"
              name-key="name"
              value-key="value"
              :loading="loading"
              :empty="completionChartData.length === 0 && !loading"
              empty-text="暂无完成率数据"
              :height="300"
              :donut="true"
              :show-legend="true"
            />
          </el-card>
        </el-col>
        <el-col :span="16">
          <el-card shadow="never" class="chart-card">
            <template #header>
              <div class="chart-header">
                <span class="chart-title">常见问题 Top10</span>
                <span class="chart-desc">从"经验教训"字段提取的高频关键词</span>
              </div>
            </template>
            <div v-if="loading" class="loading-placeholder">
              <el-skeleton :rows="5" animated />
            </div>
            <div v-else-if="commonIssues.length === 0" class="empty-placeholder">
              <el-empty description="暂无常见问题数据" :image-size="60" />
            </div>
            <div v-else class="issues-content">
              <el-table :data="commonIssues" stripe style="width: 100%" size="small" max-height="260">
                <el-table-column type="index" label="#" width="48" />
                <el-table-column prop="word" label="关键词" min-width="140">
                  <template #default="{ row }">
                    <span class="issue-word">{{ row.word }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="count" label="出现次数" width="120" sortable>
                  <template #default="{ row }">
                    <el-tag :type="getTagType(row.count)" effect="plain" size="small">
                      {{ row.count }} 次
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="频次占比" min-width="140">
                  <template #default="{ row }">
                    <div class="issue-progress-wrapper">
                      <el-progress
                        :percentage="getIssuePercent(row.count)"
                        :stroke-width="14"
                        :show-text="false"
                        :color="getProgressColor(row.count)"
                      />
                      <span class="issue-percent-text">{{ getIssuePercent(row.count) }}%</span>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import BiChart from '../../components/BiChart.vue'
import ReviewCompare from './ReviewCompare.vue'
import api from '../../api/index'
import { listAllReviews, compareReviews } from '../../api/productPlan'
import type { ReviewListItem, ReviewCompareItem } from '../../api/productPlan'

// ── 类型定义 ──

interface TrendItem {
  month: string
  avg_rating: number
  count: number
}

interface CommonIssue {
  word: string
  count: number
}

interface CompletionRate {
  total: number
  reviewed: number
  rate: number
}

interface ReviewSummary {
  rating_distribution: Record<string, number>
  monthly_trend: TrendItem[]
  common_issues: CommonIssue[]
  completion_rate: CompletionRate
}

// ── 状态 ──

const loading = ref(false)
const monthRange = ref<string[]>([])
const data = ref<ReviewSummary | null>(null)

// ── D4-5 对比模式 ──

const viewMode = ref<'summary' | 'compare'>('summary')
const reviewList = ref<ReviewListItem[]>([])
const selectedReviewIds = ref<string[]>([])
const compareItems = ref<ReviewCompareItem[]>([])
const loadingReviewList = ref(false)

function onSelectionChange(rows: ReviewListItem[]) {
  selectedReviewIds.value = rows.map(r => r.id)
}

function clearSelection() {
  selectedReviewIds.value = []
}

async function doCompare() {
  const ids = selectedReviewIds.value
  if (ids.length < 2) {
    ElMessage.warning('请至少选择 2 个复盘进行对比')
    return
  }
  try {
    const res = await compareReviews(ids)
    compareItems.value = (res.data as { items: ReviewCompareItem[] }).items
  } catch (err) {
    console.error('对比查询失败', err)
    ElMessage.error('对比查询失败')
  }
}

function exitCompare() {
  compareItems.value = []
  viewMode.value = 'compare'
}

async function fetchReviewList() {
  loadingReviewList.value = true
  try {
    const res = await listAllReviews()
    reviewList.value = (res.data as { items: ReviewListItem[] }).items
  } catch (err) {
    console.error('获取复盘列表失败', err)
    reviewList.value = []
  } finally {
    loadingReviewList.value = false
  }
}

// ── 计算属性 ──

const hasFilter = computed(() => monthRange.value?.length === 2)

const summary = computed(() => {
  const d = data.value
  if (!d) return { totalReviews: '-', avgRating: '-', topIssueCount: '-' }

  const totalReviews = d.monthly_trend.reduce((sum, item) => sum + item.count, 0)
  const ratings = Object.values(d.rating_distribution).reduce((sum, v) => sum + v, 0)
  const avgRating = ratings > 0
    ? (
        Object.entries(d.rating_distribution).reduce((sum, [k, v]) => sum + parseInt(k) * v, 0) / ratings
      ).toFixed(2)
    : '-'

  return {
    totalReviews: String(totalReviews),
    avgRating,
    topIssueCount: String(d.common_issues.length),
  }
})

const avgRatingColor = computed(() => {
  const val = parseFloat(summary.value.avgRating)
  if (isNaN(val)) return '#909399'
  if (val >= 4) return '#67C23A'
  if (val >= 3) return '#E6A23C'
  return '#F56C6C'
})

const completionRateText = computed(() => {
  const d = data.value?.completion_rate
  if (!d) return '-'
  return `${d.rate}% (${d.reviewed}/${d.total})`
})

const completionColor = computed(() => {
  const d = data.value?.completion_rate
  if (!d) return '#909399'
  if (d.rate >= 80) return '#67C23A'
  if (d.rate >= 50) return '#E6A23C'
  return '#F56C6C'
})

// ── 评分分布图表数据 ──

const ratingLabels: Record<string, string> = {
  '1': '1分',
  '2': '2分',
  '3': '3分',
  '4': '4分',
  '5': '5分',
}

const ratingChartData = computed(() => {
  const dist = data.value?.rating_distribution
  if (!dist) return []
  return Object.entries(dist).map(([key, value]) => ({
    label: ratingLabels[key] || `${key}分`,
    value,
  }))
})

// ── 趋势图表数据 ──

const trendChartData = computed(() => {
  return data.value?.monthly_trend ?? []
})

// ── 完成率图表数据 ──

const completionChartData = computed(() => {
  const d = data.value?.completion_rate
  if (!d) return []
  const reviewed = d.reviewed
  const remaining = Math.max(0, d.total - d.reviewed)
  return [
    { name: '已复盘', value: reviewed },
    { name: '未复盘', value: remaining },
  ]
})

// ── 常见问题 ──

const commonIssues = computed(() => {
  return data.value?.common_issues ?? []
})

function getIssuePercent(count: number): number {
  const maxCount = Math.max(...commonIssues.value.map(i => i.count), 1)
  return Math.round((count / maxCount) * 100)
}

function getTagType(count: number): string {
  if (count >= 5) return 'danger'
  if (count >= 3) return 'warning'
  return 'info'
}

function getProgressColor(count: number): string {
  const maxCount = Math.max(...commonIssues.value.map(i => i.count), 1)
  const ratio = count / maxCount
  if (ratio >= 0.8) return '#F56C6C'
  if (ratio >= 0.5) return '#E6A23C'
  return '#67C23A'
}

// ── 数据获取 ──

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (monthRange.value?.length === 2) {
      params.start_month = monthRange.value[0]
      params.end_month = monthRange.value[1]
    }
    const res = await api.get('/bi/review-summary', { params })
    data.value = res.data as ReviewSummary
  } catch (err) {
    console.error('获取复盘汇总数据失败', err)
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  fetchData()
}

function clearFilter() {
  monthRange.value = []
  fetchData()
}

// ── 生命周期 ──

onMounted(() => {
  fetchData()
})

// ── D4-5: 进入对比模式时加载复盘列表 ──

watch(viewMode, (mode) => {
  if (mode === 'compare') {
    fetchReviewList()
  }
})
</script>

<style scoped>
.review-dashboard {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1d1d1f;
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: #86868b;
  margin: 4px 0 0;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.spinning :deep(.el-icon) {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ── 模式切换 ── */

.mode-switch-bar {
  margin-bottom: 16px;
}

/* ── 对比模式 ── */

.compare-select-section {
  margin-top: 0;
}

.select-card {
  border-radius: 12px;
}

.select-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 500;
}

.select-actions {
  display: flex;
  gap: 8px;
}

.no-data {
  color: #c0c4cc;
}

.filter-card {
  margin-bottom: 16px;
  border-radius: 12px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 14px;
  color: #1d1d1f;
  font-weight: 500;
  white-space: nowrap;
}

.kpi-row {
  margin-bottom: 16px;
}

.kpi-card {
  border-radius: 12px;
  text-align: center;
  padding: 8px 0;
}

.kpi-label {
  font-size: 13px;
  color: #86868b;
  margin-bottom: 6px;
}

.kpi-value {
  font-size: 32px;
  font-weight: 700;
  color: #1d1d1f;
  line-height: 1.2;
}

.kpi-subtitle {
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 4px;
}

.chart-row {
  margin-bottom: 16px;
}

.chart-card {
  border-radius: 12px;
  margin-bottom: 16px;
}

.chart-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
}

.chart-desc {
  font-size: 12px;
  color: #909399;
}

.issues-content {
  min-height: 260px;
}

.issue-word {
  font-weight: 500;
  color: #303133;
}

.issue-progress-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.issue-percent-text {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  min-width: 36px;
}

.loading-placeholder,
.empty-placeholder {
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
