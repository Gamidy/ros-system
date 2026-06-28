<template>
  <div class="project-detail-page">
    <div v-if="loading" class="loading-container">
      <el-spinner :size="48" />
      <p style="margin-top: 12px; color: #909399">加载中...</p>
    </div>

    <template v-else>
      <div class="top-bar">
        <el-button text @click="router.push('/projects')">← 返回项目列表</el-button>
        <el-divider direction="vertical" />
        <span class="breadcrumb-current">{{ project?.code }} {{ project?.name }}</span>
        <div style="flex:1" />
        <el-button size="small" type="primary" plain @click="router.push('/projects/' + pid + '/gantt')">
          <el-icon style="margin-right:4px"><View /></el-icon>甘特图
        </el-button>
      </div>

      <!-- 1. Project Header Card -->
      <el-card shadow="never" class="section-card">
        <div class="header-content">
          <div class="header-left">
            <div class="project-title">
              <span class="project-code-name">{{ project?.code }} {{ project?.name }}</span>
              <el-tag :type="classTag(project?.project_class)" size="small">{{ project?.project_class }}级</el-tag>
            </div>
            <div class="project-meta">
              <span v-if="project?.owner">项目经理: {{ project?.owner }}</span>
              <span v-if="project?.source">来源: {{ project?.source }}</span>
              <span v-if="project?.product_code">产品: {{ project?.product_code }}</span>
            </div>
          </div>
          <div class="header-right">
            <el-card shadow="hover" class="health-card">
              <el-icon :size="20" :color="healthColor">
                <CircleCheckFilled v-if="dashboard?.health === 'on_track'" />
                <WarningFilled v-else-if="dashboard?.health === 'at_risk'" />
                <CircleCloseFilled v-else />
              </el-icon>
              <div class="health-text">
                <span class="health-label">项目健康度</span>
                <span class="health-value" :style="{ color: healthColor }">{{ healthLabel }}</span>
              </div>
            </el-card>
            <el-card v-if="dashboard?.days_remaining !== null && dashboard?.days_remaining !== undefined" shadow="hover" class="health-card">
              <el-icon :size="20" color="#409eff"><Clock /></el-icon>
              <div class="health-text">
                <span class="health-label">剩余天数</span>
                <span class="health-value" :style="{ color: dashboard.days_remaining < 0 ? '#f56c6c' : '#67c23a' }">
                  {{ dashboard.days_remaining >= 0 ? dashboard.days_remaining + '天' : '已超期' + Math.abs(dashboard.days_remaining) + '天' }}
                </span>
              </div>
            </el-card>
            <el-card shadow="hover" class="health-card">
              <el-icon :size="20" color="#909399"><Monitor /></el-icon>
              <div class="health-text">
                <span class="health-label">项目状态</span>
                <el-tag :type="statusTag(project?.status)" size="small">{{ statusLabel(project?.status) }}</el-tag>
              </div>
            </el-card>
          </div>
        </div>
      </el-card>

      <!-- 2. Gate Progress Bar -->
      <el-card shadow="never" class="section-card">
        <template #header><span class="section-title">Gate 进度</span></template>
        <div class="gate-stepper">
          <template v-for="(gate, idx) in gates" :key="gate.gate_code">
            <div class="gate-step" @click="openGateDialog(gate)">
              <div class="gate-circle" :class="'gc-' + (gate.status || 'pending')">
                <span class="gate-code">{{ gate.gate_code }}</span>
              </div>
              <span class="gate-label">{{ gate.gate_name }}</span>
            </div>
            <div v-if="idx < gates.length - 1" class="gate-connector" :class="gate.status === 'passed' ? 'conn-passed' : 'conn-pending'" />
          </template>
        </div>
      </el-card>

      <!-- 3. Tabbed Content -->
      <el-card shadow="never" class="section-card">
        <el-tabs v-model="activeTab">
          <!-- Tab 1: Tasks -->
          <el-tab-pane label="任务管理" name="tasks">
            <div class="kpi-row">
              <el-statistic title="总任务" :value="taskStats.total" />
              <el-statistic title="待办" :value="taskStats.todo" />
              <el-statistic title="进行中" :value="taskStats.in_progress" />
              <el-statistic title="已完成" :value="taskStats.done" />
              <el-statistic title="阻塞" :value="taskStats.blocked" />
            </div>
            <div class="toolbar">
              <el-button type="primary" size="small" @click="showTaskDialog = true">新建任务</el-button>
            </div>
            <el-table :data="tasks" stripe border size="small" style="width: 100%">
              <el-table-column prop="title" label="任务" min-width="150" show-overflow-tooltip />
              <el-table-column prop="assignee" label="负责人" width="80" />
              <el-table-column label="优先级" width="80">
                <template #default="{ row }"><el-tag :type="priorityTag(row.priority)" size="small">{{ row.priority }}</el-tag></template>
              </el-table-column>
              <el-table-column prop="due_date" label="截止" width="100" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }"><el-tag :type="taskStatusTag(row.status)" size="small">{{ taskStatusLabel(row.status) }}</el-tag></template>
              </el-table-column>
              <el-table-column label="操作" width="210" fixed="right">
                <template #default="{ row }">
                  <el-button v-if="row.status !== 'done'" text size="small" type="success" @click="updateTask(row, 'done')">完成</el-button>
                  <el-button v-if="row.status !== 'blocked'" text size="small" type="danger" @click="updateTask(row, 'blocked')">阻塞</el-button>
                  <el-select v-model="row._is" size="small" placeholder="改状态" style="width: 85px" @change="(v: string) => updateTask(row, v)">
                    <el-option label="待办" value="todo" /><el-option label="进行中" value="in_progress" /><el-option label="已完成" value="done" /><el-option label="阻塞" value="blocked" />
                  </el-select>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- Tab 2: Kanban -->
          <el-tab-pane label="看板" name="kanban">
            <TaskKanbanTab
              :tasks="tasks"
              @new-task="showTaskDialog = true"
              @update-status="updateTaskById"
              @switch-view="activeTab = 'tasks'"
            />
          </el-tab-pane>

          <!-- Tab 2: Milestones -->
          <el-tab-pane label="里程碑" name="milestones">
            <div class="kpi-row">
              <el-statistic title="总数" :value="msStats.total" />
              <el-statistic title="已达成" :value="msStats.achieved" />
              <el-statistic title="已延期" :value="msStats.delayed" />
            </div>
            <div class="toolbar">
              <el-button type="primary" size="small" @click="showMsDialog = true">新建里程碑</el-button>
            </div>
            <div class="ms-list">
              <div v-for="m in milestones" :key="m.id" class="ms-item">
                <div class="ms-badge" :class="'msb-' + m.status">
                  <el-icon><Check v-if="m.status === 'achieved'" /><Warning v-else-if="m.status === 'delayed'" /><MoreFilled v-else /></el-icon>
                </div>
                <div class="ms-body">
                  <div class="ms-name">{{ m.name }}</div>
                  <div class="ms-dates">
                    <span>计划: {{ m.planned_date || '-' }}</span>
                    <span v-if="m.actual_date">实际: {{ m.actual_date }}</span>
                  </div>
                </div>
                <el-tag :type="msTag(m.status)" size="small" class="ms-status-tag">{{ msLabel(m.status) }}</el-tag>
                <div class="ms-actions">
                  <el-button v-if="m.status !== 'achieved'" text size="small" type="success" @click="updateMs(m, 'achieved')">标记达成</el-button>
                  <el-button v-if="m.status !== 'delayed'" text size="small" type="warning" @click="updateMs(m, 'delayed')">已延期</el-button>
                </div>
              </div>
              <el-empty v-if="milestones.length === 0" description="暂无里程碑" />
            </div>
          </el-tab-pane>

          <!-- Tab 3: Risks -->
          <el-tab-pane label="风险管理" name="risks">
            <div class="kpi-row">
              <el-statistic title="总风险" :value="riskStats.total" />
              <el-statistic title="待处理" :value="riskStats.open" />
              <el-statistic title="A级风险" :value="riskStats.a_level" />
            </div>
            <div class="toolbar">
              <el-button type="warning" size="small" @click="showRiskDialog = true">新建风险</el-button>
            </div>
            <el-table :data="risks" stripe border size="small" style="width: 100%">
              <el-table-column prop="title" label="风险描述" min-width="150" show-overflow-tooltip />
              <el-table-column label="等级" width="70">
                <template #default="{ row }"><el-tag :type="riskLevelTag(row.risk_level)" size="small">{{ row.risk_level }}级</el-tag></template>
              </el-table-column>
              <el-table-column prop="risk_source" label="来源" width="80" />
              <el-table-column prop="probability" label="概率" width="70" />
              <el-table-column prop="impact" label="影响" width="70" />
              <el-table-column label="状态" width="90">
                <template #default="{ row }"><el-tag :type="riskStatusTag(row.status)" size="small">{{ riskStatusLabel(row.status) }}</el-tag></template>
              </el-table-column>
              <el-table-column label="操作" width="180" fixed="right">
                <template #default="{ row }">
                  <el-button v-if="row.status !== 'resolved'" text size="small" type="success" @click="updateRisk(row, 'resolved')">标记已解决</el-button>
                  <el-button v-if="row.status !== 'monitoring'" text size="small" type="warning" @click="updateRisk(row, 'monitoring')">转为监控</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- Tab 4: Gate Details -->
          <el-tab-pane label="Gate详情" name="gates-detail">
            <el-table :data="gates" stripe border size="small" style="width: 100%">
              <el-table-column prop="gate_code" label="编号" width="70" />
              <el-table-column prop="gate_name" label="名称" min-width="120" />
              <el-table-column prop="decision_level" label="决策层" width="90" />
              <el-table-column label="状态" width="90">
                <template #default="{ row }"><el-tag :type="gateTag(row.status)" size="small">{{ gateLabel(row.status) }}</el-tag></template>
              </el-table-column>
              <el-table-column prop="planned_date" label="计划日期" width="100" />
              <el-table-column prop="actual_date" label="实际日期" width="100" />
              <el-table-column label="操作" width="150" fixed="right">
                <template #default="{ row }">
                  <el-select v-model="row._is" size="small" placeholder="更新状态" style="width: 120px" @change="(v: string) => updateGate(row, v)">
                    <el-option label="通过 passed" value="passed" /><el-option label="失败 failed" value="failed" />
                    <el-option label="跳过 skipped" value="skipped" /><el-option label="待定 pending" value="pending" />
                  </el-select>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </template>

    <!-- Gate Update Dialog -->
    <el-dialog v-model="showGateDialog" :title="'更新 ' + (gateForm?.gate_code || '')" width="380" destroy-on-close>
      <el-form label-width="70" size="small">
        <el-form-item label="状态"><el-select v-model="gateFormStatus"><el-option label="通过 passed" value="passed" /><el-option label="失败 failed" value="failed" /><el-option label="跳过 skipped" value="skipped" /><el-option label="待定 pending" value="pending" /></el-select></el-form-item>
        <el-form-item label="实际日期"><el-date-picker v-model="gateFormDate" type="date" placeholder="选择日期" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGateDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmGateUpdate">确认更新</el-button>
      </template>
    </el-dialog>

    <!-- Task Create Dialog -->
    <el-dialog v-model="showTaskDialog" title="新建任务" width="480" destroy-on-close>
      <el-form :model="taskForm" label-width="80" size="small">
        <el-form-item label="标题"><el-input v-model="taskForm.title" placeholder="任务标题" /></el-form-item>
        <el-form-item label="负责人"><el-input v-model="taskForm.assignee" placeholder="负责人姓名" /></el-form-item>
        <el-form-item label="优先级"><el-select v-model="taskForm.priority"><el-option label="低 low" value="low" /><el-option label="中 medium" value="medium" /><el-option label="高 high" value="high" /><el-option label="紧急 urgent" value="urgent" /></el-select></el-form-item>
        <el-form-item label="截止日期"><el-date-picker v-model="taskForm.due_date" type="date" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="taskForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTaskDialog = false">取消</el-button>
        <el-button type="primary" @click="saveTask">保存</el-button>
      </template>
    </el-dialog>

    <!-- Milestone Create Dialog -->
    <el-dialog v-model="showMsDialog" title="新建里程碑" width="380" destroy-on-close>
      <el-form :model="msForm" label-width="80" size="small">
        <el-form-item label="名称"><el-input v-model="msForm.name" placeholder="里程碑名称" /></el-form-item>
        <el-form-item label="计划日期"><el-date-picker v-model="msForm.planned_date" type="date" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMsDialog = false">取消</el-button>
        <el-button type="primary" @click="saveMs">保存</el-button>
      </template>
    </el-dialog>

    <!-- Risk Create Dialog -->
    <el-dialog v-model="showRiskDialog" title="新建风险" width="480" destroy-on-close>
      <el-form :model="riskForm" label-width="80" size="small">
        <el-form-item label="标题"><el-input v-model="riskForm.title" placeholder="风险描述" /></el-form-item>
        <el-form-item label="等级"><el-select v-model="riskForm.risk_level"><el-option label="A级 (阻塞)" value="A" /><el-option label="B级 (影响)" value="B" /><el-option label="C级 (轻微)" value="C" /></el-select></el-form-item>
        <el-form-item label="来源"><el-select v-model="riskForm.risk_source"><el-option v-for="s in ['模具', '物料', '认证', '人员', '外部']" :key="s" :label="s" :value="s" /></el-select></el-form-item>
        <el-form-item label="概率"><el-select v-model="riskForm.probability"><el-option label="低" value="low" /><el-option label="中" value="medium" /><el-option label="高" value="high" /></el-select></el-form-item>
        <el-form-item label="影响"><el-select v-model="riskForm.impact"><el-option label="低" value="low" /><el-option label="中" value="medium" /><el-option label="高" value="high" /></el-select></el-form-item>
        <el-form-item label="缓解措施"><el-input v-model="riskForm.mitigation" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRiskDialog = false">取消</el-button>
        <el-button type="primary" @click="saveRisk">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheckFilled, WarningFilled, CircleCloseFilled, Clock, Monitor, Check, Warning, MoreFilled, View } from '@element-plus/icons-vue'
import api from '../../api'
import TaskKanbanTab from './TaskKanbanTab.vue'

const route = useRoute()
const router = useRouter()
const pid = computed(() => Number(route.params.id))

const loading = ref(true)
const activeTab = ref('tasks')
const project = ref<any>(null)
const dashboard = ref<any>(null)
const gates = ref<any[]>([])
const tasks = ref<any[]>([])
const milestones = ref<any[]>([])
const risks = ref<any[]>([])
const taskStats = ref({ total: 0, todo: 0, in_progress: 0, done: 0, blocked: 0 })
const msStats = ref({ total: 0, achieved: 0, delayed: 0 })
const riskStats = ref({ total: 0, open: 0, a_level: 0 })

const showGateDialog = ref(false)
const showTaskDialog = ref(false)
const showMsDialog = ref(false)
const showRiskDialog = ref(false)

const gateForm = ref<any>(null)
const gateFormStatus = ref('')
const gateFormDate = ref<string | null>(null)
const taskForm = ref({ title: '', assignee: '', priority: 'medium', due_date: null, description: '' })
const msForm = ref({ name: '', planned_date: null })
const riskForm = ref({ title: '', risk_level: 'B', risk_source: '', probability: 'medium', impact: 'medium', mitigation: '' })

// ── Display helpers ──
const healthColor = computed(() => {
  const h: string = dashboard.value?.health || 'on_track'
  return ({ on_track: '#67c23a', at_risk: '#e6a23c', overdue: '#f56c6c' } as Record<string, string>)[h] || '#909399'
})
const healthLabel = computed(() => {
  const h: string = dashboard.value?.health || 'on_track'
  return ({ on_track: '正常', at_risk: '有风险', overdue: '已超期' } as Record<string, string>)[h] || '未知'
})
function classTag(c: string | undefined): string { return ({ T: 'danger', A: 'warning', B: 'success', C: 'info' })[c || ''] || 'info' }
function statusTag(s: string | undefined): string { return ({ planning: 'info', running: 'primary', completed: 'success', paused: 'warning' })[s || ''] || 'info' }
function statusLabel(s: string | undefined): string { return ({ planning: '规划中', running: '进行中', completed: '已完成', paused: '已暂停' })[s || ''] || s || '未知' }
function priorityTag(p: string): string { return ({ low: 'info', medium: '', high: 'warning', urgent: 'danger' })[p] || 'info' }
function taskStatusTag(s: string): string { return ({ todo: 'info', in_progress: 'primary', done: 'success', blocked: 'danger' })[s] || 'info' }
function taskStatusLabel(s: string): string { return ({ todo: '待办', in_progress: '进行中', done: '已完成', blocked: '阻塞' })[s] || s }
function msTag(s: string): string { return ({ pending: 'info', achieved: 'success', delayed: 'danger' })[s] || 'info' }
function msLabel(s: string): string { return ({ pending: '待定', achieved: '已达成', delayed: '已延期' })[s] || s }
function riskLevelTag(r: string): string { return ({ A: 'danger', B: 'warning', C: 'info' })[r] || 'info' }
function riskStatusTag(s: string): string { return ({ open: 'danger', monitoring: 'warning', resolved: 'success' })[s] || 'info' }
function riskStatusLabel(s: string): string { return ({ open: '待处理', monitoring: '监控中', resolved: '已解决' })[s] || s }
function gateTag(s: string | null | undefined): string { return ({ pending: 'info', passed: 'success', failed: 'danger', skipped: 'warning' })[s || 'pending'] || 'info' }
function gateLabel(s: string | null | undefined): string { return ({ pending: '待定', passed: '通过', failed: '失败', skipped: '跳过' })[s || 'pending'] || s || '待定' }

// ── Data fetching ──
async function fetchAll() {
  loading.value = true
  const id = pid.value
  if (!id) { ElMessage.error('项目ID无效'); router.push('/projects'); return }
  try {
    const [pRes, dRes, gRes, tRes, mRes, rRes] = await Promise.all([
      api.get(`/projects/${id}`),
      api.get(`/projects/${id}/dashboard`).catch(() => ({ data: null })),
      api.get(`/projects/${id}/gates`).catch(() => ({ data: [] })),
      api.get(`/projects/${id}/tasks`).catch(() => ({ data: [] })),
      api.get(`/projects/${id}/milestones`).catch(() => ({ data: [] })),
      api.get(`/projects/${id}/risks`).catch(() => ({ data: [] })),
    ])
    project.value = pRes.data
    if (dRes.data) {
      dashboard.value = dRes.data
      taskStats.value = dRes.data.task_stats || taskStats.value
      msStats.value = dRes.data.milestone_stats || msStats.value
      riskStats.value = dRes.data.risk_stats || riskStats.value
    }
    gates.value = (gRes.data || []).map((g: any) => ({ ...g, _is: '' }))
    tasks.value = (tRes.data || []).map((t: any) => ({ ...t, _is: '' }))
    milestones.value = mRes.data || []
    risks.value = rRes.data || []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载项目详情失败')
    router.push('/projects')
  } finally { loading.value = false }
}

// ── Gate ──
function openGateDialog(g: any) { gateForm.value = g; gateFormStatus.value = g.status || 'pending'; gateFormDate.value = g.actual_date || null; showGateDialog.value = true }
async function confirmGateUpdate() {
  if (!gateForm.value) return
  try { await api.patch(`/projects/${pid.value}/gates/${gateForm.value.gate_code}`, null, { params: { status: gateFormStatus.value, actual_date: gateFormDate.value || undefined } }); ElMessage.success('Gate已更新'); showGateDialog.value = false; await fetchAll() }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '更新Gate失败') }
}
async function updateGate(g: any, s: string) {
  if (!s) return
  try { await api.patch(`/projects/${pid.value}/gates/${g.gate_code}`, null, { params: { status: s } }); ElMessage.success('Gate已更新'); await fetchAll() }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '更新Gate失败'); g._is = '' }
}

// ── Task ──
async function saveTask() {
  if (!taskForm.value.title) { ElMessage.warning('请输入任务标题'); return }
  try { await api.post(`/projects/${pid.value}/tasks`, taskForm.value); ElMessage.success('任务创建成功'); showTaskDialog.value = false; taskForm.value = { title: '', assignee: '', priority: 'medium', due_date: null, description: '' }; await fetchAll() }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '创建任务失败') }
}
async function updateTask(t: any, s: string) {
  try { await api.patch(`/projects/${pid.value}/tasks/${t.id}`, null, { params: { status: s } }); ElMessage.success('任务状态已更新'); await fetchAll() }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '更新任务失败'); t._is = '' }
}
async function updateTaskById(taskId: number, status: string) {
  try { await api.patch(`/projects/${pid.value}/tasks/${taskId}`, null, { params: { status } }); await fetchAll() }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '更新任务失败') }
}

// ── Milestone ──
async function saveMs() {
  if (!msForm.value.name) { ElMessage.warning('请输入里程碑名称'); return }
  try { await api.post(`/projects/${pid.value}/milestones`, msForm.value); ElMessage.success('里程碑创建成功'); showMsDialog.value = false; msForm.value = { name: '', planned_date: null }; await fetchAll() }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '创建里程碑失败') }
}
async function updateMs(m: any, s: string) {
  try { await api.patch(`/projects/${pid.value}/milestones/${m.id}`, null, { params: { status: s } }); ElMessage.success('里程碑已更新'); await fetchAll() }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '更新里程碑失败') }
}

// ── Risk ──
async function saveRisk() {
  if (!riskForm.value.title) { ElMessage.warning('请输入风险标题'); return }
  try { await api.post(`/projects/${pid.value}/risks`, riskForm.value); ElMessage.success('风险记录成功'); showRiskDialog.value = false; riskForm.value = { title: '', risk_level: 'B', risk_source: '', probability: 'medium', impact: 'medium', mitigation: '' }; await fetchAll() }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '创建风险失败') }
}
async function updateRisk(r: any, s: string) {
  try { await api.patch(`/projects/${pid.value}/risks/${r.id}`, null, { params: { status: s } }); ElMessage.success('风险已更新'); await fetchAll() }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '更新风险失败') }
}

onMounted(fetchAll)
</script>

<style scoped>
.project-detail-page { padding: 16px; }
.loading-container { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 400px; }
.top-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; font-size: 14px; }
.breadcrumb-current { color: #303133; font-weight: 600; }
.section-card { margin-bottom: 16px; }
.section-title { font-weight: 600; }
.header-content { display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; flex-wrap: wrap; }
.header-left { flex: 1; min-width: 280px; }
.project-title { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.project-code-name { font-size: 20px; font-weight: 700; color: #303133; }
.project-meta { display: flex; gap: 16px; color: #909399; font-size: 13px; }
.header-right { display: flex; gap: 12px; flex-wrap: wrap; }
.health-card { min-width: 120px; cursor: default; }
.health-card :deep(.el-card__body) { display: flex; align-items: center; gap: 8px; padding: 12px 16px; }
.health-text { display: flex; flex-direction: column; gap: 2px; }
.health-label { font-size: 11px; color: #909399; }
.health-value { font-size: 14px; font-weight: 600; }
.gate-stepper { display: flex; align-items: center; justify-content: center; padding: 16px 0; flex-wrap: wrap; }
.gate-step { display: flex; flex-direction: column; align-items: center; gap: 6px; cursor: pointer; transition: transform 0.15s; }
.gate-step:hover { transform: scale(1.08); }
.gate-circle { width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 3px solid #dcdfe6; background: #fff; transition: all 0.2s; }
.gate-circle.gc-passed { border-color: #67c23a; background: #f0f9eb; }
.gate-circle.gc-failed { border-color: #f56c6c; background: #fef0f0; }
.gate-circle.gc-skipped { border-color: #e6a23c; background: #fdf6ec; }
.gate-circle.gc-pending { border-color: #dcdfe6; background: #f5f7fa; }
.gate-code { font-size: 13px; font-weight: 700; color: #303133; }
.gate-label { font-size: 11px; color: #606266; max-width: 60px; text-align: center; line-height: 1.2; }
.gate-connector { width: 36px; height: 3px; margin: 0 4px 22px; border-radius: 2px; flex-shrink: 0; }
.conn-passed { background: #67c23a; }
.conn-pending { background: #dcdfe6; }
.kpi-row { display: flex; gap: 24px; margin-bottom: 16px; flex-wrap: wrap; }
.kpi-row :deep(.el-statistic) { text-align: center; }
.kpi-row :deep(.el-statistic__head) { font-size: 12px; color: #909399; }
.kpi-row :deep(.el-statistic__content) { font-size: 22px; font-weight: 700; color: #303133; }
.toolbar { margin-bottom: 12px; }
.ms-list { display: flex; flex-direction: column; gap: 8px; }
.ms-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #fafafa; border-radius: 6px; border: 1px solid #ebeef5; transition: background 0.15s; }
.ms-item:hover { background: #f0f5ff; }
.ms-badge { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 16px; }
.msb-achieved { background: #f0f9eb; color: #67c23a; }
.msb-delayed { background: #fef0f0; color: #f56c6c; }
.msb-pending { background: #f5f7fa; color: #909399; }
.ms-body { flex: 1; min-width: 0; }
.ms-name { font-weight: 600; font-size: 14px; color: #303133; }
.ms-dates { font-size: 12px; color: #909399; margin-top: 2px; display: flex; gap: 12px; }
.ms-status-tag { flex-shrink: 0; }
.ms-actions { flex-shrink: 0; display: flex; gap: 4px; }
</style>
