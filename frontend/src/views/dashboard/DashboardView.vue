<template>
  <div class="dashboard">
    <!-- ═══════════ 顶部主CTA区域 ═══════════ -->
    <div class="dashboard-header">
      <div>
        <h1 class="page-title">策划主线</h1>
        <p class="page-subtitle">产品策划全生命周期管理 — 从立项到发布一站式追踪</p>
      </div>
      <div class="header-actions">
        <button class="refresh-btn" @click="refreshAll" :class="{ spinning: loading || planLoading }">
          <el-icon :size="18"><Refresh /></el-icon>
          <span>刷新</span>
        </button>
        <el-button type="primary" size="large" @click="goToNewPlan">
          <el-icon class="btn-icon"><Plus /></el-icon>
          新建产品策划
        </el-button>
      </div>
    </div>

    <!-- ═══════════ 策划KPI卡片行 ═══════════ -->
    <section class="dashboard-section">
      <div class="section-header">
        <div class="section-badge" style="background: var(--c-primary-light, #ecf5ff); color: var(--c-primary, #409eff);">
          <el-icon :size="16"><DataAnalysis /></el-icon>
        </div>
        <h2 class="section-title">策划概览</h2>
        <span class="section-count">4 项指标</span>
      </div>

      <div class="stats-grid">
        <div class="stat-card" @click="router.push('/product-plans')">
          <div class="stat-icon" style="background: #409eff12; color: #409eff;">
            <el-icon :size="22"><Folder /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value" style="color: #409eff;">{{ planKPIs.inProgress }}</div>
            <div class="stat-label">进行中策划</div>
          </div>
          <div class="stat-arrow">
            <el-icon :size="14"><ArrowRight /></el-icon>
          </div>
        </div>
        <div class="stat-card" @click="router.push('/product-plans')">
          <div class="stat-icon" style="background: #e6a23c12; color: #e6a23c;">
            <el-icon :size="22"><Coin /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value stat-value-sm" style="color: #e6a23c;">
              <span v-for="(count, stage) in planKPIs.stageDistribution" :key="stage" class="stage-chip">
                {{ stageLabel(stage) }}<em>{{ count }}</em>
              </span>
            </div>
            <div class="stat-label">各阶段分布</div>
          </div>
          <div class="stat-arrow">
            <el-icon :size="14"><ArrowRight /></el-icon>
          </div>
        </div>
        <div class="stat-card" @click="router.push('/approvals/proposals')">
          <div class="stat-icon" style="background: #67c23a12; color: #67c23a;">
            <el-icon :size="22"><Clock /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value" style="color: #67c23a;">{{ planKPIs.pendingApprovals }}</div>
            <div class="stat-label">待审批</div>
          </div>
          <div class="stat-arrow">
            <el-icon :size="14"><ArrowRight /></el-icon>
          </div>
        </div>
        <div class="stat-card" @click="router.push('/product-plans')">
          <div class="stat-icon" style="background: #90939912; color: #909399;">
            <el-icon :size="22"><CircleCheck /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value" style="color: #909399;">{{ planKPIs.monthlyCompleted }}</div>
            <div class="stat-label">本月完成数</div>
          </div>
          <div class="stat-arrow">
            <el-icon :size="14"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══════════ BI多维图表 ═══════════ -->
    <section class="dashboard-section">
      <div class="section-header">
        <div class="section-badge" style="background: var(--c-primary-light, #ecf5ff); color: var(--c-primary, #409eff);">
          <el-icon :size="16"><TrendCharts /></el-icon>
        </div>
        <h2 class="section-title">策划多维分析</h2>
        <div class="filter-bar">
          <el-date-picker
            v-model="biDateRange"
            type="monthrange"
            range-separator="至"
            start-placeholder="开始月份"
            end-placeholder="结束月份"
            value-format="YYYY-MM"
            format="YYYY-MM"
            :clearable="true"
            :disabled="biLoading"
            @change="onBiDateChange"
            size="default"
          />
        </div>
      </div>

      <div class="charts-row">
        <!-- 趋势折线图 -->
        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">立项趋势</span>
          </div>
          <ChartContainer :loading="biLoading" :isEmpty="biTrendEmpty" height="300">
            <BiChart
              type="line"
              :data="biTrendData"
              nameKey="month"
              valueKey="count"
              :height="300"
              :showLegend="false"
              area
              smooth
            />
          </ChartContainer>
        </div>
        <!-- 转化漏斗图 -->
        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">转化漏斗</span>
          </div>
          <ChartContainer :loading="biLoading" :isEmpty="biFunnelEmpty" height="300">
            <FunnelChart
              :data="biFunnelData"
              :height="300"
            />
          </ChartContainer>
        </div>
      </div>

      <div class="charts-row">
        <!-- 分布饼图 -->
        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">市场分布</span>
          </div>
          <ChartContainer :loading="biLoading" :isEmpty="biDistEmpty" height="300">
            <BiChart
              type="pie"
              :data="biDistData"
              nameKey="name"
              valueKey="value"
              :height="300"
              donut
            />
          </ChartContainer>
        </div>
        <div class="chart-card chart-card-empty" />
      </div>
    </section>

    <!-- ═══════════ 最近策划卡片列表 ═══════════ -->
    <section class="dashboard-section">
      <div class="section-header">
        <div class="section-badge" style="background: var(--c-warning-light, #fdf6ec); color: var(--c-warning, #e6a23c);">
          <el-icon :size="16"><List /></el-icon>
        </div>
        <h2 class="section-title">最近策划</h2>
        <button class="table-link" @click="router.push('/product-plans')">
          查看全部 <el-icon :size="12"><ArrowRight /></el-icon>
        </button>
      </div>

      <div class="plan-card-list">
        <div v-if="recentPlans.length === 0" class="empty-state-small">
          <p>暂无策划数据</p>
        </div>
        <div
          v-for="plan in recentPlans"
          :key="plan.id"
          class="plan-card"
          @click="goToPlan(plan)"
        >
          <div class="plan-card-left">
            <div class="plan-card-name">{{ plan.name }}</div>
            <div class="plan-card-meta">
              <el-tag :type="stageTagType(plan.status)" size="small" effect="plain">
                {{ stageLabel(plan.status) }}
              </el-tag>
              <span v-if="plan.series" class="plan-card-series">{{ plan.series }}</span>
              <span v-if="plan.market" class="plan-card-market">{{ plan.market }}</span>
            </div>
          </div>
          <div class="plan-card-right">
            <span v-if="nextActionForPlan(plan)" class="next-action-badge">
              {{ nextActionForPlan(plan) }}
            </span>
            <el-icon :size="14" class="plan-card-arrow"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══════════ L1: System Health ═══════════ -->
    <section class="dashboard-section">
      <div class="section-header">
        <div class="section-badge">
          <el-icon :size="16"><DataAnalysis /></el-icon>
        </div>
        <h2 class="section-title">体系健康度</h2>
        <span class="section-count">{{ Object.keys(L1Cards).length }} 项指标</span>
      </div>
      
      <div class="stats-grid">
        <div 
          v-for="(item, key) in L1Cards" 
          :key="key" 
          class="stat-card"
          :class="{ 'has-action': true }"
          @click="drillDown(key)"
        >
          <div class="stat-icon" :style="{ background: item.color + '12', color: item.color }">
            <el-icon :size="22">
              <component :is="item.icon" />
            </el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value" :style="{ color: item.color }">{{ healthData?.[key] ?? '-' }}</div>
            <div class="stat-label">{{ item.label }}</div>
          </div>
          <div class="stat-arrow">
            <el-icon :size="14"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>

      <div v-if="isL1Empty" class="empty-guide-banner">
        <el-icon :size="20"><InfoFilled /></el-icon>
        <span>暂无产品数据，👉 <router-link to="/products" class="guide-link">前往产品主线创建</router-link></span>
      </div>

      <div class="charts-row">
        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">产品状态分布</span>
          </div>
          <PieChart :data="productStatusData" :height="260" />
        </div>
        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">穿透分析预览</span>
          </div>
          <div class="penetration-preview">
            <div v-if="!penetrationData" class="empty-state">
              <el-icon :size="32" color="var(--c-text-tertiary)"><Connection /></el-icon>
              <p>暂无穿透数据</p>
            </div>
            <div v-else class="penetration-chain">
              <div v-for="(chain, idx) in penetrationChains" :key="idx" class="chain-row">
                <span 
                  v-for="(node, nidx) in chain" 
                  :key="nidx" 
                  class="chain-node"
                  :class="node.type"
                >
                  {{ node.label }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══════════ L2: Project Operations ═══════════ -->
    <section class="dashboard-section">
      <div class="section-header">
        <div class="section-badge" style="background: var(--c-success-light); color: var(--c-success);">
          <el-icon :size="16"><TrendCharts /></el-icon>
        </div>
        <h2 class="section-title">项目运营</h2>
        <span class="section-count">{{ Object.keys(L2Cards).length }} 项指标</span>
      </div>
      
      <div class="stats-grid">
        <div 
          v-for="(item, key) in L2Cards" 
          :key="key" 
          class="stat-card"
          @click="drillDown(key)"
        >
          <div class="stat-icon" :style="{ background: getL2CardColor(key, item.color) + '12', color: getL2CardColor(key, item.color) }">
            <el-icon :size="22">
              <component :is="item.icon" />
            </el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value" :style="{ color: getL2CardColor(key, item.color) }">{{ opsData?.[key] ?? '-' }}</div>
            <div class="stat-label">{{ item.label }}</div>
          </div>
          <div class="stat-arrow">
            <el-icon :size="14"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>

      <div class="charts-row">
        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">项目状态分布</span>
          </div>
          <BarChart :data="projectStatusData" :height="260" />
        </div>
        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">最近30天趋势</span>
          </div>
          <LineChart :data="trendsData" :height="260" area />
        </div>
      </div>

      <div class="table-section">
        <div class="table-header">
          <h3 class="table-title">近期项目</h3>
          <button class="table-link" @click="router.push('/projects')">
            查看全部 <el-icon :size="12"><ArrowRight /></el-icon>
          </button>
        </div>
        <div class="project-list">
          <div 
            v-for="project in projectList.slice(0, 5)" 
            :key="project.id"
            class="project-row"
            @click="goToProject(project)"
          >
            <div class="project-info">
              <div class="project-code">{{ project.code }}</div>
              <div class="project-name">{{ project.name }}</div>
            </div>
            <div class="project-meta">
              <span class="project-status" :class="statusType(project.status)">
                {{ statusLabel(project.status) }}
              </span>
              <span class="project-date">{{ project.target_end_date }}</span>
            </div>
          </div>
          <div v-if="projectList.length === 0" class="empty-state-small">
            <p>暂无项目数据</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══════════ AC R&D Metrics ═══════════ -->
    <section class="dashboard-section">
      <div class="section-header">
        <div class="section-badge" style="background: var(--c-warning-light); color: var(--c-warning);">
          <el-icon :size="16"><Cpu /></el-icon>
        </div>
        <h2 class="section-title">空调研发指标</h2>
        <span class="section-count">{{ Object.keys(L3Cards).length }} 项指标</span>
      </div>

      <!-- Error state -->
      <div v-if="acError" class="empty-state section-empty">
        <el-icon :size="48" color="var(--c-danger)"><CircleCloseFilled /></el-icon>
        <p class="empty-title">数据加载失败</p>
        <p class="empty-desc">无法获取空调研发指标数据，请检查网络连接后重试</p>
        <button class="action-btn primary" @click="fetchDashboard">重新加载</button>
      </div>

      <!-- Empty state -->
      <div v-else-if="isACEmpty && !loading" class="empty-state section-empty">
        <el-icon :size="48" color="var(--c-text-tertiary)"><InfoFilled /></el-icon>
        <p class="empty-title">暂无研发指标数据</p>
        <p class="empty-desc">空调研发指标数据为空，请前往「项目管理」录入研发阶段数据</p>
        <button class="action-btn primary" @click="router.push('/projects')">前往项目管理</button>
      </div>

      <!-- Normal -->
      <template v-else>
      <div class="stats-grid">
        <div 
          v-for="(item, key) in L3Cards" 
          :key="key" 
          class="stat-card"
          @click="drillDown(key)"
        >
          <div class="stat-icon" :style="{ background: item.color + '12', color: item.color }">
            <el-icon :size="22">
              <component :is="item.icon" />
            </el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value" :style="{ color: item.color }">{{ acMetrics?.[key] ?? '-' }}</div>
            <div class="stat-label">{{ item.label }}</div>
          </div>
          <div class="stat-arrow">
            <el-icon :size="14"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>

      <div class="charts-row">
        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">研发阶段进度</span>
          </div>
          <BarChart :data="phaseProgressData" :height="260" />
        </div>
        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">测试通过率 vs 问题关闭率</span>
          </div>
          <LineChart :data="acTrendData" :height="260" />
        </div>
      </div>
      </template>
    </section>

    <!-- ═══════════ L3: Penetration Analysis ═══════════ -->
    <section class="dashboard-section">
      <div class="section-header">
        <div class="section-badge" style="background: var(--c-info-light); color: var(--c-info);">
          <el-icon :size="16"><Search /></el-icon>
        </div>
        <h2 class="section-title">穿透分析</h2>
      </div>
      
      <div class="penetration-card">
        <div v-if="!penetrationData" class="empty-state">
          <el-icon :size="48" color="var(--c-text-tertiary)"><Connection /></el-icon>
          <p class="empty-title">暂无穿透数据</p>
          <p class="empty-desc">前往「产品主线」创建产品和版本关联后，即可查看穿透分析链路</p>
          <div class="empty-actions">
            <button class="action-btn primary" @click="router.push('/products')">前往产品主线</button>
            <button class="action-btn" @click="fetchDashboard">刷新数据</button>
          </div>
        </div>
        <div v-else>
          <TreeChart :data="penetrationTreeData" :height="400" orient="TB" />
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  DataAnalysis, TrendCharts, Search, Connection, ArrowRight, Refresh,
  Cpu, InfoFilled, CircleCloseFilled, Plus, Folder, Coin, Clock,
  CircleCheck, List,
} from '@element-plus/icons-vue'
import api from '../../api'
import PieChart from '../../components/charts/PieChart.vue'
import BarChart from '../../components/charts/BarChart.vue'
import LineChart from '../../components/charts/LineChart.vue'
import ChartContainer from '../../components/ChartContainer.vue'
import FunnelChart from '../../components/charts/FunnelChart.vue'
import BiChart from '../../components/BiChart.vue'
import type { TableRow, ChartDataPoint } from '@/types/common'

interface PlanNode {
  id: string | number
  name?: string
  status?: string
  phase?: string
  products?: ProductNode[]
}
interface ProductNode {
  id: string | number
  name?: string
  versions?: VersionNode[]
}
interface VersionNode {
  id: string | number
  name?: string
  version_no?: string
  boms?: BomNode[]
}
interface BomNode {
  id: string | number
  name?: string
  bom_no?: string
}
interface ChainLink {
  label: string
  type: string
}
interface PenetrationRoot {
  project_name?: string
  products?: Array<{
    name?: string
    versions?: Array<{
      version_no?: string
      boms?: Array<{
        bom_no?: string
      }>
    }>
  }>
}

const router = useRouter()
const loading = ref(false)
const planLoading = ref(false)

// ── 策划阶段常量（复用 PlanningCenter 定义）──
const STAGE_ORDER = ['draft', 'competitor', 'definition', 'costing', 'tech_input', 'project_init', 'approved', 'released']
const STAGE_LABELS: Record<string, string> = {
  draft: '草稿', competitor: '竞品分析', definition: '产品定义',
  costing: '成本目标', tech_input: '技术方案', project_init: '立项审批',
  approved: '已批准', released: '已发布',
}
const STAGE_TAGS: Record<string, string> = {
  draft: 'info', competitor: 'primary', definition: '',
  costing: 'warning', tech_input: 'primary', project_init: 'warning',
  approved: 'success', released: '',
}
function stageLabel(s: string): string { return STAGE_LABELS[s] || s }
function stageTagType(s: string): string { return STAGE_TAGS[s] || 'info' }

// ── 产品策划数据 ──
const allPlans = ref<PlanNode[]>([])
interface PlanKPIs {
  inProgress: number
  stageDistribution: Record<string, number>
  pendingApprovals: number
  monthlyCompleted: number
}
const planKPIs = ref<PlanKPIs>({
  inProgress: 0,
  stageDistribution: {},
  pendingApprovals: 0,
  monthlyCompleted: 0,
})

const recentPlans = computed(() => {
  // 取最近5条，按 updated_at 或 created_at 降序
  const sorted = [...allPlans.value].sort((a, b) => {
    const da = a.updated_at || a.created_at || ''
    const db = b.updated_at || b.created_at || ''
    return db.localeCompare(da)
  })
  return sorted.slice(0, 5)
})

function nextActionForPlan(plan: PlanNode): string {
  // 根据阶段计算下一步动作提示
  const stage = plan.status || 'draft'
  const idx = STAGE_ORDER.indexOf(stage)
  if (idx === -1) return ''
  if (stage === 'released') return '已发布 ✓'
  const nextStage = STAGE_ORDER[idx + 1]
  if (!nextStage) return ''
  return `推进至 ${STAGE_LABELS[nextStage] || nextStage}`
}

async function fetchProductPlanSummary() {
  planLoading.value = true
  try {
    // 获取前100条数据用于仪表盘统计
    const res = await api.get('/product-plans', { params: { page: 1, page_size: 100 } })
    const items: TableRow[] = res.data.items || []
    allPlans.value = items

    // 计算KPI
    const inProgressStages = ['draft', 'competitor', 'definition', 'costing', 'tech_input', 'project_init']
    const inProgress = items.filter(p => inProgressStages.includes(p.status)).length

    // 按阶段分布
    const stageDistribution: Record<string, number> = {}
    items.forEach(p => {
      const s = p.status || 'draft'
      stageDistribution[s] = (stageDistribution[s] || 0) + 1
    })

    // 本月完成数（status=released 且 updated_at 在本月内）
    const now = new Date()
    const thisMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    const monthlyCompleted = items.filter(p => {
      if (p.status !== 'released') return false
      const updated = (p.updated_at || p.created_at || '').substring(0, 7)
      return updated === thisMonth
    }).length

    planKPIs.value = {
      inProgress,
      stageDistribution,
      pendingApprovals: Number(opsData.value?.pending_approvals_count) || 0,
      monthlyCompleted,
    }
  } catch {
    // 产品策划数据接口失败不影响已有面板
    console.warn('[Dashboard] fetchProductPlanSummary failed, using empty data')
    allPlans.value = []
  } finally {
    planLoading.value = false
  }
}

function goToNewPlan() {
  router.push('/product-plans')
}
function goToPlan(plan: PlanNode) {
  router.push(`/product-plans/${plan.id}`)
}

// ── 原有L1/L2/L3卡片定义 ──
const L1Cards = {
  total_platforms: { label: '平台总数', color: '#0284c7', icon: 'Monitor' },
  total_products: { label: '产品总数', color: '#059669', icon: 'Goods' },
  total_versions: { label: '版本总数', color: '#d97706', icon: 'List' },
  active_projects: { label: '进行中项目', color: '#dc2626', icon: 'Folder' },
}

const L2Cards = {
  project_count: { label: '项目总数', color: '#0284c7', icon: 'Folder' },
  on_time_rate: { label: '按时完成率', color: '#059669', icon: 'CircleCheck' },
  overdue_count: { label: '超期项目', color: '#dc2626', icon: 'Warning' },
  pending_approvals_count: { label: '待审批', color: '#d97706', icon: 'Clock' },
}

const L3Cards = {
  phase_progress: { label: '研发阶段进度', color: '#0284c7', icon: 'Timer' },
  test_pass_rate: { label: '测试通过率', color: '#059669', icon: 'CircleCheck' },
  issue_close_rate: { label: '问题关闭率', color: '#d97706', icon: 'WarnTriangleFilled' },
  cost_execution_rate: { label: '成本执行率', color: '#7c3aed', icon: 'Money' },
  generalization_rate: { label: '通用化率', color: '#0891b2', icon: 'Grid' },
}

const healthData = ref<Record<string, string>>({})
const opsData = ref<Record<string, string>>({})
const acMetrics = ref<Record<string, string>>({})
const acError = ref(false)
const penetrationData = ref<PenetrationRoot | null>(null)
const projectList = ref<TableRow[]>([])

const isL1Empty = computed(() => {
  const keys = Object.keys(L1Cards)
  if (!healthData.value || Object.keys(healthData.value).length === 0) return true
  return keys.every(k => {
    const v = healthData.value[k]
    return v === undefined || v === null || v === '0' || Number(v) === 0 || v === ''
  })
})

const isACEmpty = computed(() => {
  if (acError.value) return false // error is not "empty"
  const keys = Object.keys(L3Cards)
  if (!acMetrics.value || Object.keys(acMetrics.value).length === 0) return true
  return keys.every(k => {
    const v = acMetrics.value[k]
    return v === undefined || v === null || v === '0' || Number(v) === 0 || v === '' || v === '0%' || v === '0.0%'
  })
})

const trendsData = ref<{ name: string; value: number }[]>([])
const productStatusData = ref<{ name: string; value: number }[]>([])
const projectStatusData = ref<{ name: string; value: number }[]>([])
const phaseProgressData = ref<{ name: string; value: number }[]>([])
const acTrendData = ref<{ name: string; value: number }[]>([])

// ── BI多维图表数据 ──
interface BiTrendItem { month: string; count: number }
interface BiFunnelItem { name: string; value: number }
interface BiDistItem { name: string; value: number }

const biLoading = ref(false)
const biDateRange = ref<[string, string] | null>(null)

const biTrendData = ref<BiTrendItem[]>([])
const biFunnelData = ref<BiFunnelItem[]>([])
const biDistData = ref<BiDistItem[]>([])

const biTrendEmpty = computed(() => biTrendData.value.length === 0)
const biFunnelEmpty = computed(() => biFunnelData.value.length === 0)
const biDistEmpty = computed(() => biDistData.value.length === 0)

const statusMap: Record<string, { type: string; label: string }> = {
  planning: { type: 'info', label: '规划中' },
  active: { type: 'active', label: '进行中' },
  delayed: { type: 'warning', label: '已延期' },
  completed: { type: 'success', label: '已完成' },
  cancelled: { type: 'danger', label: '已取消' },
}

function statusType(s: string) {
  return statusMap[s]?.type || 'info'
}
function statusLabel(s: string) {
  return statusMap[s]?.label || s
}

function getL2CardColor(key: string, defaultColor: string): string {
  if (key === 'pending_approvals_count') {
    const count = Number(opsData.value?.[key]) || 0
    return count > 0 ? '#d97706' : '#059669'  // warning : success
  }
  return defaultColor
}

const penetrationTreeData = computed(() => {
  if (!penetrationData.value) return { name: '无数据', children: [] }
  const p = penetrationData.value
  return {
    name: p.project_name || '项目',
    children: (p.products || []).map((prod: ProductNode) => ({
      name: prod.name || '产品',
      children: (prod.versions || []).map((ver: VersionNode) => ({
        name: ver.version_no || '版本',
        children: (ver.boms || []).map((bom: BomNode) => ({
          name: bom.bom_no || 'BOM',
        })),
      })),
    })),
  }
})

const penetrationChains = computed(() => {
  if (!penetrationData.value) return []
  const chains: ChainLink[][] = []
  const p = penetrationData.value
  ;(p.products || []).forEach((prod: ProductNode) => {
    ;(prod.versions || []).forEach((ver: VersionNode) => {
      chains.push([
        { label: p.project_name || '项目', type: 'primary' },
        { label: prod.name || '产品', type: 'success' },
        { label: ver.version_no || '版本', type: 'warning' },
      ])
    })
  })
  return chains.slice(0, 5)
})

async function fetchDashboard() {
  loading.value = true
  acError.value = false
  try {
    const res = await api.get('/dashboard/summary')
    const data = res.data
    healthData.value = data.layer1_system_health ?? {}
    opsData.value = data.layer2_project_ops ?? {}
    acMetrics.value = data.layer4_ac_metrics ?? {}
    penetrationData.value = data.layer3_penetration ?? null
    projectList.value = data.layer2_project_ops?.recent_projects ?? []
    
    productStatusData.value = data.layer1_system_health?.product_status_distribution ?? []
    projectStatusData.value = data.layer2_project_ops?.project_status_distribution ?? []
    phaseProgressData.value = data.layer4_ac_metrics?.phase_progress ?? []
  } catch {
    // API 请求失败：标记错误状态，不使用硬编码 fallback 数据掩盖真实状态
    console.warn('[Dashboard] fetchDashboard failed, clearing all data')
    acError.value = true
    acMetrics.value = {}
    phaseProgressData.value = []
    productStatusData.value = []
    projectStatusData.value = []
    healthData.value = {}
    opsData.value = {}
    penetrationData.value = null
    projectList.value = []
  } finally {
    loading.value = false
  }
}

async function fetchTrends() {
  try {
    const res = await api.get('/dashboard/trends')
    const data = Array.isArray(res.data) ? res.data : []
    trendsData.value = data.map((d: ChartDataPoint) => ({ name: d.date, value: d.value }))
  } catch {
    console.warn('[Dashboard] fetchTrends failed, using empty data')
    trendsData.value = []
  }
}

// ── BI多维图表数据加载 ──

async function fetchBiTrend(startMonth?: string, endMonth?: string) {
  try {
    const params: Record<string, string> = {}
    if (startMonth) params.start_month = startMonth
    if (endMonth) params.end_month = endMonth
    const res = await api.get('/bi/trend', { params })
    biTrendData.value = (res.data?.items || []) as BiTrendItem[]
  } catch {
    console.warn('[Dashboard] fetchBiTrend failed, using empty data')
    biTrendData.value = []
  }
}

async function fetchBiFunnel() {
  try {
    const res = await api.get('/bi/funnel')
    biFunnelData.value = (res.data?.items || []) as BiFunnelItem[]
  } catch {
    console.warn('[Dashboard] fetchBiFunnel failed, using empty data')
    biFunnelData.value = []
  }
}

async function fetchBiDistribution() {
  try {
    const res = await api.get('/bi/distribution')
    biDistData.value = (res.data?.items || []) as BiDistItem[]
  } catch {
    console.warn('[Dashboard] fetchBiDistribution failed, using empty data')
    biDistData.value = []
  }
}

async function fetchBiCharts() {
  biLoading.value = true
  try {
    const startMonth = biDateRange.value?.[0]
    const endMonth = biDateRange.value?.[1]
    await Promise.all([
      fetchBiTrend(startMonth, endMonth),
      fetchBiFunnel(),
      fetchBiDistribution(),
    ])
  } finally {
    biLoading.value = false
  }
}

function onBiDateChange() {
  fetchBiCharts()
}

function refreshAll() {
  fetchDashboard()
  fetchTrends()
  fetchProductPlanSummary()
  fetchBiCharts()
}

function drillDown(key: string) {
  const routeMap: Record<string, string> = {
    total_platforms: '/products',
    total_products: '/products',
    total_versions: '/products',
    active_projects: '/projects',
    project_count: '/projects',
    on_time_rate: '/projects',
    overdue_count: '/projects',
    pending_approvals_count: '/approvals/proposals',
    phase_progress: '/projects',
    test_pass_rate: '/tests',
    issue_close_rate: '/projects',
    cost_execution_rate: '/projects',
    generalization_rate: '/projects',
  }
  const path = routeMap[key]
  if (path) router.push(path)
}

function goToProject(row: TableRow) {
  router.push({ path: '/projects', query: { highlight: row.id } })
}

onMounted(() => {
  fetchDashboard()
  fetchTrends()
  fetchProductPlanSummary()
  fetchBiCharts()
})
</script>

<style scoped>
.dashboard {
  max-width: 1200px;
  margin: 0 auto;
  animation: c-fadeIn 0.3s ease;
}

/* Dashboard Header */
.dashboard-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--c-border);
}
.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--c-text-primary);
  margin: 0 0 4px;
  letter-spacing: -0.5px;
  line-height: 1.2;
}
.page-subtitle {
  font-size: 14px;
  color: var(--c-text-secondary);
  margin: 0;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: var(--c-radius-md);
  border: 1px solid var(--c-border);
  background: var(--c-bg-card);
  color: var(--c-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--c-transition-fast);
}
.refresh-btn:hover {
  border-color: var(--c-accent);
  color: var(--c-accent);
  background: var(--c-accent-light);
}
.refresh-btn.spinning :deep(.el-icon) {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.btn-icon {
  margin-right: 4px;
}

/* Section */
.dashboard-section {
  margin-bottom: 40px;
  animation: c-fadeInUp 0.4s ease forwards;
}
.dashboard-section:nth-child(2) { animation-delay: 0.05s; }
.dashboard-section:nth-child(3) { animation-delay: 0.1s; }
.dashboard-section:nth-child(4) { animation-delay: 0.15s; }

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.section-badge {
  width: 32px;
  height: 32px;
  border-radius: var(--c-radius-sm);
  background: var(--c-info-light);
  color: var(--c-info);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.section-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--c-text-primary);
  margin: 0;
  letter-spacing: -0.3px;
  flex: 1;
}
.section-count {
  font-size: 13px;
  color: var(--c-text-tertiary);
  font-weight: 500;
  background: var(--c-bg-hover);
  padding: 4px 10px;
  border-radius: var(--c-radius-full);
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  background: var(--c-bg-card);
  border: 1px solid var(--c-border);
  border-radius: var(--c-radius-lg);
  transition: all var(--c-transition-base);
  cursor: pointer;
  position: relative;
}
.stat-card:hover {
  border-color: var(--c-border-dark);
  box-shadow: var(--c-shadow-md);
  transform: translateY(-1px);
}
.stat-card:active {
  transform: translateY(0);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--c-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--c-transition-fast);
}
.stat-card:hover .stat-icon {
  transform: scale(1.05);
}

.stat-content {
  flex: 1;
  min-width: 0;
}
.stat-value {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.5px;
  transition: color var(--c-transition-fast);
}
.stat-value-sm {
  font-size: 14px;
  line-height: 1.6;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
}
.stage-chip {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  font-weight: 500;
  background: var(--c-bg-hover);
  padding: 2px 6px;
  border-radius: var(--c-radius-sm);
}
.stage-chip em {
  font-style: normal;
  font-weight: 700;
  margin-left: 2px;
  color: inherit;
}
.stat-label {
  margin-top: 4px;
  font-size: 13px;
  color: var(--c-text-secondary);
  font-weight: 500;
}

.stat-arrow {
  color: var(--c-text-muted);
  transition: all var(--c-transition-fast);
  opacity: 0;
}
.stat-card:hover .stat-arrow {
  opacity: 1;
  color: var(--c-text-tertiary);
  transform: translateX(2px);
}

/* Charts Row */
.charts-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.chart-card {
  background: var(--c-bg-card);
  border: 1px solid var(--c-border);
  border-radius: var(--c-radius-lg);
  padding: 20px;
  transition: all var(--c-transition-base);
}
.chart-card:hover {
  border-color: var(--c-border-dark);
  box-shadow: var(--c-shadow);
}
.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text-primary);
}

/* Filter Bar */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* Chart Card Empty (spacer) */
.chart-card-empty {
  visibility: hidden;
}

/* Table Section */
.table-section {
  background: var(--c-bg-card);
  border: 1px solid var(--c-border);
  border-radius: var(--c-radius-lg);
  overflow: hidden;
}
.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border);
}
.table-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text-primary);
  margin: 0;
}
.table-link {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--c-accent);
  font-weight: 500;
  background: none;
  border: none;
  cursor: pointer;
  transition: all var(--c-transition-fast);
  padding: 4px 8px;
  border-radius: var(--c-radius-sm);
}
.table-link:hover {
  background: var(--c-accent-light);
}

.project-list {
  padding: 8px;
}
.project-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: var(--c-radius-md);
  cursor: pointer;
  transition: all var(--c-transition-fast);
  gap: 16px;
}
.project-row:hover {
  background: var(--c-bg-hover);
}
.project-row + .project-row {
  border-top: 1px solid var(--c-border-light);
}

.project-info {
  flex: 1;
  min-width: 0;
}
.project-code {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text-primary);
  font-family: var(--c-font-mono);
  margin-bottom: 2px;
}
.project-name {
  font-size: 13px;
  color: var(--c-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.project-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.project-status {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--c-radius-full);
}
.project-status.info {
  background: var(--c-info-light);
  color: var(--c-info);
}
.project-status.active {
  background: var(--c-accent-light);
  color: var(--c-accent);
}
.project-status.success {
  background: var(--c-success-light);
  color: var(--c-success);
}
.project-status.warning {
  background: var(--c-warning-light);
  color: var(--c-warning);
}
.project-status.danger {
  background: var(--c-danger-light);
  color: var(--c-danger);
}
.project-date {
  font-size: 12px;
  color: var(--c-text-tertiary);
  font-family: var(--c-font-mono);
}

/* ─── 策划卡片列表 ─── */
.plan-card-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.plan-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--c-bg-card);
  border: 1px solid var(--c-border);
  border-radius: var(--c-radius-lg);
  cursor: pointer;
  transition: all var(--c-transition-base);
  gap: 16px;
}
.plan-card:hover {
  border-color: var(--c-border-dark);
  box-shadow: var(--c-shadow-sm);
  transform: translateY(-1px);
}
.plan-card:active {
  transform: translateY(0);
}
.plan-card + .plan-card {
  margin-top: 0;
}

.plan-card-left {
  flex: 1;
  min-width: 0;
}
.plan-card-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--c-text-primary);
  margin-bottom: 6px;
  line-height: 1.3;
}
.plan-card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.plan-card-series {
  font-size: 12px;
  color: var(--c-text-tertiary);
  padding: 2px 6px;
  background: var(--c-bg-hover);
  border-radius: var(--c-radius-sm);
}
.plan-card-market {
  font-size: 12px;
  color: var(--c-text-tertiary);
  padding: 2px 6px;
  background: var(--c-bg-hover);
  border-radius: var(--c-radius-sm);
}

.plan-card-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.next-action-badge {
  font-size: 12px;
  font-weight: 500;
  color: var(--c-accent);
  background: var(--c-accent-light);
  padding: 4px 10px;
  border-radius: var(--c-radius-full);
  white-space: nowrap;
}
.plan-card-arrow {
  color: var(--c-text-muted);
  transition: all var(--c-transition-fast);
  opacity: 0;
}
.plan-card:hover .plan-card-arrow {
  opacity: 1;
  color: var(--c-text-tertiary);
  transform: translateX(2px);
}

/* Penetration */
.penetration-card {
  background: var(--c-bg-card);
  border: 1px solid var(--c-border);
  border-radius: var(--c-radius-lg);
  padding: 20px;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.penetration-card:hover {
  border-color: var(--c-border-dark);
}

.penetration-preview {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.penetration-chain {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}
.chain-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 8px 12px;
  background: var(--c-bg-hover);
  border-radius: var(--c-radius-md);
}
.chain-node {
  font-size: 13px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: var(--c-radius-sm);
}
.chain-node.primary {
  background: var(--c-info-light);
  color: var(--c-info);
}
.chain-node.success {
  background: var(--c-success-light);
  color: var(--c-success);
}
.chain-node.warning {
  background: var(--c-warning-light);
  color: var(--c-warning);
}

/* Empty States */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px;
  color: var(--c-text-tertiary);
}
.empty-state p {
  font-size: 14px;
  margin: 0;
}
.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--c-text-primary);
  margin: 0;
}
.empty-desc {
  font-size: 13px;
  color: var(--c-text-secondary);
  margin: 0;
  text-align: center;
  max-width: 360px;
  line-height: 1.5;
}
.empty-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}
.section-empty {
  min-height: 260px;
  border: 1px dashed var(--c-border);
  border-radius: var(--c-radius-lg);
  background: var(--c-bg-card);
}
.empty-guide-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  margin-bottom: 20px;
  background: var(--c-info-light);
  border: 1px solid var(--c-info);
  border-radius: var(--c-radius-md);
  color: var(--c-info);
  font-size: 14px;
}
.empty-guide-banner .guide-link {
  color: var(--c-accent);
  font-weight: 600;
  text-decoration: underline;
  cursor: pointer;
}
.empty-guide-banner .guide-link:hover {
  color: var(--c-accent-hover);
}
.empty-state-small {
  text-align: center;
  padding: 32px;
  color: var(--c-text-tertiary);
  font-size: 14px;
}

.action-btn {
  padding: 8px 16px;
  border-radius: var(--c-radius-md);
  border: 1px solid var(--c-border);
  background: var(--c-bg-card);
  color: var(--c-text-primary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--c-transition-fast);
  margin-top: 8px;
}
.action-btn:hover {
  border-color: var(--c-accent);
  color: var(--c-accent);
  background: var(--c-accent-light);
}
.action-btn.primary {
  background: var(--c-accent);
  color: #fff;
  border-color: var(--c-accent);
}
.action-btn.primary:hover {
  background: var(--c-accent-hover);
  border-color: var(--c-accent-hover);
}

/* Responsive */
@media (max-width: 768px) {
  .dashboard-header {
    flex-direction: column;
    gap: 16px;
  }
  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }
  .stats-grid {
    grid-template-columns: 1fr;
  }
  .charts-row {
    grid-template-columns: 1fr;
  }
  .project-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  .project-meta {
    width: 100%;
    justify-content: space-between;
  }
  .plan-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  .plan-card-right {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
