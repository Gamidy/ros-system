<template>
<div class="plan-detail">
<div class="detail-header">
<el-button text @click="$router.push('/product-plans')">← 返回策划列表</el-button>
<h2>{{ plan?.name || '加载中...' }}</h2>
<el-tag v-if="plan" :type="stageTagType(plan.status)" size="small">{{ stageLabel(plan.status) }}</el-tag>
</div>

<!-- PlanStatusGuide: 5子表完成度引导条 -->
<div v-if="plan" class="plan-status-guide">
<div v-for="(tab, i) in subTabs" :key="tab.key" class="guide-step" :class="{ active: activeTab === tab.key, done: tabStatus[tab.key] === 'done' }" @click="guideClick(tab.key, i)">
<div class="guide-step-num">{{ tabStatus[tab.key] === 'done' ? '✓' : i + 1 }}</div>
<div class="guide-step-label">{{ tab.label }}</div>
<el-tag size="small" :type="tabStatus[tab.key] === 'done' ? 'success' : tabStatus[tab.key] === 'progress' ? 'warning' : 'info'" effect="plain">{{ tabStatus[tab.key] === 'done' ? '已完成' : tabStatus[tab.key] === 'progress' ? '进行中' : '未开始' }}</el-tag>
</div>
</div>

<!-- ─── 桌面端: 5个子表 Tab ─── -->
<template v-if="!isMobile">
<el-tabs v-model="activeTab" type="border-card" tab-position="left" v-if="plan">
<!-- 项目概述 -->
<el-tab-pane name="initiation">
  <template #label>
    <span>项目概述 <el-tag size="small" type="primary" v-if="initiationVersion > 0">v{{initiationVersion}}</el-tag></span>
  </template>
<el-form :model="editForm" label-width="100" size="small" class="quick-edit">
<el-row :gutter="12">
<el-col :span="8"><el-form-item label="策划名称"><el-input v-model="editForm.name" /></el-form-item></el-col>
<el-col :span="8"><el-form-item label="产品系列"><el-input v-model="editForm.series" /></el-form-item></el-col>
<el-col :span="8"><el-form-item label="目标市场"><el-input v-model="editForm.market" /></el-form-item></el-col>
</el-row>
<el-row :gutter="12">
<el-col :span="8"><el-form-item label="竞品关联"><el-input-number v-model="editForm.competitor_id" :min="0" style="width:100%" /></el-form-item></el-col>
<el-col :span="4"><el-form-item><el-button type="primary" size="small" @click="saveQuickEdit" :loading="saving">保存</el-button></el-form-item></el-col>
</el-row>
</el-form>
<el-divider />
<el-form :model="initiationForm" label-width="140" size="small">
<el-row :gutter="16">
<el-col :span="12"><el-form-item label="立项背景"><el-input v-model="initiationForm.background" type="textarea" :rows="2" /></el-form-item></el-col>
<el-col :span="12"><el-form-item label="产品类型"><el-input v-model="initiationForm.type" /></el-form-item></el-col>
</el-row>
<el-row :gutter="16">
<el-col :span="6"><el-form-item label="制冷剂"><el-input v-model="initiationForm.refrigerant" /></el-form-item></el-col>
<el-col :span="6"><el-form-item label="容量"><el-input v-model="initiationForm.capacity" /></el-form-item></el-col>
<el-col :span="6"><el-form-item label="电压"><el-input v-model="initiationForm.voltage" /></el-form-item></el-col>
<el-col :span="6"><el-form-item label="能效"><el-input v-model="initiationForm.energy" /></el-form-item></el-col>
</el-row>
<el-row :gutter="16">
<el-col :span="6"><el-form-item label="开发类别"><el-input v-model="initiationForm.dev_category" /></el-form-item></el-col>
<el-col :span="6"><el-form-item label="产地"><el-input v-model="initiationForm.origin" /></el-form-item></el-col>
<el-col :span="6"><el-form-item label="开发周期(月)"><el-input-number v-model="initiationForm.duration" :min="0" style="width:100%" /></el-form-item></el-col>
<el-col :span="6"><el-form-item label="IP等级"><el-input v-model="initiationForm.ip" /></el-form-item></el-col>
</el-row>
<el-row :gutter="16">
<el-col :span="12"><el-form-item label="项目目标"><el-input v-model="initiationForm.goals" type="textarea" :rows="2" /></el-form-item></el-col>
<el-col :span="12"><el-form-item label="交付物"><el-input v-model="initiationForm.deliverables" type="textarea" :rows="2" /></el-form-item></el-col>
</el-row>
<el-form-item label="样品数量"><el-input-number v-model="initiationForm.sample_qty" :min="0" style="width:200px" /></el-form-item>
<el-form-item><el-button type="primary" size="small" @click="saveInitiation" :loading="savingInitiation">保存</el-button></el-form-item>
</el-form>
<el-divider>BOM规划</el-divider>
<div class="bom-types">
<div v-for="bt in bomTypes" :key="bt.key" class="bom-card">
<div class="bom-icon">{{ bt.icon }}</div>
<div class="bom-name">{{ bt.label }}</div>
<el-tag size="small" :type="bt.status === 'active' ? 'warning' : 'info'" effect="plain">{{ bt.status === 'active' ? '待生成' : '未开始' }}</el-tag>
</div>
</div>
</el-tab-pane>

<!-- 市场与客户 -->
<el-tab-pane name="market">
  <template #label>
    <span>市场与客户 <el-tag size="small" type="primary" v-if="marketVersion > 0">v{{marketVersion}}</el-tag></span>
  </template>
<el-form :model="marketForm" label-width="180" size="small">
<el-form-item label="主要容量"><el-input v-model="marketForm.main_capacity" /></el-form-item>
<el-form-item label="能效要求"><el-input v-model="marketForm.energy_efficiency" /></el-form-item>
<el-form-item label="认证要求"><el-input v-model="marketForm.cert_requirements" type="textarea" :rows="2" /></el-form-item>
<el-form-item label="目标价格"><el-input-number v-model="marketForm.target_price" :min="0" :precision="2" style="width:200px" /></el-form-item>
<el-form-item label="客户需求"><el-input v-model="marketForm.customer_requirements" type="textarea" :rows="3" /></el-form-item>
<el-form-item><el-button type="primary" size="small" @click="saveMarket" :loading="savingMarket">保存</el-button></el-form-item>
</el-form>
</el-tab-pane>

<!-- 技术要求 -->
<el-tab-pane name="techSpec">
  <template #label>
    <span>技术要求 <el-tag size="small" type="primary" v-if="techSpecVersion > 0">v{{techSpecVersion}}</el-tag></span>
  </template>
<el-form :model="techSpecForm" label-width="180" size="small">
<el-form-item label="核心性能指标"><el-input v-model="techSpecForm.core_performance" type="textarea" :rows="3" placeholder="制冷量、制热量、COP等" /></el-form-item>
<el-form-item label="安全合规要求"><el-input v-model="techSpecForm.safety_compliance" type="textarea" :rows="3" placeholder="CE、UL、CCC等" /></el-form-item>
<el-form-item label="可选配置"><el-input v-model="techSpecForm.optional_config" type="textarea" :rows="3" placeholder="WiFi模块、特殊面板等" /></el-form-item>
<el-form-item><el-button type="primary" size="small" @click="saveTechSpec" :loading="savingTechSpec">保存</el-button></el-form-item>
</el-form>
</el-tab-pane>

<!-- 成本核算 -->
<el-tab-pane label="成本核算" name="costingNew">
<div class="tab-toolbar"><el-button size="small" type="primary" @click="showCostDialog = true">+ 添加成本</el-button></div>
<el-table :data="costs" stripe border size="small" empty-text="暂无成本数据">
<el-table-column prop="item_name" label="成本项" min-width="120" />
<el-table-column prop="cost_type" label="类型" width="80"><template #default="{ row }"><el-tag size="small">{{ row.cost_type }}</el-tag></template></el-table-column>
<el-table-column prop="target_value" label="目标值" width="100" />
<el-table-column prop="actual_value" label="实际值" width="100" />
<el-table-column prop="currency" label="币种" width="70" />
<el-table-column prop="remark" label="备注" />
<el-table-column label="操作" width="60"><template #default="{ row }"><el-button link size="small" type="danger" @click="deleteCost(row)">删</el-button></template></el-table-column>
</el-table>
</el-tab-pane>

<!-- 团队 -->
<el-tab-pane name="team">
  <template #label>
    <span>团队 <el-tag size="small" type="primary" v-if="teamVersion > 0">v{{teamVersion}}</el-tag></span>
  </template>
<div class="tab-toolbar"><el-button size="small" type="primary" @click="showTeamDialog = true; teamDialogMode = 'add'">+ 添加成员</el-button></div>
<el-table :data="teamMembers" stripe border size="small" empty-text="暂无团队成员">
<el-table-column prop="name" label="姓名" min-width="100" />
<el-table-column prop="role" label="角色" width="120" />
<el-table-column prop="department" label="部门" width="120" />
<el-table-column prop="email" label="邮箱" width="180" />
<el-table-column prop="phone" label="电话" width="130" />
<el-table-column label="操作" width="120"><template #default="{ row }">
<el-button link size="small" type="primary" @click="editTeamMember(row)">编辑</el-button>
<el-button link size="small" type="danger" @click="deleteTeamMember(row)">删除</el-button>
</template></el-table-column>
</el-table>
</el-tab-pane>
</el-tabs>

<!-- 底部审批操作栏 -->
<div v-if="plan" class="approval-bar">
<div class="approval-info"><span class="approval-node">当前节点: {{ stageLabel(plan.status) }}</span><span class="approval-approver">审批人: {{ plan.approver || '待指定' }}</span></div>
<div class="approval-actions">
<el-button v-if="canAdvance" type="primary" size="small" @click="advancePlan">推进流程</el-button>
<el-button v-if="isApprovalStage" type="success" size="small" @click="approvePlan">通过</el-button>
<el-button v-if="isApprovalStage" type="danger" size="small" @click="rejectPlan">驳回</el-button>
<el-button v-if="canWithdraw" size="small" @click="withdrawPlan">撤回</el-button>
</div>
</div>
</template>

<!-- ─── 移动端: 5步分步表单 ─── -->
<template v-if="isMobile && plan">
<el-steps :active="mobileStep" finish-status="success" simple style="margin-bottom:12px;overflow-x:auto;">
<el-step v-for="(s, i) in mobileSteps" :key="i" :title="s.label" :status="stepStatus(s.key)" />
</el-steps>
<div class="mobile-step-form" style="padding-bottom:72px">
<!-- Step 0: 项目概述 -->
<div v-show="mobileStep === 0">
<h3 class="step-title">📄 项目概述</h3>
<el-form label-width="80" size="small">
<el-form-item label="策划名称"><el-input v-model="editForm.name" /></el-form-item>
<el-form-item label="产品系列"><el-input v-model="editForm.series" /></el-form-item>
<el-form-item label="目标市场"><el-input v-model="editForm.market" /></el-form-item>
<el-form-item label="竞品ID"><el-input-number v-model="editForm.competitor_id" :min="0" style="width:100%" /></el-form-item>
<el-divider />
<el-form-item label="立项背景"><el-input v-model="initiationForm.background" type="textarea" :rows="2" /></el-form-item>
<el-form-item label="产品类型"><el-input v-model="initiationForm.type" /></el-form-item>
<el-row :gutter="8"><el-col :span="12"><el-form-item label="制冷剂"><el-input v-model="initiationForm.refrigerant" /></el-form-item></el-col><el-col :span="12"><el-form-item label="容量"><el-input v-model="initiationForm.capacity" /></el-form-item></el-col></el-row>
<el-row :gutter="8"><el-col :span="12"><el-form-item label="电压"><el-input v-model="initiationForm.voltage" /></el-form-item></el-col><el-col :span="12"><el-form-item label="能效"><el-input v-model="initiationForm.energy" /></el-form-item></el-col></el-row>
<el-row :gutter="8"><el-col :span="12"><el-form-item label="开发类别"><el-input v-model="initiationForm.dev_category" /></el-form-item></el-col><el-col :span="12"><el-form-item label="产地"><el-input v-model="initiationForm.origin" /></el-form-item></el-col></el-row>
<el-row :gutter="8"><el-col :span="12"><el-form-item label="开发周期(月)"><el-input-number v-model="initiationForm.duration" :min="0" style="width:100%" /></el-form-item></el-col><el-col :span="12"><el-form-item label="IP等级"><el-input v-model="initiationForm.ip" /></el-form-item></el-col></el-row>
<el-form-item label="项目目标"><el-input v-model="initiationForm.goals" type="textarea" :rows="2" /></el-form-item>
<el-form-item label="交付物"><el-input v-model="initiationForm.deliverables" type="textarea" :rows="2" /></el-form-item>
<el-form-item label="样品数量"><el-input-number v-model="initiationForm.sample_qty" :min="0" style="width:100%" /></el-form-item>
</el-form>
</div>
<!-- Step 1: 市场与客户 -->
<div v-show="mobileStep === 1">
<h3 class="step-title">🎯 市场与客户</h3>
<el-form label-width="90" size="small">
<el-form-item label="主要容量"><el-input v-model="marketForm.main_capacity" /></el-form-item>
<el-form-item label="能效要求"><el-input v-model="marketForm.energy_efficiency" /></el-form-item>
<el-form-item label="认证要求"><el-input v-model="marketForm.cert_requirements" type="textarea" :rows="2" /></el-form-item>
<el-form-item label="目标价格"><el-input-number v-model="marketForm.target_price" :min="0" :precision="2" style="width:100%" /></el-form-item>
<el-form-item label="客户需求"><el-input v-model="marketForm.customer_requirements" type="textarea" :rows="3" /></el-form-item>
</el-form>
</div>
<!-- Step 2: 技术要求 -->
<div v-show="mobileStep === 2">
<h3 class="step-title">⚡ 技术要求</h3>
<el-form label-width="90" size="small">
<el-form-item label="核心性能指标"><el-input v-model="techSpecForm.core_performance" type="textarea" :rows="3" /></el-form-item>
<el-form-item label="安全合规要求"><el-input v-model="techSpecForm.safety_compliance" type="textarea" :rows="3" /></el-form-item>
<el-form-item label="可选配置"><el-input v-model="techSpecForm.optional_config" type="textarea" :rows="3" /></el-form-item>
</el-form>
</div>
<!-- Step 3: 成本核算 -->
<div v-show="mobileStep === 3">
<h3 class="step-title">💰 成本核算</h3>
<el-table :data="costs" stripe border size="small" empty-text="暂无数据" style="margin-bottom:12px">
<el-table-column prop="item_name" label="成本项" min-width="100" />
<el-table-column prop="target_value" label="目标" width="80" />
<el-table-column prop="actual_value" label="实际" width="80" />
</el-table>
<el-button size="small" type="primary" @click="showCostDialog = true">+ 添加</el-button>
</div>
<!-- Step 4: 团队 -->
<div v-show="mobileStep === 4">
<h3 class="step-title">👥 团队</h3>
<el-button size="small" type="primary" @click="showTeamDialog = true; teamDialogMode = 'add'" style="margin-bottom:12px">+ 添加成员</el-button>
<div v-if="teamMembers.length === 0" style="text-align:center;padding:24px 0;color:#909399">暂无团队成员</div>
<div v-for="m in teamMembers" :key="m.id" class="mobile-team-card">
<div class="team-card-row"><span class="team-card-name">{{ m.name }}</span><el-tag size="small">{{ m.role }}</el-tag></div>
<div class="team-card-detail">{{ m.department }} · {{ m.email }}</div>
<div class="team-card-actions"><el-button link size="small" type="primary" @click="editTeamMember(m)">编辑</el-button><el-button link size="small" type="danger" @click="deleteTeamMember(m)">删除</el-button></div>
</div>
</div>
</div>
<div class="mobile-step-footer">
<el-button v-if="mobileStep > 0" size="large" @click="prevStep" :disabled="savingAll">上一步</el-button>
<el-button v-if="mobileStep < mobileSteps.length - 1" type="primary" size="large" @click="nextStep">下一步</el-button>
<el-button v-if="mobileStep === mobileSteps.length - 1 && plan.status === 'project_init'" type="warning" size="large" @click="showApprovalDrawer = true" style="flex:1">提交审批</el-button>
<el-button v-else-if="mobileStep === mobileSteps.length - 1" type="primary" size="large" @click="saveAll" :loading="savingAll" style="flex:1">保存全部</el-button>
</div>
</template>

<!-- 成本弹窗 -->
<el-dialog v-model="showCostDialog" title="添加成本" width="450px" :close-on-click-modal="false">
<el-form :model="costForm" label-width="100" size="small">
<el-form-item label="成本项"><el-input v-model="costForm.item_name" /></el-form-item>
<el-form-item label="类型"><el-select v-model="costForm.cost_type"><el-option label="目标成本" value="target" /><el-option label="实际成本" value="actual" /><el-option label="估算" value="estimate" /></el-select></el-form-item>
<el-form-item label="目标值"><el-input-number v-model="costForm.target_value" :min="0" :precision="2" style="width:200px" /></el-form-item>
<el-form-item label="实际值"><el-input-number v-model="costForm.actual_value" :min="0" :precision="2" style="width:200px" /></el-form-item>
<el-form-item label="币种"><el-input v-model="costForm.currency" placeholder="CNY" /></el-form-item>
<el-form-item label="备注"><el-input v-model="costForm.remark" type="textarea" :rows="2" /></el-form-item>
</el-form>
<template #footer><el-button @click="showCostDialog = false">取消</el-button><el-button type="primary" @click="addCost" :loading="addingCost">添加</el-button></template>
</el-dialog>

<!-- 团队弹窗 -->
<el-dialog v-model="showTeamDialog" :title="teamDialogMode === 'add' ? '添加成员' : '编辑成员'" width="450px" :close-on-click-modal="false">
<el-form :model="teamForm" label-width="100" size="small">
<el-form-item label="姓名"><el-input v-model="teamForm.name" /></el-form-item>
<el-form-item label="角色"><el-input v-model="teamForm.role" /></el-form-item>
<el-form-item label="部门"><el-input v-model="teamForm.department" /></el-form-item>
<el-form-item label="邮箱"><el-input v-model="teamForm.email" /></el-form-item>
<el-form-item label="电话"><el-input v-model="teamForm.phone" /></el-form-item>
</el-form>
<template #footer><el-button @click="showTeamDialog = false">取消</el-button><el-button type="primary" @click="saveTeamMember" :loading="savingTeam">{{ teamDialogMode === 'add' ? '添加' : '保存' }}</el-button></template>
</el-dialog>

<!-- 移动端审批 Drawer -->
<el-drawer v-if="isMobile" v-model="showApprovalDrawer" direction="btt" size="100%" :close-on-click-modal="false" :with-header="false" class="approval-drawer-mobile">
<div class="drawer-body">
<div class="drawer-header"><h3>✅ 审批操作</h3><el-button text @click="showApprovalDrawer = false">关闭</el-button></div>
<div class="drawer-content">
<el-descriptions :column="1" border size="small" style="margin-bottom:16px">
<el-descriptions-item label="策划名称">{{ plan?.name }}</el-descriptions-item>
<el-descriptions-item label="当前阶段">{{ plan ? stageLabel(plan.status) : '' }}</el-descriptions-item>
</el-descriptions>
<label class="comment-label">审批意见</label>
<el-input v-model="approvalComment" type="textarea" :rows="4" placeholder="请输入审批意见..." maxlength="500" show-word-limit resize="none" />
</div>
<div class="drawer-footer"><el-button type="primary" size="large" @click="submitApproval" :loading="submittingApproval" style="flex:1">提交审批</el-button><el-button size="large" @click="showApprovalDrawer = false" style="flex:1">取消</el-button></div>
</div>
</el-drawer>
</div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useResponsive } from '../../composables/useResponsive'
import api from '../../api'
import * as planAPI from '../../api/productPlan'
import { useSubTableProgress } from '../../composables/useSubTableProgress'

// ── Types ──
interface PlanInfo {
  id: string
  name: string
  series?: string
  market?: string
  status: string
  costs?: CostItem[]
  competitor_id?: number | null
  approver?: string | null
  version_id?: number
  created_at?: string
  created_by?: string
}

interface CostItem {
  id?: number
  item_name: string
  cost_type: string
  target_value: number
  actual_value: number
  currency: string
  remark?: string
  version_id?: number
}

interface TeamMember {
  id: number
  name: string
  role: string
  department: string
  email: string
  phone: string
  version_id?: number
}

const route = useRoute()
const planId = route.params.id as string
const { isMobile } = useResponsive()

// ── Sub-table progress (useSubTableProgress) ──
const {
  subTabs,
  activeTab,
  tabStatus,
  refreshStatus,
  setSubTableDone,
  guideClick: guideClickFromComposable,
} = useSubTableProgress(planId)

// ── Mobile 5-step ──
const mobileStep = ref(0)
const savingAll = ref(false)
const savingStep = ref(false)
const mobileSteps = [
{ label: '项目概述', key: 'initiation' },
{ label: '市场客户', key: 'market' },
{ label: '技术要求', key: 'techSpec' },
{ label: '成本核算', key: 'costingNew' },
{ label: '团队', key: 'team' },
]

/** Auto-save current mobile step before navigating */
async function saveCurrentStep(stepIdx: number) {
  const key = mobileSteps[stepIdx].key
  savingStep.value = true
  try {
    switch (key) {
      case 'initiation':
        await planAPI.upsertPlanInitiation(planId, initiationForm)
        setSubTableDone('initiation', true)
        break
      case 'market':
        await planAPI.upsertPlanMarket(planId, marketForm)
        setSubTableDone('market', true)
        break
      case 'techSpec':
        await planAPI.upsertPlanTechSpec(planId, techSpecForm)
        setSubTableDone('techSpec', true)
        break
      // costingNew / team — 通过弹窗管理，无需自动保存
    }
  } catch (e: any) { /* silent — auto-save 不应阻塞导航 */ ElMessage.error(e?.response?.data?.detail || e?.message || '自动保存失败') }
  finally { savingStep.value = false }
}

async function nextStep() {
  if (mobileStep.value >= mobileSteps.length - 1) return
  await saveCurrentStep(mobileStep.value)
  mobileStep.value++
}
async function prevStep() {
  if (mobileStep.value <= 0) return
  await saveCurrentStep(mobileStep.value)
  mobileStep.value--
}

/** Guide 引导条点击 — 同步 activeTab + 移动端切换步骤 */
function guideClick(key: string, idx: number) {
  guideClickFromComposable(key, idx)
  if (isMobile.value) mobileStep.value = idx
}

/** 移动端步骤完成状态 — 已完成步骤显示✓ */
function stepStatus(key: string): 'success' | undefined {
  if (tabStatus.value[key] === 'done') return 'success'
  return undefined
}

// ── Data ──
const plan = ref<PlanInfo | null>(null)
const costs = ref<CostItem[]>([])
const loading = ref(true)
const saving = ref(false)
const editForm = ref({ name: '', series: '', market: '', competitor_id: null as number | null })
const costForm = ref({ item_name: '', cost_type: 'target', target_value: 0, actual_value: 0, currency: 'CNY', remark: '' })
const showCostDialog = ref(false)
const addingCost = ref(false)
const approvalComment = ref('')
const submittingApproval = ref(false)
const showApprovalDrawer = ref(false)

// ── 项目概述 ──
const initiationForm = reactive({ background: '', type: '', market: '', refrigerant: '', capacity: '', voltage: '', series: '', energy: '', dev_category: '', origin: '', duration: 0, ip: '', goals: '', deliverables: '', sample_qty: 0 })
const savingInitiation = ref(false)

// ── 子表版本号 ──
const initiationVersion = ref(0)
const marketVersion = ref(0)
const techSpecVersion = ref(0)
const teamVersion = ref(0)

async function fetchInitiation() {
try { const res = await planAPI.getPlanInitiation(planId); if (res.data) { Object.assign(initiationForm, res.data); initiationVersion.value = res.data.version_id ?? 0 } } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
}
async function saveInitiation() {
savingInitiation.value = true
try { const res = await planAPI.upsertPlanInitiation(planId, initiationForm); initiationVersion.value = res.data.version_id ?? 0; ElMessage.success('项目概述保存成功'); setSubTableDone('initiation', true) } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
finally { savingInitiation.value = false }
}

// ── 市场与客户 ──
const marketForm = reactive({ main_capacity: '', energy_efficiency: '', cert_requirements: '', target_price: 0, customer_requirements: '' })
const savingMarket = ref(false)

async function fetchMarket() {
try { const res = await planAPI.getPlanMarket(planId); if (res.data) { Object.assign(marketForm, res.data); marketVersion.value = res.data.version_id ?? 0 } } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
}
async function saveMarket() {
savingMarket.value = true
try { const res = await planAPI.upsertPlanMarket(planId, marketForm); marketVersion.value = res.data.version_id ?? 0; ElMessage.success('市场与客户需求保存成功'); setSubTableDone('market', true) } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
finally { savingMarket.value = false }
}

// ── 技术要求 ──
const techSpecForm = reactive({ core_performance: '', safety_compliance: '', optional_config: '' })
const savingTechSpec = ref(false)

async function fetchTechSpec() {
try { const res = await planAPI.getPlanTechSpec(planId); if (res.data) { Object.assign(techSpecForm, res.data); techSpecVersion.value = res.data.version_id ?? 0 } } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
}
async function saveTechSpec() {
savingTechSpec.value = true
try { const res = await planAPI.upsertPlanTechSpec(planId, techSpecForm); techSpecVersion.value = res.data.version_id ?? 0; ElMessage.success('技术要求保存成功'); setSubTableDone('techSpec', true) } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
finally { savingTechSpec.value = false }
}

// ── 团队 ──
const teamMembers = ref<TeamMember[]>([])
const showTeamDialog = ref(false)
const teamDialogMode = ref<'add' | 'edit'>('add')
const teamForm = reactive({ name: '', role: '', department: '', email: '', phone: '' })
const editingTeamId = ref<number | null>(null)
const savingTeam = ref(false)

async function fetchTeam() {
try { const res = await planAPI.listPlanTeam(planId); teamMembers.value = res.data || []; teamVersion.value = teamMembers.value.length > 0 ? Math.max(...teamMembers.value.map((m: TeamMember) => m.version_id ?? 0)) : 0; setSubTableDone('team', teamMembers.value.length > 0) } catch (e: any) { teamMembers.value = []; teamVersion.value = 0; setSubTableDone('team', false); ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
}
function editTeamMember(row: TeamMember) {
teamDialogMode.value = 'edit'; editingTeamId.value = row.id
Object.assign(teamForm, { name: row.name, role: row.role, department: row.department, email: row.email, phone: row.phone, version_id: row.version_id })
showTeamDialog.value = true
}
async function saveTeamMember() {
savingTeam.value = true
try {
if (teamDialogMode.value === 'add') await planAPI.addPlanTeamMember(planId, teamForm)
else if (editingTeamId.value !== null) await planAPI.updatePlanTeamMember(planId, editingTeamId.value, teamForm)
ElMessage.success(teamDialogMode.value === 'add' ? '成员添加成功' : '成员更新成功')
showTeamDialog.value = false; teamForm.name = ''; teamForm.role = ''; teamForm.department = ''; teamForm.email = ''; teamForm.phone = ''
await fetchTeam()
} catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
finally { savingTeam.value = false }
}
async function deleteTeamMember(row: TeamMember) {
try { await ElMessageBox.confirm(`确定删除「${row.name}」?`, '确认', { type: 'warning' }); await planAPI.deletePlanTeamMember(planId, row.id); ElMessage.success('已删除'); await fetchTeam() } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
}

// ── 主API ──
async function fetchPlan() {
loading.value = true
try {
const res = await api.get(`/product-plans/${planId}`)
plan.value = res.data
costs.value = res.data.costs || []
setSubTableDone('costingNew', costs.value.length > 0)
editForm.value = { name: res.data.name || '', series: res.data.series || '', market: res.data.market || '', competitor_id: res.data.competitor_id ?? null }
} catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
finally { loading.value = false }
}
async function saveQuickEdit() {
saving.value = true
try { await api.patch(`/product-plans/${planId}`, editForm.value); ElMessage.success('保存成功'); await fetchPlan() } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
finally { saving.value = false }
}

// ── 成本 ──
async function addCost() {
addingCost.value = true
try { await api.post(`/product-plans/${planId}/costs`, costForm.value); ElMessage.success('成本添加成功'); showCostDialog.value = false; costForm.value = { item_name: '', cost_type: 'target', target_value: 0, actual_value: 0, currency: 'CNY', remark: '' }; await fetchPlan(); setSubTableDone('costingNew', true) } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
finally { addingCost.value = false }
}
async function deleteCost(row: CostItem) {
try { await api.delete(`/product-plans/${planId}/costs/${row.id}`); ElMessage.success('已删除'); await fetchPlan(); setSubTableDone('costingNew', costs.value.length > 0) } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
}

// ── BOM类型 ──
const bomTypes = [
{ key: 'concept_bom', icon: '📐', label: '概念BOM', desc: '初期架构', status: 'inactive' },
{ key: 'design_bom', icon: '✏️', label: '设计BOM', desc: '详细设计', status: 'inactive' },
{ key: 'pilot_bom', icon: '🧪', label: '试产BOM', desc: '试产验证', status: 'inactive' },
{ key: 'mass_bom', icon: '🏭', label: '量产BOM', desc: '量产正式', status: 'inactive' },
]

// ── 阶段映射 ──
const STAGE_LABELS: Record<string, string> = { draft: '草稿', competitor: '竞品分析', definition: '产品定义', costing: '成本目标', tech_input: '技术方案', project_init: '立项审批', approved: '已批准', released: '已发布' }
const STAGE_TAGS: Record<string, string> = { draft: 'info', competitor: 'primary', definition: 'primary', costing: 'warning', tech_input: 'primary', project_init: 'warning', approved: 'success', released: 'success' }
function stageLabel(s: string): string { return STAGE_LABELS[s] || s }
function stageTagType(s: string): string { return STAGE_TAGS[s] || 'info' }

// ── 底部审批操作栏 ──
const canAdvance = computed(() => plan.value && ['draft', 'competitor', 'definition', 'costing', 'tech_input'].includes(plan.value.status))
const isApprovalStage = computed(() => plan.value?.status === 'project_init')
const canWithdraw = computed(() => plan.value && !['draft', 'project_init', 'released'].includes(plan.value.status))

async function advancePlan() {
try { await api.post(`/product-plans/${planId}/advance`); ElMessage.success('流程已推进'); await fetchPlan() } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
}
async function approvePlan() {
try { await api.post(`/product-plans/${planId}/approve`); ElMessage.success('已通过'); await fetchPlan() } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
}
async function rejectPlan() {
try { await api.post(`/product-plans/${planId}/reject`); ElMessage.success('已驳回'); await fetchPlan() } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
}
async function withdrawPlan() {
try { await api.post(`/product-plans/${planId}/withdraw`); ElMessage.success('已撤回'); await fetchPlan() } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
}

// ── 移动端保存全部 ──
async function saveAll() {
savingAll.value = true
try {
await api.patch(`/product-plans/${planId}`, editForm.value)
await planAPI.upsertPlanInitiation(planId, initiationForm)
await planAPI.upsertPlanMarket(planId, marketForm)
await planAPI.upsertPlanTechSpec(planId, techSpecForm)
ElMessage.success('全部保存成功')
} catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
finally { savingAll.value = false }
}

// ── 移动端审批 ──
async function submitApproval() {
submittingApproval.value = true
try { await api.post(`/product-plans/${planId}/advance`, { comment: approvalComment.value }); ElMessage.success('审批已提交'); approvalComment.value = ''; showApprovalDrawer.value = false; await fetchPlan() } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败，请重试') }
finally { submittingApproval.value = false }
}

onMounted(async () => {
  await Promise.all([
    fetchPlan(),
    fetchInitiation(),
    fetchMarket(),
    fetchTechSpec(),
    fetchTeam(),
  ])
  refreshStatus()
})
</script>

<style scoped>
.detail-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.detail-header h2 { margin: 0; font-size: 18px; flex: 1; }
.tab-toolbar { margin-bottom: 12px; }
/* PlanStatusGuide */
.plan-status-guide { display: flex; gap: 8px; margin-bottom: 20px; padding: 16px; background: #f5f7fa; border-radius: 8px; }
.guide-step { flex: 1; text-align: center; cursor: pointer; padding: 8px; border-radius: 6px; transition: all .2s; }
.guide-step:hover { background: #e8eaed; }
.guide-step.active { background: #ecf5ff; box-shadow: 0 0 0 1px #409eff; }
.guide-step.done .guide-step-num { background: #67c23a; color: #fff; }
.guide-step-num { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; background: #dcdfe6; color: #fff; font-size: 13px; font-weight: 600; margin-bottom: 4px; }
.guide-step.active .guide-step-num { background: #409eff; }
.guide-step-label { font-size: 13px; font-weight: 600; margin-bottom: 4px; color: #303133; }
/* BOM cards */
.bom-types { display: flex; gap: 12px; }
.bom-card { flex: 1; text-align: center; padding: 12px; border: 1px solid #ebeef5; border-radius: 6px; }
.bom-icon { font-size: 24px; margin-bottom: 4px; }
.bom-name { font-size: 13px; font-weight: 600; margin-bottom: 4px; }
/* Quick edit */
.quick-edit { padding: 12px; background: #fafafa; border-radius: 6px; border: 1px solid #ebeef5; }
/* Approval bar */
.approval-bar { display: flex; align-items: center; justify-content: space-between; margin-top: 16px; padding: 12px 16px; background: #fff; border: 1px solid #e4e7ed; border-radius: 6px; }
.approval-info { display: flex; gap: 20px; font-size: 13px; }
.approval-node { font-weight: 600; }
.approval-actions { display: flex; gap: 8px; }
/* Mobile */
.mobile-step-form { padding: 0 12px; }
.step-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #ebeef5; }
.mobile-step-footer { position: fixed; bottom: 0; left: 0; right: 0; display: flex; gap: 12px; padding: 12px 16px; padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px)); background: #fff; border-top: 1px solid #e4e7ed; box-shadow: 0 -2px 8px rgba(0,0,0,0.06); z-index: 100; }
.mobile-step-footer .el-button { flex: 1; }
.mobile-team-card { background: #f5f7fa; border-radius: 8px; padding: 12px; margin-bottom: 8px; }
.team-card-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.team-card-name { font-weight: 600; font-size: 14px; }
.team-card-detail { font-size: 12px; color: #909399; margin-bottom: 6px; }
.team-card-actions { display: flex; gap: 8px; }
/* Approval Drawer */
.approval-drawer-mobile :deep(.el-drawer__body) { padding: 0; overflow: hidden; }
.drawer-body { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.drawer-header { display: flex; align-items: center; justify-content: space-between; padding: 16px; border-bottom: 1px solid #e4e7ed; flex-shrink: 0; }
.drawer-header h3 { margin: 0; font-size: 18px; }
.drawer-content { flex: 1; overflow-y: auto; padding: 16px; padding-bottom: 80px; -webkit-overflow-scrolling: touch; }
.comment-label { display: block; font-size: 14px; font-weight: 600; margin-bottom: 8px; color: #303133; }
.drawer-footer { position: fixed; bottom: 0; left: 0; right: 0; display: flex; gap: 12px; padding: 12px 16px; padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px)); background: #fff; border-top: 1px solid #e4e7ed; z-index: 10; }
</style>
