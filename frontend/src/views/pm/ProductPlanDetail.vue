<template>
  <div class="plan-detail">
    <div class="detail-header">
      <el-button text @click="$router.push('/product-plans')">← 返回策划列表</el-button>
      <h2>{{ plan?.name || '加载中...' }}</h2>
      <el-tag v-if="plan" :type="stageTagType(plan.status)" size="small">{{ stageLabel(plan.status) }}</el-tag>
    </div>

    <!-- 进度条 -->
    <el-steps v-if="plan" :active="currentStepIndex" align-center finish-status="success" size="small" style="margin-bottom:20px">
      <el-step v-for="s in stages" :key="s.key" :title="s.label" />
    </el-steps>

    <!-- Tab -->
    <el-tabs v-model="activeTab" type="border-card" tab-position="left" v-if="plan">
      <!-- Tab 1: 竞品对标 -->
      <el-tab-pane label="🏷️ 竞品对标" name="competitor">
        <div v-if="plan.competitor_id" class="tab-section">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="关联竞品ID">{{ plan.competitor_id }}</el-descriptions-item>
          </el-descriptions>
        </div>
        <el-empty v-else description="暂未关联竞品" :image-size="50" />
      </el-tab-pane>

      <!-- Tab 2: 产品定义 -->
      <el-tab-pane label="📋 产品定义" name="definition">
        <el-form :model="editForm" label-width="100" size="small">
          <el-form-item label="策划名称">
            <el-input v-model="editForm.name" />
          </el-form-item>
          <el-form-item label="产品系列">
            <el-input v-model="editForm.series" />
          </el-form-item>
          <el-form-item label="目标市场">
            <el-input v-model="editForm.market" />
          </el-form-item>
          <el-form-item label="竞品关联">
            <el-input-number v-model="editForm.competitor_id" :min="0" style="width:200px" placeholder="竞品ID" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" size="small" @click="savePlan" :loading="saving">保存</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- Tab 3: 成本目标 -->
      <el-tab-pane label="💰 成本目标" name="costing">
        <div class="tab-toolbar">
          <el-button size="small" type="primary" @click="showCostDialog = true">+ 添加成本</el-button>
        </div>
        <el-table :data="costs" stripe border size="small" empty-text="暂无成本数据">
          <el-table-column prop="item_name" label="成本项" min-width="120" />
          <el-table-column prop="cost_type" label="类型" width="80">
            <template #default="{ row }">
              <el-tag size="small">{{ row.cost_type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="target_value" label="目标值" width="100" />
          <el-table-column prop="actual_value" label="实际值" width="100" />
          <el-table-column prop="currency" label="币种" width="70" />
          <el-table-column prop="remark" label="备注" />
          <el-table-column label="操作" width="60">
            <template #default="{ row }">
              <el-button link size="small" type="danger" @click="deleteCost(row)">删</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Tab 4: 技术输入 -->
      <el-tab-pane label="⚙️ 技术输入" name="tech">
        <el-input v-model="editForm.performance_target" type="textarea" :rows="8" placeholder='技术指标JSON，如 [{"param":"制冷量","target":"3500W"}]' />
        <div style="margin-top:12px">
          <el-button type="primary" size="small" @click="savePlan" :loading="saving">保存</el-button>
        </div>
      </el-tab-pane>

      <!-- Tab 5: 项目关联 -->
      <el-tab-pane label="🔗 项目关联" name="project">
        <div v-if="plan.project_id" class="tab-section">
          <el-alert title="已生成关联项目" type="success" show-icon :closable="false" style="margin-bottom:12px" />
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="项目ID">{{ plan.project_id }}</el-descriptions-item>
            <el-descriptions-item label="状态">已创建</el-descriptions-item>
          </el-descriptions>
        </div>
        <el-empty v-else description="策划尚未批准，未生成项目" :image-size="50" />
      </el-tab-pane>

      <!-- Tab 6: BOM规划 -->
      <el-tab-pane label="📦 BOM规划" name="bom">
        <div class="bom-types">
          <el-card v-for="bt in bomTypes" :key="bt.key" shadow="never" class="bom-type-card" :class="'bom-' + bt.key">
            <div class="bom-type-icon">{{ bt.icon }}</div>
            <div class="bom-type-name">{{ bt.label }}</div>
            <div class="bom-type-desc">{{ bt.desc }}</div>
            <el-tag size="small" :type="bt.status === 'active' ? 'warning' : 'info'" effect="plain">
              {{ bt.status === 'active' ? '待生成' : '未开始' }}
            </el-tag>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- Tab 7: 项目概述 -->
      <el-tab-pane label="📄 项目概述" name="initiation">
        <el-form :model="initiationForm" label-width="140" size="small">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="立项背景">
                <el-input v-model="initiationForm.background" type="textarea" :rows="3" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="产品类型">
                <el-input v-model="initiationForm.type" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="目标市场">
                <el-input v-model="initiationForm.market" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="制冷剂">
                <el-input v-model="initiationForm.refrigerant" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="容量">
                <el-input v-model="initiationForm.capacity" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="电压">
                <el-input v-model="initiationForm.voltage" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="系列">
                <el-input v-model="initiationForm.series" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="能效">
                <el-input v-model="initiationForm.energy" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="开发类别">
                <el-input v-model="initiationForm.dev_category" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="产地">
                <el-input v-model="initiationForm.origin" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="开发周期(月)">
                <el-input-number v-model="initiationForm.duration" :min="0" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="IP等级">
                <el-input v-model="initiationForm.ip" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="项目目标">
            <el-input v-model="initiationForm.goals" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="交付物">
            <el-input v-model="initiationForm.deliverables" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="样品数量">
            <el-input-number v-model="initiationForm.sample_qty" :min="0" style="width:200px" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" size="small" @click="saveInitiation" :loading="savingInitiation">保存</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- Tab 8: 市场与客户需求 -->
      <el-tab-pane label="🎯 市场与客户需求" name="market">
        <el-form :model="marketForm" label-width="180" size="small">
          <el-form-item label="主要容量">
            <el-input v-model="marketForm.main_capacity" />
          </el-form-item>
          <el-form-item label="能效要求">
            <el-input v-model="marketForm.energy_efficiency" />
          </el-form-item>
          <el-form-item label="认证要求">
            <el-input v-model="marketForm.cert_requirements" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="目标价格">
            <el-input-number v-model="marketForm.target_price" :min="0" :precision="2" style="width:200px" />
          </el-form-item>
          <el-form-item label="客户需求">
            <el-input v-model="marketForm.customer_requirements" type="textarea" :rows="4" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" size="small" @click="saveMarket" :loading="savingMarket">保存</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- Tab 9: 技术要求 -->
      <el-tab-pane label="⚡ 技术要求" name="techSpec">
        <el-form :model="techSpecForm" label-width="180" size="small">
          <el-form-item label="核心性能指标">
            <el-input v-model="techSpecForm.core_performance" type="textarea" :rows="4" placeholder="制冷量、制热量、COP等" />
          </el-form-item>
          <el-form-item label="安全合规要求">
            <el-input v-model="techSpecForm.safety_compliance" type="textarea" :rows="4" placeholder="CE、UL、CCC等" />
          </el-form-item>
          <el-form-item label="可选配置">
            <el-input v-model="techSpecForm.optional_config" type="textarea" :rows="4" placeholder="WiFi模块、特殊面板等" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" size="small" @click="saveTechSpec" :loading="savingTechSpec">保存</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- Tab 10: 成本核算 -->
      <el-tab-pane label="💰 成本核算" name="costingNew">
        <div class="tab-section">
          <el-alert title="成本核算" type="info" show-icon :closable="false" style="margin-bottom:12px">
            <template #default>
              <p>当前产品已有 {{ costs.length }} 条成本记录。</p>
            </template>
          </el-alert>
          <el-table :data="costs" stripe border size="small" empty-text="暂无成本数据">
            <el-table-column prop="item_name" label="成本项" min-width="120" />
            <el-table-column prop="cost_type" label="类型" width="80">
              <template #default="{ row }">
                <el-tag size="small">{{ row.cost_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="target_value" label="目标值" width="100" />
            <el-table-column prop="actual_value" label="实际值" width="100" />
            <el-table-column prop="currency" label="币种" width="70" />
            <el-table-column prop="remark" label="备注" />
          </el-table>
          <div style="margin-top:12px">
            <el-button size="small" @click="$router.push('/cost-accounting')">前往成本核算 →</el-button>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 11: 团队 -->
      <el-tab-pane label="👥 团队" name="team">
        <div class="tab-toolbar">
          <el-button size="small" type="primary" @click="showTeamDialog = true; teamDialogMode = 'add'">+ 添加成员</el-button>
        </div>
        <el-table :data="teamMembers" stripe border size="small" empty-text="暂无团队成员">
          <el-table-column prop="name" label="姓名" min-width="100" />
          <el-table-column prop="role" label="角色" width="120" />
          <el-table-column prop="department" label="部门" width="120" />
          <el-table-column prop="email" label="邮箱" width="180" />
          <el-table-column prop="phone" label="电话" width="130" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link size="small" type="primary" @click="editTeamMember(row)">编辑</el-button>
              <el-button link size="small" type="danger" @click="deleteTeamMember(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加成本弹窗 -->
    <el-dialog v-model="showCostDialog" title="添加成本" width="450px" :close-on-click-modal="false">
      <el-form :model="costForm" label-width="100" size="small">
        <el-form-item label="成本项">
          <el-input v-model="costForm.item_name" placeholder="如: 模具成本" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="costForm.cost_type">
            <el-option label="目标成本" value="target" />
            <el-option label="实际成本" value="actual" />
            <el-option label="估算" value="estimate" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标值">
          <el-input-number v-model="costForm.target_value" :min="0" :precision="2" style="width:200px" />
        </el-form-item>
        <el-form-item label="实际值">
          <el-input-number v-model="costForm.actual_value" :min="0" :precision="2" style="width:200px" />
        </el-form-item>
        <el-form-item label="币种">
          <el-input v-model="costForm.currency" placeholder="CNY" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="costForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCostDialog = false">取消</el-button>
        <el-button type="primary" @click="addCost" :loading="addingCost">添加</el-button>
      </template>
    </el-dialog>

    <!-- 团队弹窗 -->
    <el-dialog v-model="showTeamDialog" :title="teamDialogMode === 'add' ? '添加成员' : '编辑成员'" width="450px" :close-on-click-modal="false">
      <el-form :model="teamForm" label-width="100" size="small">
        <el-form-item label="姓名">
          <el-input v-model="teamForm.name" placeholder="姓名" />
        </el-form-item>
        <el-form-item label="角色">
          <el-input v-model="teamForm.role" placeholder="如: 项目经理、开发工程师" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="teamForm.department" placeholder="部门" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="teamForm.email" placeholder="email@company.com" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="teamForm.phone" placeholder="手机号" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTeamDialog = false">取消</el-button>
        <el-button type="primary" @click="saveTeamMember" :loading="savingTeam">{{ teamDialogMode === 'add' ? '添加' : '保存' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'
import * as planAPI from '../../api/productPlan'

const route = useRoute()
const planId = route.params.id as string

// ── Data ──
const plan = ref<any>(null)
const costs = ref<any[]>([])
const loading = ref(true)
const saving = ref(false)
const activeTab = ref('competitor')
const showCostDialog = ref(false)
const addingCost = ref(false)

const editForm = ref({ name: '', series: '', market: '', competitor_id: null as number | null, performance_target: '' })
const costForm = ref({ item_name: '', cost_type: 'target', target_value: 0, actual_value: 0, currency: 'CNY', remark: '' })

// ── 阶段映射 ──
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

const stages = computed(() => STAGE_ORDER.map((key, i) => ({
  key, label: STAGE_LABELS[key] || key,
  status: !plan.value ? 'pending' :
    STAGE_ORDER.indexOf(plan.value.status) > i ? 'success' :
    STAGE_ORDER.indexOf(plan.value.status) === i ? 'process' : 'wait',
})))
const currentStepIndex = computed(() => {
  if (!plan.value) return 0
  return STAGE_ORDER.indexOf(plan.value.status)
})

// ── BOM类型 ──
const bomTypes = [
  { key: 'concept_bom', icon: '📐', label: '概念BOM', desc: '产品初期架构BOM', status: 'inactive' },
  { key: 'design_bom', icon: '✏️', label: '设计BOM', desc: '详细设计BOM', status: 'inactive' },
  { key: 'pilot_bom', icon: '🧪', label: '试产BOM', desc: '试产验证BOM', status: 'inactive' },
  { key: 'mass_bom', icon: '🏭', label: '量产BOM', desc: '量产正式BOM', status: 'inactive' },
]

// ── 项目概述 (Initiation) ──
const initiationForm = reactive({
  background: '', type: '', market: '', refrigerant: '', capacity: '', voltage: '',
  series: '', energy: '', dev_category: '', origin: '', duration: 0, ip: '',
  goals: '', deliverables: '', sample_qty: 0,
})
const savingInitiation = ref(false)

async function fetchInitiation() {
  try {
    const res = await planAPI.getPlanInitiation(planId)
    if (res.data) Object.assign(initiationForm, res.data)
  } catch { /* 未创建时忽略404 */ }
}

async function saveInitiation() {
  savingInitiation.value = true
  try {
    await planAPI.upsertPlanInitiation(planId, initiationForm)
    ElMessage.success('项目概述保存成功')
  } catch { /* handled */ }
  finally { savingInitiation.value = false }
}

// ── 市场与客户需求 (Market) ──
const marketForm = reactive({
  main_capacity: '', energy_efficiency: '', cert_requirements: '', target_price: 0, customer_requirements: '',
})
const savingMarket = ref(false)

async function fetchMarket() {
  try {
    const res = await planAPI.getPlanMarket(planId)
    if (res.data) Object.assign(marketForm, res.data)
  } catch { /* 404 ignored */ }
}

async function saveMarket() {
  savingMarket.value = true
  try {
    await planAPI.upsertPlanMarket(planId, marketForm)
    ElMessage.success('市场与客户需求保存成功')
  } catch { /* handled */ }
  finally { savingMarket.value = false }
}

// ── 技术要求 (TechSpec) ──
const techSpecForm = reactive({
  core_performance: '', safety_compliance: '', optional_config: '',
})
const savingTechSpec = ref(false)

async function fetchTechSpec() {
  try {
    const res = await planAPI.getPlanTechSpec(planId)
    if (res.data) Object.assign(techSpecForm, res.data)
  } catch { /* 404 ignored */ }
}

async function saveTechSpec() {
  savingTechSpec.value = true
  try {
    await planAPI.upsertPlanTechSpec(planId, techSpecForm)
    ElMessage.success('技术要求保存成功')
  } catch { /* handled */ }
  finally { savingTechSpec.value = false }
}

// ── 团队 (Team) ──
const teamMembers = ref<any[]>([])
const showTeamDialog = ref(false)
const teamDialogMode = ref<'add' | 'edit'>('add')
const teamForm = reactive({ name: '', role: '', department: '', email: '', phone: '' })
const editingTeamId = ref<number | null>(null)
const savingTeam = ref(false)

async function fetchTeam() {
  try {
    const res = await planAPI.listPlanTeam(planId)
    teamMembers.value = res.data || []
  } catch { teamMembers.value = [] }
}

function editTeamMember(row: any) {
  teamDialogMode.value = 'edit'
  editingTeamId.value = row.id
  Object.assign(teamForm, { name: row.name, role: row.role, department: row.department, email: row.email, phone: row.phone })
  showTeamDialog.value = true
}

async function saveTeamMember() {
  savingTeam.value = true
  try {
    if (teamDialogMode.value === 'add') {
      await planAPI.addPlanTeamMember(planId, teamForm)
    } else if (editingTeamId.value !== null) {
      await planAPI.updatePlanTeamMember(planId, editingTeamId.value, teamForm)
    }
    ElMessage.success(teamDialogMode.value === 'add' ? '成员添加成功' : '成员更新成功')
    showTeamDialog.value = false
    resetTeamForm()
    await fetchTeam()
  } catch { /* handled */ }
  finally { savingTeam.value = false }
}

async function deleteTeamMember(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除团队成员「${row.name}」?`, '确认', { type: 'warning' })
    await planAPI.deletePlanTeamMember(planId, row.id)
    ElMessage.success('成员已删除')
    await fetchTeam()
  } catch { /* cancel or error */ }
}

function resetTeamForm() {
  teamForm.name = ''
  teamForm.role = ''
  teamForm.department = ''
  teamForm.email = ''
  teamForm.phone = ''
}

// — Team members loaded from onMounted via loadPlanTeam()

// ── 主API ──
async function fetchPlan() {
  loading.value = true
  try {
    const res = await api.get(`/product-plans/${planId}`)
    plan.value = res.data
    costs.value = res.data.costs || []
    editForm.value = {
      name: res.data.name || '',
      series: res.data.series || '',
      market: res.data.market || '',
      competitor_id: res.data.competitor_id ?? null,
      performance_target: res.data.performance_target || '',
    }
  } catch { /* handled */ }
  finally { loading.value = false }
}

async function savePlan() {
  saving.value = true
  try {
    await api.patch(`/product-plans/${planId}`, editForm.value)
    ElMessage.success('保存成功')
    await fetchPlan()
  } catch { /* handled */ }
  finally { saving.value = false }
}

async function addCost() {
  addingCost.value = true
  try {
    await api.post(`/product-plans/${planId}/costs`, costForm.value)
    ElMessage.success('成本添加成功')
    showCostDialog.value = false
    costForm.value = { item_name: '', cost_type: 'target', target_value: 0, actual_value: 0, currency: 'CNY', remark: '' }
    await fetchPlan()
  } catch { /* handled */ }
  finally { addingCost.value = false }
}

async function deleteCost(row: any) {
  try {
    await api.delete(`/product-plans/${planId}/costs/${row.id}`)
    ElMessage.success('已删除')
    await fetchPlan()
  } catch { /* handled */ }
}

onMounted(() => {
  fetchPlan()
  fetchInitiation()
  fetchMarket()
  fetchTechSpec()
  fetchTeam()
})
</script>

<style scoped>
.detail-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.detail-header h2 { margin: 0; font-size: 18px; flex: 1; }
.tab-section { padding: 8px 0; }
.tab-toolbar { margin-bottom: 12px; }

/* BOM 类型卡片网格 */
.bom-types { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.bom-type-card { text-align: center; padding: 16px 0; }
.bom-type-icon { font-size: 32px; margin-bottom: 8px; }
.bom-type-name { font-size: 14px; font-weight: 600; margin-bottom: 4px; }
.bom-type-desc { font-size: 12px; color: #909399; margin-bottom: 8px; }
</style>
