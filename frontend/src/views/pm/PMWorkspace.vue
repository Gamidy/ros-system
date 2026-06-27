<template>
  <div class="pm-workspace">
    <!-- ═══════════════ 顶部标题 ═══════════════ -->
    <WorkspaceHeader v-model:viewMode="viewMode" />

    <!-- ═══════════════ 路线图视图 ═══════════════ -->
    <template v-if="viewMode === 'roadmap'">
      <RoadmapPanel :items="roadmapData?.roadmap_items || []" />
    </template>

    <!-- ═══════════════ 工作台视图 ═══════════════ -->
    <template v-if="viewMode === 'workspace'">
      <!-- ═══════════════ 统计卡片 ═══════════════ -->
      <StatsCards :statsData="statsData" />

      <!-- ═══════════════ 待处理需求卡片 ═══════════════ -->
      <el-row :gutter="12" style="margin-bottom:16px">
        <el-col :span="4">
          <el-card shadow="never" class="stat-card clickable" @click="$router.push('/pm/requirements')">
            <div class="stat-card-num" style="color:#e6a23c">{{ pendingRequirementCount }}</div>
            <div class="stat-card-label">待处理需求</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- ═══════════════ 快捷入口 ═══════════════ -->
      <QuickLinks />

      <!-- ═══════════════ 三栏布局 ═══════════════ -->
      <div class="workspace-body">
        <!-- 左栏 (30%)：年度产品规划 -->
        <div class="col-left">
          <AnnualPlanList :planning-items="planningItems" />
        </div>
        <!-- 中栏 (40%)：产品立项入口 -->
        <div class="col-middle">
          <ProductInitiation :draft-id="draftId" @open="$router.push('/proposals')" />
        </div>
        <!-- 右栏 (30%)：我的项目看板 -->
        <div class="col-right">
          <MyProjectKanban :projects="myProjects" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import api from '../../api'
import type { PlanningItem, ProjectItem, WorkspaceStats, RoadmapData } from './types'
import { listRequirements } from '../../api/productPlan'

// 子组件
import AnnualPlanList from './AnnualPlanList.vue'
import MyProjectKanban from './MyProjectKanban.vue'
import ProductInitiation from './proposal/ProductInitiation.vue'
import RoadmapPanel from './RoadmapPanel.vue'
import WorkspaceHeader from './WorkspaceHeader.vue'
import StatsCards from './StatsCards.vue'
import QuickLinks from './QuickLinks.vue'

// ═══════════════════════════════════════════════
// 响应式数据
// ═══════════════════════════════════════════════

// 年度规划
const planningItems = ref<PlanningItem[]>([])

// 项目
const myProjects = ref<ProjectItem[]>([])

// 草稿ID（从workspace API获取）
const draftId = ref<number | null>(null)

// 统计卡片数据
const statsData = ref<WorkspaceStats | null>(null)

// 视图模式
const viewMode = ref<'workspace' | 'roadmap'>('workspace')
const roadmapData = ref<RoadmapData | null>(null)

// 待处理需求计数
const pendingRequirementCount = ref(0)

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

/** 获取待处理需求数量 */
async function fetchPendingRequirementCount() {
  try {
    const res = await listRequirements({ status: 'pending', page_size: 1 })
    pendingRequirementCount.value = res.data?.total ?? 0
  } catch {
    // 静默失败
  }
}

// ═══════════════════════════════════════════════
// 视图切换时按需加载路线图数据
// ═══════════════════════════════════════════════

watch(viewMode, (mode) => {
  if (mode === 'roadmap' && !roadmapData.value) {
    fetchRoadmap()
  }
})

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
    await fetchPendingRequirementCount()
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

/* 移动端响应式 */
@media (max-width: 768px) {
  .workspace-body { flex-direction: column; }
  .col-left, .col-middle, .col-right { flex: none; width: 100%; }
}

/* 统计卡片样式（与 StatsCards 对齐） */
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
.clickable {
  cursor: pointer;
  transition: all 0.2s;
}
.clickable:hover {
  border-color: #409eff;
  background: #f0f6ff;
  transform: translateY(-1px);
}
</style>
