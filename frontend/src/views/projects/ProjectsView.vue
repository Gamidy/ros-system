<template>
  <div class="projects-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>项目管理 · Program → Project(T/A/B/C) → M1~M9 Gate → Risk</span>
          <el-button type="primary" @click="fetchAll">刷新</el-button>
        </div>
      </template>

      <el-tabs v-model="tab" @tab-change="onTabChange">
        <!-- Programs -->
        <el-tab-pane label="项目群 Program" name="programs">
          <el-button type="primary" size="small" style="margin-bottom:12px" @click="showProgramDialog=true">新建项目群</el-button>
          <el-table :data="programs" stripe border size="small">
            <el-table-column prop="code" label="编号" width="150" />
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="status" label="状态" width="80" />
            <el-table-column prop="start_date" label="开始" width="100" />
            <el-table-column prop="end_date" label="结束" width="100" />
          </el-table>
        </el-tab-pane>

        <!-- Projects -->
        <el-tab-pane label="项目列表" name="projects">
          <div class="toolbar">
            <el-button type="primary" size="small" @click="showProjectDialog=true">新建项目</el-button>
            <el-button size="small" @click="$router.push('/projects/compare')">项目对比</el-button>
            <el-select v-model="filterClass" placeholder="等级" clearable size="small" style="width:100px;margin-left:8px">
              <el-option v-for="c in ['T','A','B','C']" :key="c" :label="c+'级'" :value="c" />
            </el-select>
            <el-select v-model="filterStatus" placeholder="状态" clearable size="small" style="width:100px;margin-left:8px">
              <el-option v-for="s in ['planning','running','completed','paused','cancelled']" :key="s" :label="s" :value="s" />
            </el-select>
          </div>
          <el-table :data="filteredProjects" stripe border size="small" @row-click="openProjectDetail">
            <el-table-column prop="code" label="编号" width="120" />
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="project_class" label="等级" width="60">
              <template #default="{ row }">
                <el-tag :type="classColor(row.project_class)" size="small">{{ row.project_class }}级</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="source" label="场景" width="100" />
            <el-table-column prop="product_code" label="产品" width="100" />
            <el-table-column prop="owner" label="项目经理" width="90" />
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }"><el-tag size="small">{{ row.status }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="target_end_date" label="目标日期" width="100" />
          </el-table>
        </el-tab-pane>

        <!-- Risk Center -->
        <el-tab-pane label="风险中心" name="risks">
          <el-table :data="allRisks" stripe border size="small">
            <el-table-column prop="title" label="风险描述" />
            <el-table-column prop="risk_level" label="等级" width="70">
              <template #default="{ row }"><el-tag :type="riskColor(row.risk_level)" size="small">{{ row.risk_level }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="risk_source" label="来源" width="80" />
            <el-table-column prop="probability" label="概率" width="70" />
            <el-table-column prop="impact" label="影响" width="70" />
            <el-table-column prop="status" label="状态" width="80" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- Program Dialog -->
    <el-dialog v-model="showProgramDialog" title="新建项目群" width="500">
      <el-form :model="pgForm" label-width="80" size="small">
        <el-form-item label="编号"><el-input v-model="pgForm.code" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="pgForm.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="pgForm.description" type="textarea" /></el-form-item>
        <el-form-item label="开始"><el-date-picker v-model="pgForm.start_date" type="date" /></el-form-item>
        <el-form-item label="结束"><el-date-picker v-model="pgForm.end_date" type="date" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showProgramDialog=false">取消</el-button><el-button type="primary" @click="saveProgram">保存</el-button></template>
    </el-dialog>

    <!-- Project Dialog -->
    <el-dialog v-model="showProjectDialog" title="新建项目" width="600">
      <el-form :model="pjForm" label-width="90" size="small">
        <el-form-item label="项目编号"><el-input v-model="pjForm.code" /></el-form-item>
        <el-form-item label="项目名称"><el-input v-model="pjForm.name" /></el-form-item>
        <el-form-item label="项目等级">
          <el-select v-model="pjForm.project_class">
            <el-option v-for="c in ['T','A','B','C']" :key="c" :label="`${c}级`" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目场景">
          <el-select v-model="pjForm.source">
            <el-option v-for="s in sources" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联产品"><el-input v-model="pjForm.product_code" /></el-form-item>
        <el-form-item label="开发模块"><el-input v-model="pjForm.dev_modules" placeholder='JSON: ["结构","系统"]' /></el-form-item>
        <el-form-item label="变更影响"><el-input v-model="pjForm.change_impacts" placeholder='JSON: ["性能","认证"]' /></el-form-item>
        <el-form-item label="项目经理"><el-input v-model="pjForm.owner" /></el-form-item>
        <el-form-item label="目标日期"><el-date-picker v-model="pjForm.target_end_date" type="date" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showProjectDialog=false">取消</el-button><el-button type="primary" @click="saveProject">保存并生成M1~M9</el-button></template>
    </el-dialog>

    <!-- Project Detail Dialog -->
    <el-dialog v-model="showDetailDialog" :title="`${detailProject?.code} - ${detailProject?.name}`" width="900" top="5vh">
      <template v-if="detailProject">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="等级"><el-tag :type="classColor(detailProject.project_class)">{{ detailProject.project_class }}级</el-tag></el-descriptions-item>
          <el-descriptions-item label="场景">{{ detailProject.source }}</el-descriptions-item>
          <el-descriptions-item label="产品">{{ detailProject.product_code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="项目经理">{{ detailProject.owner || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态"><el-tag>{{ detailProject.status }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="目标">{{ detailProject.target_end_date || '-' }}</el-descriptions-item>
        </el-descriptions>

        <!-- Gates -->
        <el-divider>M1~M9 Gate 节点</el-divider>
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px">
          <el-card v-for="g in detailGates" :key="g.gate_code" shadow="hover"
            :class="['gate-card', g.status === 'passed' ? 'gate-passed' : g.is_high_risk_zone ? 'gate-risk' : '']"
            style="flex:0 0 calc(33% - 8px);min-width:180px"
          >
            <template #header>
              <div style="display:flex;justify-content:space-between;align-items:center">
                <b>{{ g.gate_code }} {{ g.gate_name }}</b>
                <el-tag :type="gateStatusColor(g.status)" size="small">{{ g.status }}</el-tag>
              </div>
            </template>
            <div style="font-size:12px">
              <div v-if="g.decision_level">决策: {{ g.decision_level }}</div>
              <div>计划: {{ g.planned_date || '-' }}</div>
              <div>实际: {{ g.actual_date || '-' }}</div>
              <el-select v-model="g._newStatus" size="small" placeholder="更新状态" style="width:100%;margin-top:4px" @change="(v: string) => updateGate(g.id, v)">
                <el-option label="通过 passed" value="passed" />
                <el-option label="失败 failed" value="failed" />
                <el-option label="跳过 skipped" value="skipped" />
              </el-select>
            </div>
          </el-card>
        </div>

        <!-- Tasks -->
        <el-divider>任务 Task</el-divider>
        <el-button type="primary" size="small" @click="showTaskDialog=true" style="margin-bottom:8px">新增任务</el-button>
        <el-table :data="detailTasks" stripe border size="small">
          <el-table-column prop="title" label="任务" />
          <el-table-column prop="assignee" label="负责人" width="80" />
          <el-table-column prop="status" label="状态" width="90" />
          <el-table-column prop="priority" label="优先级" width="70" />
          <el-table-column prop="due_date" label="截止" width="100" />
        </el-table>

        <!-- Risks -->
        <el-divider>风险 Risk</el-divider>
        <el-button type="warning" size="small" @click="showRiskDialog=true" style="margin-bottom:8px">新增风险</el-button>
        <el-table :data="detailRisks" stripe border size="small">
          <el-table-column prop="title" label="风险" />
          <el-table-column prop="risk_level" label="等级" width="60" />
          <el-table-column prop="risk_source" label="来源" width="70" />
          <el-table-column prop="status" label="状态" width="80" />
          <el-table-column prop="mitigation" label="缓解措施" />
        </el-table>
      </template>
      <template #footer><el-button @click="showDetailDialog=false">关闭</el-button></template>
    </el-dialog>

    <!-- Task Dialog -->
    <el-dialog v-model="showTaskDialog" title="新增任务" width="450">
      <el-form :model="taskForm" label-width="70" size="small">
        <el-form-item label="标题"><el-input v-model="taskForm.title" /></el-form-item>
        <el-form-item label="负责人"><el-input v-model="taskForm.assignee" /></el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="taskForm.priority"><el-option v-for="p in ['low','medium','high','urgent']" :key="p" :label="p" :value="p" /></el-select>
        </el-form-item>
        <el-form-item label="截止"><el-date-picker v-model="taskForm.due_date" type="date" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showTaskDialog=false">取消</el-button><el-button type="primary" @click="saveTask">保存</el-button></template>
    </el-dialog>

    <!-- Risk Dialog -->
    <el-dialog v-model="showRiskDialog" title="新增风险" width="450">
      <el-form :model="riskForm" label-width="70" size="small">
        <el-form-item label="标题"><el-input v-model="riskForm.title" /></el-form-item>
        <el-form-item label="等级">
          <el-select v-model="riskForm.risk_level"><el-option v-for="r in ['A','B','C']" :key="r" :label="r+'级'" :value="r" /></el-select>
        </el-form-item>
        <el-form-item label="来源"><el-select v-model="riskForm.risk_source"><el-option v-for="s in ['模具','物料','认证','人员','外部']" :key="s" :label="s" :value="s" /></el-select></el-form-item>
        <el-form-item label="概率"><el-select v-model="riskForm.probability"><el-option v-for="p in ['low','medium','high']" :key="p" :label="p" :value="p" /></el-select></el-form-item>
        <el-form-item label="影响"><el-select v-model="riskForm.impact"><el-option v-for="p in ['low','medium','high']" :key="p" :label="p" :value="p" /></el-select></el-form-item>
        <el-form-item label="措施"><el-input v-model="riskForm.mitigation" type="textarea" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showRiskDialog=false">取消</el-button><el-button type="primary" @click="saveRisk">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../../api'

const router = useRouter()

const tab = ref('projects')
const programs = ref<any[]>([])
const projects = ref<any[]>([])
const allRisks = ref<any[]>([])

const filterClass = ref('')
const filterStatus = ref('')

const showProgramDialog = ref(false)
const showProjectDialog = ref(false)
const showDetailDialog = ref(false)
const showTaskDialog = ref(false)
const showRiskDialog = ref(false)

const pgForm = ref({ code: '', name: '', description: '', start_date: null, end_date: null })
const pjForm = ref({ code: '', name: '', project_class: 'B', source: '', product_code: '', dev_modules: '', change_impacts: '', owner: '', target_end_date: null })
const taskForm = ref({ title: '', assignee: '', priority: 'medium', due_date: null })
const riskForm = ref({ title: '', risk_level: 'B', risk_source: '', probability: 'medium', impact: 'medium', mitigation: '' })

const detailProject = ref<any>(null)
const detailGates = ref<any[]>([])
const detailTasks = ref<any[]>([])
const detailRisks = ref<any[]>([])

const sources = ['年度规划', '客户需求', '品质整改', '研发降本', '供应链二供', '工艺提效', '法规升级']

const filteredProjects = computed(() => {
  let list = projects.value
  if (filterClass.value) list = list.filter((p: Record<string, unknown>) => p.project_class === filterClass.value)
  if (filterStatus.value) list = list.filter((p: Record<string, unknown>) => p.status === filterStatus.value)
  return list
})

function classColor(c: string) { return { T: 'danger', A: 'warning', B: 'success', C: 'info' }[c] || 'info' }
function riskColor(r: string) { return { A: 'danger', B: 'warning', C: 'info' }[r] || 'info' }
function gateStatusColor(s: string) { return { pending: 'info', passed: 'success', failed: 'danger', skipped: 'warning' }[s] || 'info' }

async function fetchAll() {
  try {
    const [pg, pj] = await Promise.all([api.get('/programs'), api.get('/projects')])
    programs.value = pg.data
    projects.value = pj.data
  } catch {}
}

async function onTabChange(name: string) {
  if (name === 'risks') {
    try {
      const all = await Promise.all(projects.value.map((p: Record<string, unknown>) => api.get(`/projects/${p.id}/risks`).catch(() => ({ data: [] }))))
      allRisks.value = all.flatMap((r: { data: unknown }) => r.data)
    } catch {}
  }
}

async function saveProgram() {
  try { await api.post('/programs', pgForm.value); ElMessage.success('成功'); showProgramDialog.value = false; await fetchAll() } catch {}
}

async function saveProject() {
  try { await api.post('/projects', pjForm.value); ElMessage.success('项目创建成功，M1~M9已自动生成'); showProjectDialog.value = false; pjForm.value = { ...pjForm.value, code: '', name: '' }; await fetchAll() } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '创建项目失败，请检查必填字段')
  }
}

async function openProjectDetail(row: Record<string, unknown>) {
  router.push(`/projects/${row.id}`)
}

async function updateGate(gateId: number, status: string) {
  try { await api.patch(`/projects/gates/${gateId}`, { status }); ElMessage.success('Gate更新') } catch {}
}

async function saveTask() {
  try { await api.post(`/projects/${detailProject.value.id}/tasks`, taskForm.value); ElMessage.success('任务创建'); showTaskDialog.value = false } catch {}
}

async function saveRisk() {
  try { await api.post(`/projects/${detailProject.value.id}/risks`, riskForm.value); ElMessage.success('风险记录'); showRiskDialog.value = false } catch {}
}

onMounted(fetchAll)
</script>

<style scoped>
.card-header { display:flex; justify-content:space-between; align-items:center; font-weight:bold; }
.toolbar { margin-bottom:12px; }
.gate-card { cursor:pointer; }
.gate-passed { border-left:4px solid #67c23a; }
.gate-risk { border-left:4px solid #f56c6c; }
</style>
