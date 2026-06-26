<template>
  <div class="pm-workspace">
    <!-- ═══════════════ 顶部标题 ═══════════════ -->
    <div class="workspace-header">
      <h2>📋 产品经理工作台</h2>
      <div class="header-right">
        <el-radio-group v-model="viewMode" size="small" @change="onViewModeChange">
          <el-radio-button value="workspace">📊 工作台</el-radio-button>
          <el-radio-button value="roadmap">🗺️ 路线图</el-radio-button>
        </el-radio-group>
        <span class="header-date">{{ currentDate }}</span>
      </div>
    </div>

    <!-- ═══════════════ 路线图视图 ═══════════════ -->
    <template v-if="viewMode === 'roadmap'">
      <RoadmapPanel :items="roadmapData?.roadmap_items || []" />
    </template>

    <!-- ═══════════════ 工作台视图 ═══════════════ -->
    <template v-if="viewMode === 'workspace'">
      <!-- ═══════════════ 统计卡片 ═══════════════ -->
      <el-row :gutter="12" class="stats-cards" v-if="statsData">
        <el-col :span="4">
          <el-card shadow="never" class="stat-card">
            <div class="stat-card-num">{{ statsData.annual_plan_count }}</div>
            <div class="stat-card-label">年度规划</div>
          </el-card>
        </el-col>
        <el-col :span="5">
          <el-card shadow="never" class="stat-card">
            <div class="stat-card-num">{{ statsData.total_projects }}</div>
            <div class="stat-card-label">总项目数</div>
          </el-card>
        </el-col>
        <el-col :span="5">
          <el-card shadow="never" class="stat-card">
            <div class="stat-card-num">¥{{ formatMoney(statsData.total_budget) }}</div>
            <div class="stat-card-label">总预算</div>
          </el-card>
        </el-col>
        <el-col :span="5">
          <el-card shadow="never" class="stat-card">
            <div class="stat-card-num" :style="{ color: statsData.completion_rate >= 60 ? '#67c23a' : '#e6a23c' }">{{ statsData.completion_rate }}%</div>
            <div class="stat-card-label">完成率</div>
          </el-card>
        </el-col>
        <el-col :span="5">
          <el-card shadow="never" class="stat-card">
            <div class="stat-card-num" :style="{ color: statsData.overdue_rate > 0 ? '#f56c6c' : '#67c23a' }">{{ statsData.overdue_rate }}%</div>
            <div class="stat-card-label">逾期率</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- ═══════════════ 快捷入口 ═══════════════ -->
      <div class="quick-links">
        <el-card shadow="never" class="quick-link-card" @click="$router.push('/competitor-bench')">
          <div class="quick-link-icon">📊</div>
          <div class="quick-link-info">
            <div class="quick-link-title">竞品对标</div>
            <div class="quick-link-desc">查看各品牌竞品参数与性能对比</div>
          </div>
          <el-icon class="quick-link-arrow"><ArrowRight /></el-icon>
        </el-card>
        <el-card shadow="never" class="quick-link-card" @click="$router.push('/market-mgmt')">
          <div class="quick-link-icon">🏛️</div>
          <div class="quick-link-info">
            <div class="quick-link-title">市场管理</div>
            <div class="quick-link-desc">各国认证标准、能效要求、压缩机信息</div>
          </div>
          <el-icon class="quick-link-arrow"><ArrowRight /></el-icon>
        </el-card>
        <el-card shadow="never" class="quick-link-card" @click="$router.push('/proposals')">
          <div class="quick-link-icon">📝</div>
          <div class="quick-link-info">
            <div class="quick-link-title">提案管理</div>
            <div class="quick-link-desc">查看和管理所有产品立项提案</div>
          </div>
          <el-icon class="quick-link-arrow"><ArrowRight /></el-icon>
        </el-card>
      </div>

      <!-- ═══════════════ 三栏布局 ═══════════════ -->
      <div class="workspace-body">
        <!-- 左栏 (30%)：年度产品规划 -->
        <div class="col-left">
          <el-card shadow="never" class="col-card">
            <template #header>
              <div class="card-header">
                <span>📋 年度产品规划</span>
                <el-button type="primary" size="small" @click="$router.push('/product-plans')">查看全部</el-button>
              </div>
            </template>
            <div v-if="planningItems.length === 0" class="empty-state">
              <el-empty description="暂无年度规划项" :image-size="60" />
            </div>
            <div
              v-for="item in planningItems" :key="item.id"
              class="plan-item"
              @click="$router.push('/product-plans/' + item.id)"
            >
              <div class="plan-item-name">{{ item.name }}</div>
              <div class="plan-item-meta">
                <el-tag size="small" type="warning">{{ item.year }}</el-tag>
                <span class="plan-item-desc">{{ item.description || '暂无描述' }}</span>
              </div>
              <div class="plan-item-count" v-if="item.project_count !== undefined">
                关联项目: {{ item.project_count }} 个
              </div>
            </div>
          </el-card>
        </div>

        <!-- 中栏 (40%)：产品立项入口 -->
        <div class="col-middle">
          <ProductInitiation :draft-id="draftId" @open="$router.push('/proposals')" />
        </div>

        <!-- 右栏 (30%)：我的项目看板 -->
        <div class="col-right">
          <el-card shadow="never" class="col-card">
            <template #header>
              <div class="card-header">
                <span>📊 我的项目</span>
              </div>
            </template>
            <div class="stats-row">
              <div class="stat-item">
                <div class="stat-num">{{ myProjects.length }}</div>
                <div class="stat-label">总数</div>
              </div>
              <div class="stat-item">
                <div class="stat-num" style="color:#409eff">{{ stats.running }}</div>
                <div class="stat-label">进行中</div>
              </div>
              <div class="stat-item">
                <div class="stat-num" style="color:#67c23a">{{ stats.completed }}</div>
                <div class="stat-label">已完成</div>
              </div>
              <div class="stat-item">
                <div class="stat-num" style="color:#f56c6c">{{ stats.overdue }}</div>
                <div class="stat-label">超期</div>
              </div>
            </div>
            <div v-if="myProjects.length === 0" class="empty-state">
              <el-empty description="暂无项目" :image-size="60" />
            </div>
            <div v-for="proj in myProjects" :key="proj.id" class="project-card" @click="toggleExpand(proj.id)">
              <div class="project-card-header">
                <span class="project-name">{{ proj.name }}</span>
                <div class="project-card-tags">
                  <el-tag v-if="proj.approval_status" :type="approvalTagType(proj.approval_status)" size="small">{{ approvalLabel(proj.approval_status) }}</el-tag>
                  <el-tag :type="statusTagType(proj.status)" size="small">{{ statusLabel(proj.status) }}</el-tag>
                </div>
              </div>
              <el-progress
                :percentage="proj.progress || 0"
                :color="progressColor(proj.progress || 0)"
                :stroke-width="6"
                style="margin:6px 0"
              />
              <div class="project-card-meta" v-if="proj.budget || proj.market_policy">
                <span v-if="proj.budget">预算: ¥{{ formatMoney(proj.budget) }}</span>
                <span v-if="proj.market_policy">{{ proj.market_policy }}</span>
              </div>
              <div v-if="expandedProjectId === proj.id" class="project-detail">
                <div class="detail-row"><label>项目等级:</label> {{ proj.project_class || '-' }}级</div>
                <div class="detail-row"><label>应用场景:</label> {{ proj.scene || '-' }}</div>
                <div class="detail-row"><label>关联产品:</label> {{ proj.linked_product || '-' }}</div>
                <div class="detail-row"><label>目标日期:</label> {{ proj.target_end_date || '-' }}</div>
                <div class="detail-row"><label>背景:</label> {{ proj.background_basis || '-' }}</div>
                <div class="detail-row"><label>市场政策:</label> {{ proj.market_policy || '-' }}</div>
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'
import api from '../../api'

// 子组件
import ProductInitiation from './proposal/ProductInitiation.vue'
import RoadmapPanel from './RoadmapPanel.vue'

interface PlanningItem {
  id: number; name: string; year: string; description: string
  doc_ref: string; project_count: number; projects?: ProjectSummary[]
}
interface ProjectSummary { id: number; name: string; status: string; approval_status?: string }
interface ProjectItem {
  id: number; name: string; status: string; project_class: string
  progress: number; budget?: number; market_policy?: string
  scene?: string; linked_product?: string; target_end_date?: string
  background_basis?: string; product_type?: string; target_market?: string
  refrigerant?: string; main_capacity?: string; capacity_range?: string
  voltage_freq?: string; series_name?: string; energy_rating?: string
  ip_ownership?: string; project_duration?: string
  dev_category?: string; project_origin?: string
  start_date?: string; required_date?: string; sample_qty?: number
  annual_planning_ref?: string; annual_planning_id?: number | null
  market_demand_overview?: string; competitor_analysis?: string; customer_special_req?: string
  climate_zone?: string; is_draft?: boolean
  has_outsourcing?: boolean
  customer_name?: string; cert_requirements?: string; energy_efficiency_req?: string
  target_price?: string; customer_requirements?: string; other_requirements?: string
  program_id?: number | null; leader_id?: number | null
  overall_goal?: string; background_basis_raw?: string; tech_goal?: string
  cost_goal?: string; sales_goal?: string; cert_goal?: string
  schedule_goal?: string; patent_goal?: string; other_goals?: string
  deliverables?: string; fob_price?: number; bom_cost_target?: number
  annual_sales_forecast?: number; product_lifecycle?: string
  dev_cost_items?: string; mold_costs?: string; prototype_costs_detail?: string
  test_costs?: string; labor_costs?: string; cert_costs?: string
  core_performance?: string; safety_compliance?: string
  material_components?: string
  accessory_config?: string; feature_config?: string
  team_members?: string
  approval_status?: string
  created_at?: string; updated_at?: string
}

// ═══════════════════════════════════════════════
// 计算属性
// ═══════════════════════════════════════════════

const currentDate = computed(() => {
  const d = new Date()
  const weekDays = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${weekDays[d.getDay()]}`
})

// ═══════════════════════════════════════════════
// 响应式数据
// ═══════════════════════════════════════════════

// 年度规划
const planningItems = ref<PlanningItem[]>([])

// 项目
const myProjects = ref<ProjectItem[]>([])

// 看板统计
const stats = computed(() => {
  const items = myProjects.value
  const running = items.filter(p => p.status === 'running').length
  const completed = items.filter(p => p.status === 'completed').length
  const overdue = items.filter(p => p.status === 'overdue').length
  return { running, completed, overdue }
})

// 展开的项目ID
const expandedProjectId = ref<number | null>(null)

// 草稿ID（从workspace API获取）
const draftId = ref<number | null>(null)

// 统计卡片数据
const statsData = ref<{
  annual_plan_count: number
  total_projects: number
  total_budget: number
  completion_rate: number
  overdue_rate: number
  running_count: number
  overdue_count: number
  completed_count: number
} | null>(null)

// 视图模式
const viewMode = ref<'workspace' | 'roadmap'>('workspace')
const roadmapData = ref<{ roadmap_items: any[] } | null>(null)

// ═══════════════════════════════════════════════
// 工具函数
// ═══════════════════════════════════════════════

function formatMoney(val: number | null | undefined): string {
  if (val == null) return '0'
  return Number(val).toLocaleString('zh-CN')
}

function statusTagType(status: string): string {
  const map: Record<string, string> = {
    planning: 'info', running: '', completed: 'success',
    paused: 'warning', cancelled: 'danger', draft: 'info', overdue: 'danger',
    submitted: 'primary'
  }
  return map[status] || 'info'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    planning: '规划中', running: '进行中', completed: '已完成',
    paused: '暂停', cancelled: '已取消', draft: '草稿', overdue: '超期',
    submitted: '已提交'
  }
  return map[status] || status
}

function approvalTagType(status: string): string {
  const map: Record<string, string> = {
    pending: 'warning', approved: 'success', rejected: 'danger'
  }
  return map[status] || 'info'
}

function approvalLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '审批中', approved: '审批通过', rejected: '审批驳回'
  }
  return map[status] || status
}

function progressColor(progress: number): string {
  if (progress >= 80) return '#67c23a'
  if (progress >= 40) return '#409eff'
  return '#e6a23c'
}

// ═══════════════════════════════════════════════
// 项目看板
// ═══════════════════════════════════════════════

function toggleExpand(projId: number) {
  expandedProjectId.value = expandedProjectId.value === projId ? null : projId
}

// ═══════════════════════════════════════════════
// API 调用
// ═══════════════════════════════════════════════

async function fetchStatistics() {
  try {
    const res = await api.get('/pm/statistics')
    statsData.value = res.data
  } catch {
    // 静默失败
  }
}

async function fetchRoadmap() {
  try {
    const res = await api.get('/pm/roadmap')
    roadmapData.value = res.data
  } catch {
    // 静默失败
  }
}

function onViewModeChange(mode: string) {
  if (mode === 'roadmap' && !roadmapData.value) {
    fetchRoadmap()
  }
}

async function fetchWorkspaceData() {
  try {
    const res = await api.get('/pm/workspace')
    const data = res.data
    planningItems.value = data.annual_plans || []
    myProjects.value = data.my_projects || []
    if (data.draft) {
      draftId.value = data.draft.id
    }
  } catch {
    // handled by interceptor
  }
}

// ═══════════════════════════════════════════════
// 生命周期
// ═══════════════════════════════════════════════

onMounted(async () => {
  try {
    await fetchWorkspaceData()
    await fetchStatistics()
  } catch (e) {
    console.error('PMWorkspace init error:', e)
  }
})
</script>

<style>
.pm-workspace {
  height: 100%;
  overflow-y: auto;
}

.workspace-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.workspace-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-date {
  font-size: 14px;
  color: #909399;
}

/* 统计卡片栏 */
.stats-cards {
  margin-bottom: 16px;
}
.stat-card {
  text-align: center;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.stat-card :deep(.el-card__body) {
  padding: 12px 8px;
  width: 100%;
}
.stat-card-num {
  font-size: 26px;
  font-weight: bold;
  color: #303133;
  line-height: 1.2;
}
.stat-card-label {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

/* 三栏布局 */
.workspace-body {
  display: flex;
  gap: 16px;
  min-height: 500px;
}

.col-left {
  flex: 0 0 30%;
}
.col-middle {
  flex: 0 0 40%;
}
.col-right {
  flex: 0 0 30%;
}

.col-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.col-card :deep(.el-card__body) {
  flex: 1;
  overflow-y: auto;
}

/* 移动端响应式 */
@media (max-width: 768px) {
  .workspace-body { flex-direction: column; }
  .col-left, .col-middle, .col-right { flex: none; width: 100%; }
  .stat-cards { flex-wrap: wrap; }
  .stat-card { flex: 1 1 calc(50% - 8px); min-width: 0; }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.empty-state {
  padding: 20px 0;
}

/* 规划项列表 */
.plan-item {
  padding: 10px 12px;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  border: 1px solid #ebeef5;
  transition: all 0.2s;
}

.plan-item:hover {
  border-color: #409eff;
  background: #ecf5ff;
}

.plan-item-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.plan-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.plan-item-desc {
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plan-item-count {
  font-size: 12px;
  color: #606266;
}

/* 看板统计 */
.stats-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.stat-item {
  flex: 1;
  text-align: center;
}

.stat-num {
  font-size: 20px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}

/* 项目卡片 */
.project-card {
  padding: 10px 12px;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  border: 1px solid #ebeef5;
  transition: all 0.2s;
}

.project-card:hover {
  border-color: #409eff;
  background: #ecf5ff;
}

.project-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.project-card-tags {
  display: flex;
  gap: 4px;
  align-items: center;
}

.project-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  margin-right: 8px;
}

.project-card-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 12px;
}

.project-detail {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #dcdfe6;
  font-size: 12px;
  color: #606266;
}

.detail-row {
  padding: 2px 0;
}

.detail-row label {
  font-weight: 500;
  color: #303133;
  margin-right: 4px;
}

/* ── 快捷入口 ── */
.quick-links {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}
.quick-link-card {
  flex: 1;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid #e4e7ed;
}
.quick-link-card:hover {
  border-color: #409eff;
  background: #f0f6ff;
  transform: translateY(-1px);
}
.quick-link-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  padding: 16px 20px;
}
.quick-link-icon {
  font-size: 28px;
  margin-right: 16px;
  flex-shrink: 0;
}
.quick-link-info {
  flex: 1;
  min-width: 0;
}
.quick-link-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}
.quick-link-desc {
  font-size: 12px;
  color: #909399;
}
.quick-link-arrow {
  font-size: 16px;
  color: #c0c4cc;
  flex-shrink: 0;
  margin-left: 12px;
}
</style>
