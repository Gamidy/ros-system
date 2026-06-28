<template>
  <div class="compare-page">
    <div class="page-header">
      <h2>项目对比</h2>
      <div class="header-actions">
        <el-select v-model="selectedIds" multiple placeholder="选择项目对比(2-4个)" style="width:360px" filterable @change="onSelectChange">
          <el-option v-for="p in allProjects" :key="p.id" :label="`${p.code} ${p.name}`" :value="p.id" />
        </el-select>
        <el-button type="primary" size="small" :disabled="selectedIds.length < 2" @click="loadComparison">对比</el-button>
      </div>
    </div>

    <el-empty v-if="projects.length === 0 && !loading" description="请选择2-4个项目进行对比" />

    <div v-if="projects.length >= 2" class="compare-content">
      <!-- 概览对比表 -->
      <el-card shadow="never" class="section-card">
        <template #header><span>📋 基本信息</span></template>
        <el-table :data="baseRows" border stripe size="small">
          <el-table-column prop="label" label="属性" width="160" />
          <el-table-column v-for="p in projects" :key="p.id" :label="p.code" min-width="140">
            <template #default="{ row }">
              {{ row[p.id] || '-' }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- Gate状态对比 -->
      <el-card shadow="never" class="section-card">
        <template #header><span>🚪 Gate状态</span></template>
        <el-table :data="gateRows" border stripe size="small">
          <el-table-column prop="label" label="Gate" width="160" />
          <el-table-column v-for="p in projects" :key="p.id" :label="p.code" min-width="140">
            <template #default="{ row }">
              <el-tag :type="gateTag(row[p.id]?.status)" size="small">
                {{ gateLabel(row[p.id]?.status) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 任务统计对比 -->
      <el-card shadow="never" class="section-card">
        <template #header><span>📊 任务统计</span></template>
        <el-table :data="taskRows" border stripe size="small">
          <el-table-column prop="label" label="指标" width="160" />
          <el-table-column v-for="p in projects" :key="p.id" :label="p.code" min-width="140">
            <template #default="{ row }">
              {{ row[p.id] ?? '-' }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 风险对比 -->
      <el-card shadow="never" class="section-card">
        <template #header><span>⚠️ 风险对比</span></template>
        <el-table :data="riskRows" border stripe size="small">
          <el-table-column prop="label" label="指标" width="160" />
          <el-table-column v-for="p in projects" :key="p.id" :label="p.code" min-width="140">
            <template #default="{ row }">
              {{ row[p.id] ?? '-' }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const allProjects = ref<any[]>([])
const selectedIds = ref<number[]>([])
const projects = ref<any[]>([])
const loading = ref(false)

const baseRows = ref<any[]>([])
const gateRows = ref<any[]>([])
const taskRows = ref<any[]>([])
const riskRows = ref<any[]>([])

function gateTag(s: string | null) {
  return ({ passed: 'success', failed: 'danger', skipped: 'info', pending: 'warning' })[s || ''] || 'info'
}
function gateLabel(s: string | null) {
  return ({ passed: '通过', failed: '失败', skipped: '跳过', pending: '待定' })[s || ''] || s || '-'
}

async function fetchAllProjects() {
  try {
    const r = await api.get('/projects/dashboard/overview')
    allProjects.value = r.data?.projects || []
  } catch { /* ignore */ }
}

function onSelectChange() {
  if (selectedIds.value.length > 4) {
    ElMessage.warning('最多对比4个项目')
    selectedIds.value = selectedIds.value.slice(0, 4)
  }
}

async function loadComparison() {
  if (selectedIds.value.length < 2) return
  loading.value = true
  try {
    const r = await api.post('/projects/compare', { project_ids: selectedIds.value })
    const data = r.data as any
    projects.value = data.projects || []

    // Build comparison tables
    baseRows.value = [
      { label: '项目名称', ...Object.fromEntries(projects.value.map((p: any) => [p.id, p.name])) },
      { label: '项目等级', ...Object.fromEntries(projects.value.map((p: any) => [p.id, p.project_class])) },
      { label: '状态', ...Object.fromEntries(projects.value.map((p: any) => [p.id, p.status])) },
      { label: '来源', ...Object.fromEntries(projects.value.map((p: any) => [p.id, p.source || '-'])) },
      { label: '项目经理', ...Object.fromEntries(projects.value.map((p: any) => [p.id, p.owner || '-'])) },
      { label: '开始日期', ...Object.fromEntries(projects.value.map((p: any) => [p.id, p.start_date || '-'])) },
      { label: '截止日期', ...Object.fromEntries(projects.value.map((p: any) => [p.id, p.target_end_date || '-'])) },
      { label: '预算(元)', ...Object.fromEntries(projects.value.map((p: any) => [p.id, p.budget != null ? '¥' + p.budget.toLocaleString() : '-'])) },
    ]

    gateRows.value = (data.gates || []).map((g: any) => ({
      label: `${g.gate_code} ${g.gate_name}`,
      ...Object.fromEntries((g.per_project || []).map((pg: any) => [pg.project_id, { status: pg.status }])),
    }))

    taskRows.value = [
      { label: '总任务', ...Object.fromEntries(projects.value.map((p: any) => [p.id, p._taskStats?.total ?? '-'])) },
      { label: '待办', ...Object.fromEntries(projects.value.map((p: any) => [p.id, p._taskStats?.todo ?? '-'])) },
      { label: '进行中', ...Object.fromEntries(projects.value.map((p: any) => [p.id, p._taskStats?.in_progress ?? '-'])) },
      { label: '已完成', ...Object.fromEntries(projects.value.map((p: any) => [p.id, p._taskStats?.done ?? '-'])) },
    ]

    riskRows.value = [
      { label: '总风险', ...Object.fromEntries(projects.value.map((p: any) => [p.id, p._riskStats?.total ?? '-'])) },
      { label: 'A级风险', ...Object.fromEntries(projects.value.map((p: any) => [p.id, p._riskStats?.a_level ?? '-'])) },
    ]
  } catch (e: unknown) {
    ElMessage.error('加载对比数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchAllProjects)
</script>

<style scoped>
.compare-page { padding: 16px 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.header-actions { display: flex; gap: 8px; }
.section-card { margin-bottom: 16px; }
</style>
