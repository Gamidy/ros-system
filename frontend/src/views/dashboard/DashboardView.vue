<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <div>
        <h1 class="page-title">仪表盘</h1>
        <p class="page-subtitle">实时查看系统运行状态和关键指标</p>
      </div>
      <button class="refresh-btn" @click="refreshAll" :class="{ spinning: loading }">
        <el-icon :size="18"><Refresh /></el-icon>
        <span>刷新</span>
      </button>
    </div>

    <!-- L1: System Health -->
    <section class="dashboard-section">
      <div class="section-header">
        <div class="section-badge">
          <el-icon :size="16"><DataAnalysis /></el-icon>
        </div>
        <h2 class="section-title">体系健康度</h2>
        <span class="section-count">4 项指标</span>
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

    <!-- L2: Project Operations -->
    <section class="dashboard-section">
      <div class="section-header">
        <div class="section-badge" style="background: var(--c-success-light); color: var(--c-success);">
          <el-icon :size="16"><TrendCharts /></el-icon>
        </div>
        <h2 class="section-title">项目运营</h2>
        <span class="section-count">3 项指标</span>
      </div>
      
      <div class="stats-grid">
        <div 
          v-for="(item, key) in L2Cards" 
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
            <div class="stat-value" :style="{ color: item.color }">{{ opsData?.[key] ?? '-' }}</div>
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

    <!-- AC R&D Metrics (New) -->
    <section class="dashboard-section">
      <div class="section-header">
        <div class="section-badge" style="background: var(--c-warning-light); color: var(--c-warning);">
          <el-icon :size="16"><Cpu /></el-icon>
        </div>
        <h2 class="section-title">空调研发指标</h2>
        <span class="section-count">5 项指标</span>
      </div>
      
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
    </section>

    <!-- L3: Penetration Analysis -->
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
          <p>暂无穿透数据</p>
          <button class="action-btn" @click="fetchDashboard">刷新数据</button>
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
import { DataAnalysis, TrendCharts, Search, Connection, ArrowRight, Refresh, Cpu } from '@element-plus/icons-vue'
import api from '../../api'
import PieChart from '../../components/charts/PieChart.vue'
import BarChart from '../../components/charts/BarChart.vue'
import LineChart from '../../components/charts/LineChart.vue'

const router = useRouter()
const loading = ref(false)

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
const penetrationData = ref<any>(null)
const projectList = ref<any[]>([])
const trendsData = ref<{ name: string; value: number }[]>([])
const productStatusData = ref<{ name: string; value: number }[]>([])
const projectStatusData = ref<{ name: string; value: number }[]>([])
const phaseProgressData = ref<{ name: string; value: number }[]>([])
const acTrendData = ref<{ name: string; value: number }[]>([])

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

const penetrationTreeData = computed(() => {
  if (!penetrationData.value) return { name: '无数据', children: [] }
  const p = penetrationData.value
  return {
    name: p.project_name || '项目',
    children: (p.products || []).map((prod: any) => ({
      name: prod.name || '产品',
      children: (prod.versions || []).map((ver: any) => ({
        name: ver.version_no || '版本',
        children: (ver.boms || []).map((bom: any) => ({
          name: bom.bom_no || 'BOM',
        })),
      })),
    })),
  }
})

const penetrationChains = computed(() => {
  if (!penetrationData.value) return []
  const chains: any[] = []
  const p = penetrationData.value
  ;(p.products || []).forEach((prod: any) => {
    ;(prod.versions || []).forEach((ver: any) => {
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
  try {
    const res = await api.get('/dashboard/summary')
    const data = res.data
    healthData.value = data.layer1_system_health ?? {}
    opsData.value = data.layer2_project_ops ?? {}
    acMetrics.value = data.layer4_ac_metrics ?? {}
    penetrationData.value = data.layer3_penetration ?? null
    projectList.value = data.layer2_project_ops?.recent_projects ?? []
    
    productStatusData.value = data.layer1_system_health?.product_status_distribution ?? [
      { name: '开发中', value: 12 }, { name: '已发布', value: 8 }, { name: '生产中', value: 15 }, { name: '退役', value: 3 },
    ]
    projectStatusData.value = data.layer2_project_ops?.project_status_distribution ?? [
      { name: '规划中', value: 5 }, { name: '进行中', value: 12 }, { name: '已延期', value: 2 }, { name: '已完成', value: 8 },
    ]
    phaseProgressData.value = data.layer4_ac_metrics?.phase_progress ?? [
      { name: '立项', value: 100 }, { name: '方案', value: 100 }, { name: '详细设计', value: 45 },
      { name: '手板', value: 0 }, { name: '模具', value: 0 }, { name: '测试', value: 0 }, { name: '试产', value: 0 },
    ]
  } catch {
    // Error handled by interceptor
    // Fallback data for AC metrics
    acMetrics.value = {
      phase_progress: '45%',
      test_pass_rate: '82%',
      issue_close_rate: '78%',
      cost_execution_rate: '91%',
      generalization_rate: '76%',
    }
    phaseProgressData.value = [
      { name: '立项', value: 100 }, { name: '方案', value: 100 }, { name: '详细设计', value: 45 },
      { name: '手板', value: 0 }, { name: '模具', value: 0 }, { name: '测试', value: 0 }, { name: '试产', value: 0 },
    ]
    acTrendData.value = [
      { name: 'W1', value: 75 }, { name: 'W2', value: 78 }, { name: 'W3', value: 82 }, { name: 'W4', value: 80 },
    ]
  } finally {
    loading.value = false
  }
}

async function fetchTrends() {
  try {
    const res = await api.get('/dashboard/trends')
    const data = res.data ?? []
    trendsData.value = data.map((d: any) => ({ name: d.date, value: d.value }))
  } catch {
    trendsData.value = [
      { name: 'D-30', value: 2 }, { name: 'D-25', value: 3 }, { name: 'D-20', value: 1 },
      { name: 'D-15', value: 4 }, { name: 'D-10', value: 2 }, { name: 'D-5', value: 5 }, { name: '今天', value: 3 },
    ]
  }
}

function refreshAll() {
  fetchDashboard()
  fetchTrends()
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
    phase_progress: '/projects',
    test_pass_rate: '/tests',
    issue_close_rate: '/projects',
    cost_execution_rate: '/projects',
    generalization_rate: '/projects',
  }
  const path = routeMap[key]
  if (path) router.push(path)
}

function goToProject(row: any) {
  router.push({ path: '/projects', query: { highlight: row.id } })
}

onMounted(() => {
  fetchDashboard()
  fetchTrends()
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

/* Responsive */
@media (max-width: 768px) {
  .dashboard-header {
    flex-direction: column;
    gap: 16px;
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
}
</style>
