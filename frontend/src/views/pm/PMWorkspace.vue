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
</style>
