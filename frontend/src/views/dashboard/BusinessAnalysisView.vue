<template>
  <section class="dashboard-section">
    <div class="section-header">
      <div class="section-badge" style="background: var(--c-accent-light, #fce4d6); color: var(--c-accent, #d97757);">
        <el-icon :size="16"><TrendCharts /></el-icon>
      </div>
      <h2 class="section-title">经营分析看板</h2>
      <span class="section-count">4 维 · {{ totalMetrics }} 项指标</span>
      <div class="filter-bar">
        <el-button size="small" :loading="loading" @click="$emit('refresh')" text>
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- Error / Empty -->
    <div v-if="error" class="empty-state section-empty">
      <el-icon :size="48" color="var(--c-danger)"><CircleCloseFilled /></el-icon>
      <p class="empty-title">数据加载失败</p>
      <p class="empty-desc">经营分析数据暂不可用，请稍后重试</p>
    </div>

    <!-- Loading -->
    <div v-else-if="loading" class="biz-loading">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <p>正在加载经营分析数据...</p>
    </div>

    <!-- Normal -->
    <template v-else>
      <!-- 四维度主指标卡 -->
      <div class="biz-pillar-grid">
        <div class="biz-pillar-card" @click="activePillar = 'production_sales'"
          :class="{ 'is-active': activePillar === 'production_sales' }"
          style="border-left: 4px solid #0284c7;">
          <div class="biz-pillar-icon" style="background: #0284c712; color: #0284c7;">
            <el-icon :size="24"><Connection /></el-icon>
          </div>
          <div class="biz-pillar-header">
            <span class="biz-pillar-title">产销协同</span>
            <span class="biz-pillar-sub">T+3产销</span>
          </div>
          <div class="biz-pillar-kpi">
            <div class="biz-pillar-stat">
              <span class="biz-stat-value">{{ data.production_sales?.running_projects ?? '-' }}</span>
              <span class="biz-stat-label">进行中项目</span>
            </div>
            <div class="biz-pillar-stat">
              <span class="biz-stat-value">{{ data.production_sales?.total_plans ?? '-' }}</span>
              <span class="biz-stat-label">策划总数</span>
            </div>
          </div>
          <div class="biz-pillar-footer">
            <span class="biz-pillar-change">转化率 {{ data.production_sales?.plan_to_project_rate ?? '-' }}%</span>
            <el-icon :size="14"><ArrowRight /></el-icon>
          </div>
        </div>

        <div class="biz-pillar-card" @click="activePillar = 'financial_control'"
          :class="{ 'is-active': activePillar === 'financial_control' }"
          style="border-left: 4px solid #059669;">
          <div class="biz-pillar-icon" style="background: #05966912; color: #059669;">
            <el-icon :size="24"><Coin /></el-icon>
          </div>
          <div class="biz-pillar-header">
            <span class="biz-pillar-title">财务管控</span>
            <span class="biz-pillar-sub">老虎管控</span>
          </div>
          <div class="biz-pillar-kpi">
            <div class="biz-pillar-stat">
              <span class="biz-stat-value">{{ formatAmount(data.financial_control?.total_purchase_amount) }}</span>
              <span class="biz-stat-label">采购总额</span>
            </div>
            <div class="biz-pillar-stat">
              <span class="biz-stat-value">{{ data.financial_control?.active_suppliers ?? '-' }}</span>
              <span class="biz-stat-label">活跃供应商</span>
            </div>
          </div>
          <div class="biz-pillar-footer">
            <span class="biz-pillar-change">待审批 {{ data.financial_control?.pending_purchase_orders ?? 0 }} 单</span>
            <el-icon :size="14"><ArrowRight /></el-icon>
          </div>
        </div>

        <div class="biz-pillar-card" @click="activePillar = 'growth_engine'"
          :class="{ 'is-active': activePillar === 'growth_engine' }"
          style="border-left: 4px solid #d97706;">
          <div class="biz-pillar-icon" style="background: #d9770612; color: #d97706;">
            <el-icon :size="24"><DataAnalysis /></el-icon>
          </div>
          <div class="biz-pillar-header">
            <span class="biz-pillar-title">增长引擎</span>
            <span class="biz-pillar-sub">ToB+海外</span>
          </div>
          <div class="biz-pillar-kpi">
            <div class="biz-pillar-stat">
              <span class="biz-stat-value">{{ data.growth_engine?.total_markets ?? '-' }}</span>
              <span class="biz-stat-label">市场覆盖</span>
            </div>
            <div class="biz-pillar-stat">
              <span class="biz-stat-value">{{ data.growth_engine?.total_competitors ?? '-' }}</span>
              <span class="biz-stat-label">竞品跟踪</span>
            </div>
          </div>
          <div class="biz-pillar-footer">
            <span class="biz-pillar-change">R32 {{ data.growth_engine?.r32_markets ?? 0 }} · R410A {{ data.growth_engine?.r410a_markets ?? 0 }}</span>
            <el-icon :size="14"><ArrowRight /></el-icon>
          </div>
        </div>

        <div class="biz-pillar-card" @click="activePillar = 'efficiency'"
          :class="{ 'is-active': activePillar === 'efficiency' }"
          style="border-left: 4px solid #7c3aed;">
          <div class="biz-pillar-icon" style="background: #7c3aed12; color: #7c3aed;">
            <el-icon :size="24"><Timer /></el-icon>
          </div>
          <div class="biz-pillar-header">
            <span class="biz-pillar-title">效率指标</span>
            <span class="biz-pillar-sub">AI提效+数字化</span>
          </div>
          <div class="biz-pillar-kpi">
            <div class="biz-pillar-stat">
              <span class="biz-stat-value">{{ data.efficiency?.on_time_rate ?? '-' }}%</span>
              <span class="biz-stat-label">按时完成率</span>
            </div>
            <div class="biz-pillar-stat">
              <span class="biz-stat-value">{{ data.efficiency?.test_pass_rate ?? '-' }}%</span>
              <span class="biz-stat-label">测试通过率</span>
            </div>
          </div>
          <div class="biz-pillar-footer">
            <span class="biz-pillar-change" :class="alertClass">
              <el-icon :size="12"><WarningFilled /></el-icon>
              预警 {{ data.efficiency?.alert_count ?? 0 }} 条
            </span>
            <el-icon :size="14"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>

      <!-- 展开详情区域 -->
      <transition name="biz-detail">
        <div v-if="activePillar" class="biz-detail-panel">
          <!-- 产销协同详情 -->
          <div v-if="activePillar === 'production_sales'" class="biz-detail-grid">
            <div class="biz-detail-card">
              <h4 class="biz-detail-title">📋 项目管道</h4>
              <div class="biz-detail-metrics">
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.production_sales?.total_projects ?? 0 }}</span>
                  <span class="biz-detail-lbl">项目总数</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val" style="color: var(--c-accent);">{{ data.production_sales?.running_projects ?? 0 }}</span>
                  <span class="biz-detail-lbl">进行中</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val" style="color: var(--c-success);">{{ data.production_sales?.completed_projects ?? 0 }}</span>
                  <span class="biz-detail-lbl">已完成</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val" :class="data.production_sales?.overdue_projects ? 'text-danger' : ''">{{ data.production_sales?.overdue_projects ?? 0 }}</span>
                  <span class="biz-detail-lbl">超期</span>
                </div>
              </div>
            </div>
            <div class="biz-detail-card">
              <h4 class="biz-detail-title">📝 策划管道</h4>
              <div class="biz-detail-metrics">
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.production_sales?.total_plans ?? 0 }}</span>
                  <span class="biz-detail-lbl">策划总数</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val" style="color: var(--c-info);">{{ data.production_sales?.draft_plans ?? 0 }}</span>
                  <span class="biz-detail-lbl">草稿</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val" style="color: var(--c-warning);">{{ data.production_sales?.costing_plans ?? 0 }}</span>
                  <span class="biz-detail-lbl">成本目标</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val" style="color: var(--c-success);">{{ data.production_sales?.released_plans ?? 0 }}</span>
                  <span class="biz-detail-lbl">已发布</span>
                </div>
              </div>
            </div>
            <div class="biz-detail-card">
              <h4 class="biz-detail-title">🔧 BOM/物料</h4>
              <div class="biz-detail-metrics">
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.production_sales?.total_boms ?? 0 }}</span>
                  <span class="biz-detail-lbl">BOM总数</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.production_sales?.total_parts ?? 0 }}</span>
                  <span class="biz-detail-lbl">物料总数</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.production_sales?.plan_to_project_rate ?? 0 }}%</span>
                  <span class="biz-detail-lbl">策划→项目转化率</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 财务管控详情 -->
          <div v-else-if="activePillar === 'financial_control'" class="biz-detail-grid">
            <div class="biz-detail-card">
              <h4 class="biz-detail-title">💰 采购管理</h4>
              <div class="biz-detail-metrics">
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.financial_control?.total_purchase_orders ?? 0 }}</span>
                  <span class="biz-detail-lbl">采购订单</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val" style="color: var(--c-warning);">{{ data.financial_control?.pending_purchase_orders ?? 0 }}</span>
                  <span class="biz-detail-lbl">待审批</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val biz-detail-val-lg">{{ formatAmount(data.financial_control?.total_purchase_amount) }}</span>
                  <span class="biz-detail-lbl">采购总额(万元)</span>
                </div>
              </div>
            </div>
            <div class="biz-detail-card">
              <h4 class="biz-detail-title">🏭 供应商</h4>
              <div class="biz-detail-metrics">
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.financial_control?.total_suppliers ?? 0 }}</span>
                  <span class="biz-detail-lbl">供应商总数</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val" style="color: var(--c-success);">{{ data.financial_control?.active_suppliers ?? 0 }}</span>
                  <span class="biz-detail-lbl">活跃供应商</span>
                </div>
              </div>
            </div>
            <div class="biz-detail-card">
              <h4 class="biz-detail-title">📊 成本核算</h4>
              <div class="biz-detail-metrics">
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.financial_control?.cost_accounting_periods ?? 0 }}</span>
                  <span class="biz-detail-lbl">核算期间</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.financial_control?.cost_orders_count ?? 0 }}</span>
                  <span class="biz-detail-lbl">成本核算单</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 增长引擎详情 -->
          <div v-else-if="activePillar === 'growth_engine'" class="biz-detail-grid">
            <div class="biz-detail-card">
              <h4 class="biz-detail-title">🌍 市场拓展</h4>
              <div class="biz-detail-metrics">
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.growth_engine?.total_markets ?? 0 }}</span>
                  <span class="biz-detail-lbl">总市场数</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val" style="color: #0284c7;">{{ data.growth_engine?.r32_markets ?? 0 }}</span>
                  <span class="biz-detail-lbl">R32市场</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val" style="color: #7c3aed;">{{ data.growth_engine?.r410a_markets ?? 0 }}</span>
                  <span class="biz-detail-lbl">R410A市场</span>
                </div>
              </div>
            </div>
            <div class="biz-detail-card">
              <h4 class="biz-detail-title">🔍 竞品与认证</h4>
              <div class="biz-detail-metrics">
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.growth_engine?.total_competitors ?? 0 }}</span>
                  <span class="biz-detail-lbl">竞品总数</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.growth_engine?.competitor_markets_count ?? 0 }}</span>
                  <span class="biz-detail-lbl">覆盖市场</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.growth_engine?.total_cert_projects ?? 0 }}/{{ data.growth_engine?.cert_projects_in_progress ?? 0 }}</span>
                  <span class="biz-detail-lbl">认证项目(总/进行中)</span>
                </div>
              </div>
            </div>
            <div class="biz-detail-card">
              <h4 class="biz-detail-title">📦 产品线</h4>
              <div class="biz-detail-metrics">
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.growth_engine?.total_products ?? 0 }}</span>
                  <span class="biz-detail-lbl">产品数</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.growth_engine?.total_versions ?? 0 }}</span>
                  <span class="biz-detail-lbl">版本数</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 效率指标详情 -->
          <div v-else-if="activePillar === 'efficiency'" class="biz-detail-grid">
            <div class="biz-detail-card">
              <h4 class="biz-detail-title">⏱ 项目效率</h4>
              <div class="biz-detail-metrics">
                <div class="biz-detail-item">
                  <span class="biz-detail-val" :class="data.efficiency?.on_time_rate >= 80 ? 'text-success' : 'text-warning'">{{ data.efficiency?.on_time_rate ?? 0 }}%</span>
                  <span class="biz-detail-lbl">按时完成率</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.efficiency?.avg_project_duration_days ?? 0 }}天</span>
                  <span class="biz-detail-lbl">平均项目周期</span>
                </div>
              </div>
            </div>
            <div class="biz-detail-card">
              <h4 class="biz-detail-title">✅ 质量效率</h4>
              <div class="biz-detail-metrics">
                <div class="biz-detail-item">
                  <span class="biz-detail-val" :class="data.efficiency?.test_pass_rate >= 80 ? 'text-success' : 'text-warning'">{{ data.efficiency?.test_pass_rate ?? 0 }}%</span>
                  <span class="biz-detail-lbl">测试通过率</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val" :class="data.efficiency?.issue_close_rate >= 80 ? 'text-success' : 'text-warning'">{{ data.efficiency?.issue_close_rate ?? 0 }}%</span>
                  <span class="biz-detail-lbl">问题关闭率</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val">{{ data.efficiency?.phase_gate_pass_rate ?? 0 }}%</span>
                  <span class="biz-detail-lbl">门控通过率</span>
                </div>
              </div>
            </div>
            <div class="biz-detail-card">
              <h4 class="biz-detail-title">🔔 预警监控</h4>
              <div class="biz-detail-metrics">
                <div class="biz-detail-item">
                  <span class="biz-detail-val" :class="data.efficiency?.alert_count > 0 ? 'text-warning' : 'text-success'">{{ data.efficiency?.alert_count ?? 0 }}</span>
                  <span class="biz-detail-lbl">未解决预警</span>
                </div>
                <div class="biz-detail-item">
                  <span class="biz-detail-val" :class="data.efficiency?.overdue_alert_count > 0 ? 'text-danger' : ''">{{ data.efficiency?.overdue_alert_count ?? 0 }}</span>
                  <span class="biz-detail-lbl">紧急预警</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  TrendCharts, Connection, Coin, DataAnalysis, Timer,
  Refresh, ArrowRight, WarningFilled, CircleCloseFilled, Loading,
} from '@element-plus/icons-vue'

interface ProductionSales {
  total_projects: number; running_projects: number; completed_projects: number
  overdue_projects: number; total_plans: number; draft_plans: number
  costing_plans: number; released_plans: number
  total_boms: number; total_parts: number; plan_to_project_rate: number
}
interface FinancialControl {
  total_purchase_orders: number; pending_purchase_orders: number
  total_purchase_amount: number; total_suppliers: number; active_suppliers: number
  cost_accounting_periods: number; cost_orders_count: number
  cost_execution_rate: number; cost_overrun_alerts: number
}
interface GrowthEngine {
  total_markets: number; r32_markets: number; r410a_markets: number
  total_competitors: number; competitor_markets_count: number
  total_cert_projects: number; cert_projects_in_progress: number
  total_products: number; total_versions: number
}
interface Efficiency {
  on_time_rate: number; avg_project_duration_days: number
  test_pass_rate: number; issue_close_rate: number
  phase_gate_pass_rate: number; alert_count: number; overdue_alert_count: number
}
interface BizData {
  production_sales?: ProductionSales
  financial_control?: FinancialControl
  growth_engine?: GrowthEngine
  efficiency?: Efficiency
}

const props = defineProps<{
  data: BizData
  loading: boolean
  error: boolean
}>()
defineEmits<{ refresh: [] }>()

const activePillar = ref<string | null>(null)

const totalMetrics = computed(() => {
  let count = 0
  const d = props.data
  if (d.production_sales) count += 10
  if (d.financial_control) count += 7
  if (d.growth_engine) count += 9
  if (d.efficiency) count += 7
  return count
})

const alertClass = computed(() => {
  const cnt = props.data.efficiency?.alert_count ?? 0
  return cnt > 0 ? 'text-warning' : 'text-success'
})

function formatAmount(val?: number): string {
  if (val === undefined || val === null) return '-'
  const w = val / 10000
  if (w >= 1) return w.toFixed(1) + '万'
  return val.toFixed(0)
}
</script>

<style scoped>
.biz-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 60px 20px;
  color: var(--c-text-secondary);
}
.biz-loading p { margin: 0; font-size: 14px; }

/* 四维度主指标卡网格 */
.biz-pillar-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
@media (max-width: 1024px) {
  .biz-pillar-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
  .biz-pillar-grid { grid-template-columns: 1fr; }
}

.biz-pillar-card {
  background: var(--c-bg-card);
  border: 1px solid var(--c-border);
  border-radius: var(--c-radius-lg);
  padding: 20px;
  cursor: pointer;
  transition: all var(--c-transition-base);
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.biz-pillar-card:hover {
  border-color: var(--c-border-dark);
  box-shadow: var(--c-shadow-md);
  transform: translateY(-2px);
}
.biz-pillar-card.is-active {
  border-color: var(--c-border-dark);
  box-shadow: var(--c-shadow-md);
  background: var(--c-bg-hover);
}

.biz-pillar-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--c-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.biz-pillar-header {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.biz-pillar-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--c-text-primary);
}
.biz-pillar-sub {
  font-size: 12px;
  color: var(--c-text-tertiary);
}
.biz-pillar-kpi {
  display: flex;
  gap: 16px;
}
.biz-pillar-stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.biz-stat-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--c-text-primary);
  line-height: 1.2;
  letter-spacing: -0.5px;
}
.biz-stat-label {
  font-size: 12px;
  color: var(--c-text-tertiary);
  font-weight: 500;
}
.biz-pillar-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--c-border-light);
  font-size: 12px;
  color: var(--c-text-tertiary);
}
.biz-pillar-change {
  display: flex;
  align-items: center;
  gap: 4px;
}
.text-success { color: var(--c-success, #67c23a) !important; }
.text-warning { color: var(--c-warning, #e6a23c) !important; }
.text-danger { color: var(--c-danger, #f56c6c) !important; }

/* 展开详情面板 */
.biz-detail-panel {
  background: var(--c-bg-card);
  border: 1px solid var(--c-border);
  border-radius: var(--c-radius-lg);
  padding: 20px;
  margin-bottom: 20px;
}
.biz-detail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
@media (max-width: 768px) {
  .biz-detail-grid { grid-template-columns: 1fr; }
}
.biz-detail-card {
  background: var(--c-bg-hover);
  border-radius: var(--c-radius-md);
  padding: 16px;
}
.biz-detail-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text-primary);
  margin: 0 0 12px;
}
.biz-detail-metrics {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.biz-detail-item {
  flex: 1;
  min-width: 80px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.biz-detail-val {
  font-size: 20px;
  font-weight: 700;
  color: var(--c-text-primary);
  line-height: 1.2;
}
.biz-detail-val-lg {
  font-size: 14px;
}
.biz-detail-lbl {
  font-size: 11px;
  color: var(--c-text-tertiary);
  font-weight: 500;
}

/* 过渡动画 */
.biz-detail-enter-active { transition: all 0.3s ease; }
.biz-detail-leave-active { transition: all 0.2s ease; }
.biz-detail-enter-from { opacity: 0; transform: translateY(-10px); }
.biz-detail-leave-to { opacity: 0; }
</style>
