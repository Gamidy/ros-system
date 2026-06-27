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

        <!-- ══════ D3-3: 预警Badge ══════ -->
        <div class="alert-badges" v-if="alertsSummary.total > 0">
          <el-badge :value="alertsSummary.overdue" :hidden="alertsSummary.overdue === 0" class="alert-badge-item" type="danger">
            <el-button size="small" class="alert-badge-btn alert-btn-danger" @click="showAlertDrawer = true">
              <el-icon :size="14"><WarningFilled /></el-icon>
              <span>逾期</span>
            </el-button>
          </el-badge>
          <el-badge :value="alertsSummary.cost_overrun" :hidden="alertsSummary.cost_overrun === 0" class="alert-badge-item" type="warning">
            <el-button size="small" class="alert-badge-btn alert-btn-warning" @click="showAlertDrawer = true">
              <el-icon :size="14"><Coin /></el-icon>
              <span>超标</span>
            </el-button>
          </el-badge>
          <el-badge :value="alertsSummary.stuck" :hidden="alertsSummary.stuck === 0" class="alert-badge-item" type="warning">
            <el-button size="small" class="alert-badge-btn alert-btn-warning" @click="showAlertDrawer = true">
              <el-icon :size="14"><Time /></el-icon>
              <span>滞留</span>
            </el-button>
          </el-badge>
        </div>
        <div class="alert-badges" v-else-if="alertsLoading">
          <el-button size="small" class="alert-badge-btn" disabled>
            <el-icon :size="14"><Loading /></el-icon>
            <span>检测中...</span>
          </el-button>
        </div>
        <div class="alert-badges" v-else>
          <el-button size="small" class="alert-badge-btn alert-btn-safe" @click="showAlertDrawer = true">
            <el-icon :size="14"><CircleCheck /></el-icon>
            <span>无异常</span>
          </el-button>
        </div>

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
        <div class="stat-card" @click="openKpiDrawer('in_progress')">
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
        <div class="stat-card" @click="openKpiDrawer('in_progress')">
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
        <div class="stat-card" @click="openKpiDrawer('pending')">
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
        <div class="stat-card" @click="openKpiDrawer('completed')">
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

    <!-- ═══════════ D3-3: 预警列表抽屉 ═══════════ -->
    <el-drawer
      v-model="showAlertDrawer"
      title="预警与异常一览"
      direction="rtl"
      size="420px"
      :close-on-press-escape="true"
      :close-on-click-modal="true"
    >
      <template #title>
        <div class="alert-drawer-title">
          <el-icon :size="20" color="#e6a23c"><WarningFilled /></el-icon>
          <span>预警与异常一览</span>
          <el-tag type="danger" size="small" v-if="alertsSummary.total > 0">
            {{ alertsSummary.total }} 条
          </el-tag>
        </div>
      </template>

      <div v-if="alertsLoading" class="alert-drawer-loading">
        <el-icon :size="32" class="is-loading"><Loading /></el-icon>
        <p>正在检测异常...</p>
      </div>

      <div v-else-if="alertList.length === 0" class="alert-drawer-empty">
        <el-icon :size="48" color="#67c23a"><CircleCheckFilled /></el-icon>
        <p>暂无预警，所有策划运行正常</p>
      </div>

      <div v-else class="alert-drawer-list">
        <div class="alert-summary-counts">
          <div class="alert-count-item">
            <span class="alert-count-dot danger"></span>
            <span>逾期</span>
            <strong>{{ alertsSummary.overdue }}</strong>
          </div>
          <div class="alert-count-item">
            <span class="alert-count-dot warning"></span>
            <span>超标</span>
            <strong>{{ alertsSummary.cost_overrun }}</strong>
          </div>
          <div class="alert-count-item">
            <span class="alert-count-dot warning-light"></span>
            <span>滞留</span>
            <strong>{{ alertsSummary.stuck }}</strong>
          </div>
        </div>

        <div
          v-for="(alert, idx) in alertList"
          :key="`${alert.type}-${alert.plan_id}-${idx}`"
          class="alert-card"
          :class="`alert-card--${alert.type}`"
          @click="goToAlertPlan(alert)"
        >
          <div class="alert-card-left">
            <el-tag
              :type="alertTagType(alert.type)"
              size="small"
              effect="dark"
              class="alert-tag"
            >
              {{ alertLabel(alert.type) }}
            </el-tag>
            <div class="alert-card-name">{{ alert.plan_name }}</div>
            <div class="alert-card-message">{{ alert.message }}</div>
            <div class="alert-card-meta" v-if="alert.status">
              <span class="alert-stage-tag">{{ alert.status }}</span>
              <span v-if="alert.created_at" class="alert-time">{{ formatTime(alert.created_at) }}</span>
            </div>
          </div>
          <div class="alert-card-right">
            <el-icon :size="16"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- ═══════════════ KPI明细钻取抽屉 [D3-2] ═══════════════ -->
    <el-drawer
      v-model="kpiDrawerVisible"
      :title="kpiDrawerTitle"
      direction="rtl"
      size="650px"
      :close-on-press-escape="true"
      :close-on-click-modal="false"
      @close="kpiDrawerVisible = false"
    >
      <template #header="{ close }">
        <div class="kpi-drawer-header">
          <el-button class="kpi-drawer-close-btn" text @click="close">
            <el-icon :size="18"><ArrowLeft /></el-icon>
          </el-button>
          <span class="kpi-drawer-title">{{ kpiDrawerTitle }}</span>
        </div>
      </template>

      <div class="kpi-drawer-body">
        <div v-if="kpiDrawerLoading" class="kpi-drawer-loading">
          <el-icon class="is-loading" :size="24"><Loading /></el-icon>
          <span>加载中...</span>
        </div>

        <template v-else>
          <!-- 空状态 -->
          <div v-if="kpiDrawerData.length === 0" class="kpi-drawer-empty">
            <el-icon :size="48" color="var(--c-text-tertiary)"><InfoFilled /></el-icon>
            <p class="empty-title">暂无数据</p>
          </div>

          <!-- 数据表格 -->
          <el-table
            v-else
            :data="kpiDrawerData"
            stripe
            highlight-current-row
            @row-click="onKpiRowClick"
            empty-text="暂无数据"
            style="width: 100%"
          >
            <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip sortable="custom" />
            <el-table-column prop="market" label="市场" width="100" sortable="custom">
              <template #default="{ row }">
                <span>{{ row.market || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100" sortable="custom">
              <template #default="{ row }">
                <el-tag v-if="row.type === 'plan'" :type="stageTagType(row.status)" size="small" effect="plain">
                  {{ stageLabel(row.status) }}
                </el-tag>
                <el-tag v-else-if="row.type === 'project'" :type="statusType(row.status)" size="small" effect="plain">
                  {{ statusLabel(row.status) }}
                </el-tag>
                <el-tag v-else type="info" size="small" effect="plain">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="110" sortable="custom">
              <template #default="{ row }">
                <span class="kpi-cell-date">{{ formatDate(row.created_at) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click.stop="viewKpiDetail(row)">
                  查看
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </template>
      </div>
    </el-drawer>

    <!-- ═══════════════ 二次下钻：策划摘要抽屉 ═══════════════ -->
    <el-drawer
      v-model="summaryDrawerVisible"
      :title="summaryDrawerTitle"
      direction="rtl"
      size="500px"
      @close="summaryDrawerVisible = false"
    >
      <template #header="{ close }">
        <div class="kpi-drawer-header">
          <el-button class="kpi-drawer-close-btn" text @click="close">
            <el-icon :size="18"><ArrowLeft /></el-icon>
          </el-button>
          <span class="kpi-drawer-title">{{ summaryDrawerTitle }}</span>
        </div>
      </template>

      <div v-if="summaryLoading" class="kpi-drawer-loading">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <div v-else-if="!summaryData" class="kpi-drawer-empty">
        <el-icon :size="48" color="var(--c-text-tertiary)"><InfoFilled /></el-icon>
        <p class="empty-title">暂无数据</p>
      </div>

      <div v-else class="summary-content">
        <div class="summary-field">
          <span class="summary-label">策划名称</span>
          <span class="summary-value">{{ summaryData.name }}</span>
        </div>
        <div class="summary-field">
          <span class="summary-label">当前状态</span>
          <el-tag :type="stageTagType(summaryData.status)" size="small" effect="plain">
            {{ stageLabel(summaryData.status) }}
          </el-tag>
        </div>
        <div class="summary-field" v-if="summaryData.series">
          <span class="summary-label">产品系列</span>
          <span class="summary-value">{{ summaryData.series }}</span>
        </div>
        <div class="summary-field" v-if="summaryData.market">
          <span class="summary-label">目标市场</span>
          <span class="summary-value">{{ summaryData.market }}</span>
        </div>
        <div class="summary-field" v-if="summaryData.created_at">
          <span class="summary-label">创建时间</span>
          <span class="summary-value">{{ formatDate(summaryData.created_at) }}</span>
        </div>
        <div class="summary-field" v-if="summaryData.updated_at">
          <span class="summary-label">最近更新</span>
          <span class="summary-value">{{ formatDate(summaryData.updated_at) }}</span>
        </div>

        <div class="summary-actions">
          <el-button type="primary" @click="goToPlanDetail(summaryData)">
            查看完整详情
          </el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'
import {
  DataAnalysis, TrendCharts, Search, Connection, ArrowRight, Refresh,
  Cpu, InfoFilled, CircleCloseFilled, Plus, Folder, Coin, Clock,
  CircleCheck, List,
  WarningFilled, CircleCheckFilled, Time, Loading, ArrowLeft,
} from '@element-plus/icons-vue'
import api from '../../api'
import PieChart from '../../components/charts/PieChart.vue'
import BarChart from '../../components/charts/BarChart.vue'
import LineChart from '../../components/charts/LineChart.vue'
import ChartContainer from '../../components/ChartContainer.vue'
import FunnelChart from '../../components/charts/FunnelChart.vue'
import BiChart from '../../components/BiChart.vue'
import type { TableRow, ChartDataPoint } from '@/types/common'
import { useWebSocket } from '../../composables/useWebSocket'
import type { WebSocketMessage } from '../../composables/useWebSocket'

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

// ── D3-3: 预警类型 ──
interface AlertItemData {
  type: 'overdue' | 'stuck' | 'cost_overrun'
  plan_id: string | number
  plan_name: string
  message: string
  severity: number
  status?: string
  created_at?: string
}

interface AlertsSummaryData {
  overdue_count: number
  stuck_count: number
  cost_overrun_count: number
  alerts: AlertItemData[]
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

// ── D3-3: 预警逻辑 ──
const showAlertDrawer = ref(false)
const alertsLoading = ref(false)
const alertList = ref<AlertItemData[]>([])
const alertsSummary = ref({
  overdue: 0,
  stuck: 0,
  cost_overrun: 0,
  total: 0,
})

function alertTagType(type: string): string {
  const map: Record<string, string> = {
    overdue: 'danger',
    cost_overrun: 'warning',
    stuck: 'warning',
  }
  return map[type] || 'info'
}

function alertLabel(type: string): string {
  const map: Record<string, string> = {
    overdue: '逾期',
    cost_overrun: '超标',
    stuck: '滞留',
  }
  return map[type] || type
}

function formatTime(ts: string): string {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${month}-${day}`
  } catch {
    return ts.substring(0, 10)
  }
}

function goToAlertPlan(alert: AlertItemData): void {
  showAlertDrawer.value = false
  router.push(`/product-plans/${alert.plan_id}`)
}

async function fetchAlertsSummary(): Promise<void> {
  alertsLoading.value = true
  try {
    const res = await api.get('/dashboard/alerts-summary')
    const data: AlertsSummaryData = res.data
    alertList.value = data.alerts || []
    alertsSummary.value = {
      overdue: data.overdue_count || 0,
      stuck: data.stuck_count || 0,
      cost_overrun: data.cost_overrun_count || 0,
      total: (data.overdue_count || 0) + (data.stuck_count || 0) + (data.cost_overrun_count || 0),
    }
  } catch {
    console.warn('[Dashboard] fetchAlertsSummary failed')
    alertList.value = []
    alertsSummary.value = { overdue: 0, stuck: 0, cost_overrun: 0, total: 0 }
  } finally {
    alertsLoading.value = false
  }
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

// ── WebSocket 实时刷新 [D3-5] ─────────────────────────

const { connect: wsConnect, on: wsOn, off: wsOff } = useWebSocket()

const WS_DEBOUNCE_MS = 30000
let lastWsRefreshTime = 0

/** 仪表盘刷新防抖处理 — 30 秒内不重复刷新 */
function handleDashboardRefresh(_msg: WebSocketMessage): void {
  const now = Date.now()
  if (now - lastWsRefreshTime < WS_DEBOUNCE_MS) {
    console.debug('[Dashboard] WS refresh debounced')
    return
  }
  lastWsRefreshTime = now

  // 视觉提示：ElNotification
  ElNotification({
    title: '数据已更新',
    message: '仪表盘数据已自动刷新',
    type: 'success',
    duration: 3000,
    position: 'top-right',
  })

  // 重新加载 BI 图表数据
  fetchBiCharts()
}

function setupWsDashboardRefresh(): void {
  wsConnect()
  wsOff('dashboard_refresh', handleDashboardRefresh) // 防重复注册
  wsOn('dashboard_refresh', handleDashboardRefresh)
}

function refreshAll() {
  fetchDashboard()
  fetchTrends()
  fetchProductPlanSummary()
  fetchBiCharts()
  fetchAlertsSummary()
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

// ── KPI明细抽屉 [D3-2] ─────────────────────────────

const KPI_LABELS: Record<string, string> = {
  in_progress: '进行中策划',
  pending: '待审批',
  completed: '本月完成数',
  overdue: '超期项目',
  all_plans: '全部策划',
}

const kpiDrawerVisible = ref(false)
const kpiDrawerTitle = ref('')
const kpiDrawerLoading = ref(false)
const kpiDrawerData = ref<KpiDetailItem[]>([])

interface KpiDetailItem {
  id: string | number
  name: string
  market?: string | null
  status: string
  series?: string | null
  created_at?: string | null
  updated_at?: string | null
  code?: string | null
  target_end_date?: string | null
  type: string
}

const summaryDrawerVisible = ref(false)
const summaryDrawerTitle = ref('')
const summaryLoading = ref(false)
const summaryData = ref<KpiDetailItem | null>(null)

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  } catch {
    return dateStr.substring(0, 10)
  }
}

async function openKpiDrawer(type: string) {
  kpiDrawerTitle.value = KPI_LABELS[type] || type
  kpiDrawerVisible.value = true
  kpiDrawerLoading.value = true
  kpiDrawerData.value = []

  try {
    const res = await api.get('/dashboard/kpi-detail', { params: { type } })
    const data = (Array.isArray(res.data) ? res.data : []) as KpiDetailItem[]
    kpiDrawerData.value = data
    // Update title with count
    kpiDrawerTitle.value = `${KPI_LABELS[type] || type} (${data.length})`
  } catch {
    console.warn('[Dashboard] kpi-detail fetch failed')
    kpiDrawerData.value = []
  } finally {
    kpiDrawerLoading.value = false
  }
}

/** 表格行点击 → 二次下钻 */
function onKpiRowClick(row: KpiDetailItem) {
  if (row.type === 'plan') {
    viewKpiDetail(row)
  } else if (row.type === 'project') {
    router.push({ path: '/projects', query: { highlight: row.id } })
  } else if (row.type === 'approval') {
    router.push('/approvals/proposals')
  }
}

/** 查看策划详情（二次下钻 — 打开策划摘要抽屉） */
async function viewKpiDetail(row: KpiDetailItem) {
  if (row.type === 'plan') {
    // 打开策划摘要抽屉
    summaryData.value = null
    summaryDrawerTitle.value = `策划摘要 — ${row.name}`
    summaryDrawerVisible.value = true
    summaryLoading.value = true

    try {
      // 尝试从后端获取策划详情
      const res = await api.get(`/product-plans/${row.id}`)
      summaryData.value = (res.data || row) as KpiDetailItem
    } catch {
      // 如果获取失败，使用表格中的数据
      summaryData.value = row
    } finally {
      summaryLoading.value = false
    }
  } else if (row.type === 'project') {
    router.push({ path: '/projects', query: { highlight: row.id } })
  } else if (row.type === 'approval') {
    router.push('/approvals/proposals')
  }
}

/** 从摘要抽屉跳转到完整详情页 */
function goToPlanDetail(row: KpiDetailItem) {
  summaryDrawerVisible.value = false
  kpiDrawerVisible.value = false
  router.push(`/product-plans/${row.id}`)
}

onMounted(() => {
  fetchDashboard()
  fetchTrends()
  fetchProductPlanSummary()
  fetchBiCharts()
  fetchAlertsSummary()
  setupWsDashboardRefresh()
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

/* ═══════════ D3-3: 预警Badge与抽屉 ═══════════ */
.alert-badges {
  display: flex;
  align-items: center;
  gap: 8px;
}
.alert-badge-item {
  margin-top: 4px;
}
.alert-badge-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--c-radius-full);
  border: 1px solid var(--c-border);
  background: var(--c-bg-card);
  color: var(--c-text-secondary);
  cursor: pointer;
  transition: all var(--c-transition-fast);
}
.alert-badge-btn:hover {
  transform: translateY(-1px);
  box-shadow: var(--c-shadow-sm);
}
.alert-btn-danger {
  border-color: #f56c6c;
  color: #f56c6c;
  background: #fef0f0;
}
.alert-btn-danger:hover {
  background: #f56c6c;
  color: #fff;
}
.alert-btn-warning {
  border-color: #e6a23c;
  color: #e6a23c;
  background: #fdf6ec;
}
.alert-btn-warning:hover {
  background: #e6a23c;
  color: #fff;
}
.alert-btn-safe {
  border-color: #67c23a;
  color: #67c23a;
  background: #f0f9eb;
}
.alert-btn-safe:hover {
  background: #67c23a;
  color: #fff;
}

/* ─── 预警抽屉 ─── */
.alert-drawer-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 16px;
}
.alert-drawer-loading,
.alert-drawer-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 60px 20px;
  color: var(--c-text-secondary);
}
.alert-drawer-loading p,
.alert-drawer-empty p {
  margin: 0;
  font-size: 14px;
}
.alert-summary-counts {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: var(--c-bg-hover);
  border-radius: var(--c-radius-md);
}
.alert-count-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--c-text-secondary);
}
.alert-count-item strong {
  font-size: 16px;
  color: var(--c-text-primary);
  margin-left: 2px;
}
.alert-count-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.alert-count-dot.danger { background: #f56c6c; }
.alert-count-dot.warning { background: #e6a23c; }
.alert-count-dot.warning-light { background: #f3d19a; }

.alert-drawer-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.alert-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border-radius: var(--c-radius-md);
  border: 1px solid var(--c-border);
  background: var(--c-bg-card);
  cursor: pointer;
  transition: all var(--c-transition-fast);
}
.alert-card:hover {
  border-color: var(--c-border-dark);
  box-shadow: var(--c-shadow-sm);
  transform: translateX(2px);
}
.alert-card--overdue {
  border-left: 3px solid #f56c6c;
}
.alert-card--stuck {
  border-left: 3px solid #e6a23c;
}
.alert-card--cost_overrun {
  border-left: 3px solid #e6a23c;
}
.alert-card-left {
  flex: 1;
  min-width: 0;
}
.alert-tag {
  margin-bottom: 6px;
}
.alert-card-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text-primary);
  margin-bottom: 4px;
  line-height: 1.3;
}
.alert-card-message {
  font-size: 13px;
  color: var(--c-text-secondary);
  line-height: 1.5;
  margin-bottom: 6px;
}
.alert-card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}
.alert-stage-tag {
  font-size: 11px;
  color: var(--c-text-tertiary);
  background: var(--c-bg-hover);
  padding: 2px 6px;
  border-radius: var(--c-radius-sm);
}
.alert-time {
  font-size: 11px;
  color: var(--c-text-tertiary);
  font-family: var(--c-font-mono);
}
.alert-card-right {
  display: flex;
  align-items: center;
  color: var(--c-text-muted);
  opacity: 0;
  transition: all var(--c-transition-fast);
  padding-top: 12px;
}
.alert-card:hover .alert-card-right {
  opacity: 1;
  color: var(--c-text-tertiary);
}

/* ─── KPI明细抽屉 [D3-2] ─── */
.kpi-drawer-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.kpi-drawer-close-btn {
  font-size: 16px;
  padding: 4px;
  color: var(--c-text-secondary);
}
.kpi-drawer-close-btn:hover {
  color: var(--c-text-primary);
}
.kpi-drawer-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--c-text-primary);
}
.kpi-drawer-body {
  min-height: 200px;
}
.kpi-drawer-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px;
  color: var(--c-text-tertiary);
  font-size: 14px;
}
.kpi-drawer-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 64px 24px;
  color: var(--c-text-tertiary);
}
.kpi-cell-date {
  font-size: 12px;
  color: var(--c-text-tertiary);
  font-family: var(--c-font-mono);
}

/* ─── 策划摘要内容 ─── */
.summary-content {
  padding: 8px 0;
}
.summary-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 0;
  border-bottom: 1px solid var(--c-border-light);
}
.summary-field:last-of-type {
  border-bottom: none;
}
.summary-label {
  font-size: 12px;
  color: var(--c-text-tertiary);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.summary-value {
  font-size: 15px;
  color: var(--c-text-primary);
  font-weight: 500;
}
.summary-actions {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--c-border);
}
</style>
