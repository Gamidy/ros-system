<template>
  <div class="page">
    <el-card shadow="never" style="margin-bottom: 16px">
      <template #header>
        <div class="card-header">
          <span>认证项目详情</span>
          <el-button @click="$router.push('/s2/projects')">返回列表</el-button>
        </div>
      </template>
      <el-descriptions :column="3" border v-loading="loading">
        <el-descriptions-item label="项目编码">{{ project.code }}</el-descriptions-item>
        <el-descriptions-item label="名称">{{ project.name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusType(project.status)" size="small">{{ statusLabel(project.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="关联项目ID">{{ project.project_id }}</el-descriptions-item>
        <el-descriptions-item label="目标市场ID">{{ project.target_market_id }}</el-descriptions-item>
        <el-descriptions-item label="认证类型">
          <el-tag v-for="t in parsedCertTypes" :key="t" :type="certTagType(t)" size="small" style="margin-right: 4px">{{ t }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="计划开始">{{ project.planned_start_date?.slice(0, 10) }}</el-descriptions-item>
        <el-descriptions-item label="计划结束">{{ project.planned_end_date?.slice(0, 10) }}</el-descriptions-item>
        <el-descriptions-item label="备注">{{ project.remark }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="关联样机" name="samples">
          <el-table :data="samples" stripe border v-loading="loadingSamples" max-height="350">
            <el-table-column prop="sample_no" label="样机编号" width="180" />
            <el-table-column prop="prototype_id" label="关联Prototype" width="120" />
            <el-table-column prop="cert_type" label="认证类型" width="100">
              <template #default="{ row }"><el-tag size="small">{{ row.cert_type }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }"><el-tag :type="sampleStatusType(row.status)" size="small">{{ sampleStatusLabel(row.status) }}</el-tag></template>
            </el-table-column>
            <el-table-column :label="'提交日期'" width="120">
              <template #default="{ row }">{{ row.submitted_date?.slice(0, 10) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="执行记录" name="executions">
          <el-table :data="executions" stripe border v-loading="loadingExec" max-height="350">
            <el-table-column prop="id" label="执行ID" width="80" />
            <el-table-column prop="lab" label="实验室" width="150" />
            <el-table-column prop="agency" label="代理机构" width="150" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }"><el-tag :type="execStatusType(row.status)" size="small">{{ execStatusLabel(row.status) }}</el-tag></template>
            </el-table-column>
            <el-table-column :label="'开始日期'" width="120">
              <template #default="{ row }">{{ row.start_date?.slice(0, 10) }}</template>
            </el-table-column>
            <el-table-column :label="'结束日期'" width="120">
              <template #default="{ row }">{{ row.end_date?.slice(0, 10) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="认证结果" name="results">
          <el-table :data="results" stripe border v-loading="loadingResults" max-height="350">
            <el-table-column prop="id" label="结果ID" width="80" />
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }"><el-tag :type="resultStatusType(row.status)" size="small">{{ resultStatusLabel(row.status) }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="summary" label="总结" min-width="200" />
            <el-table-column :label="'结果日期'" width="120">
              <template #default="{ row }">{{ row.result_date?.slice(0, 10) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../api'

const route = useRoute()
const project = ref<Record<string, unknown>>({})
const loading = ref(false)
const activeTab = ref('samples')
const samples = ref<Record<string, unknown>[]>([])
const loadingSamples = ref(false)
const executions = ref<Record<string, unknown>[]>([])
const loadingExec = ref(false)
const results = ref<Record<string, unknown>[]>([])
const loadingResults = ref(false)

const parsedCertTypes = computed(() => {
  const ct = project.value.cert_types
  if (!ct) return []
  try { return JSON.parse(ct) } catch { return [ct] }
})

const statusMap: Record<string, string> = { planning: '计划中', in_progress: '进行中', completed: '已完成', failed: '失败', on_hold: '暂停', cancelled: '已取消' }
const statusTypeMap: Record<string, string> = { planning: 'info', in_progress: 'primary', completed: 'success', failed: 'danger', on_hold: 'warning', cancelled: 'info' }
function statusLabel(s: string) { return statusMap[s] || s }
function statusType(s: string) { return (statusTypeMap[s] || 'info') as string }

const sampleStatusMap: Record<string, string> = { pending: '待提交', preparing: '准备中', submitted: '已提交', testing: '测试中', passed: '通过', failed: '失败' }
const sampleStatusTypeMap: Record<string, string> = { pending: 'info', preparing: 'warning', submitted: 'primary', testing: 'warning', passed: 'success', failed: 'danger' }
function sampleStatusLabel(s: string) { return sampleStatusMap[s] || s }
function sampleStatusType(s: string) { return (sampleStatusTypeMap[s] || 'info') as string }

const execStatusMap: Record<string, string> = { pending: '待开始', in_progress: '进行中', completed: '已完成', failed: '失败' }
const execStatusTypeMap: Record<string, string> = { pending: 'info', in_progress: 'primary', completed: 'success', failed: 'danger' }
function execStatusLabel(s: string) { return execStatusMap[s] || s }
function execStatusType(s: string) { return (execStatusTypeMap[s] || 'info') as string }

const resultStatusMap: Record<string, string> = { draft: '草稿', submitted: '已提交', testing: '测试中', passed: '通过', failed: '失败', expired: '过期' }
const resultStatusTypeMap: Record<string, string> = { draft: 'info', submitted: 'primary', testing: 'warning', passed: 'success', failed: 'danger', expired: 'info' }
function resultStatusLabel(s: string) { return resultStatusMap[s] || s }
function resultStatusType(s: string) { return (resultStatusTypeMap[s] || 'info') as string }

function certTagType(t: string) { const map: Record<string, string> = { CE: 'danger', CB: 'warning', UL: 'primary', SAA: 'success' }; return map[t] || 'info' }

async function fetchProject() {
  loading.value = true
  try {
    const res = await api.get(`/s2/certification-projects/${route.params.id}`)
    project.value = res.data || {}
  } finally { loading.value = false }
}

async function fetchSamples() {
  loadingSamples.value = true
  try {
    const res = await api.get(`/s2/certification-samples?cert_project_id=${route.params.id}`)
    samples.value = res.data || []
  } finally { loadingSamples.value = false }
}

async function fetchExecutions() {
  loadingExec.value = true
  try {
    const res = await api.get('/s2/certification-executions')
    const all = res.data || []
    // Filter by sample ids belonging to this project
    if (samples.value.length) {
      const sampleIds = new Set(samples.value.map((s: Record<string, unknown>) => s.id))
      executions.value = all.filter((e: Record<string, unknown>) => sampleIds.has(e.cert_sample_id))
    } else {
      executions.value = []
    }
  } finally { loadingExec.value = false }
}

async function fetchResults() {
  loadingResults.value = true
  try {
    const res = await api.get('/s2/certification-results')
    const all = res.data || []
    if (executions.value.length) {
      const execIds = new Set(executions.value.map((e: Record<string, unknown>) => e.id))
      results.value = all.filter((r: Record<string, unknown>) => execIds.has(r.cert_execution_id))
    } else {
      results.value = []
    }
  } finally { loadingResults.value = false }
}

watch(activeTab, (tab) => {
  if (tab === 'samples' && !samples.value.length) fetchSamples()
  if (tab === 'executions' && !executions.value.length) {
    if (!samples.value.length) fetchSamples().then(fetchExecutions)
    else fetchExecutions()
  }
  if (tab === 'results' && !results.value.length) {
    fetchExecutions().then(fetchResults)
  }
})

onMounted(async () => {
  await fetchProject()
  await fetchSamples()
})
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
