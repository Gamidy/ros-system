<template>
  <el-form :model="form" label-width="110" size="small" class="overview-market-form">
    <!-- ═══ 一、项目基本信息 ═══ -->
    <el-divider content-position="left">一、项目基本信息</el-divider>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label="产品类型">
          <el-select v-model="form.product_type" filterable clearable placeholder="请选择" style="width:100%">
            <el-option v-for="o in kbOptions.product_type" :key="o" :label="o" :value="o" />
          </el-select>
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="目标市场">
          <el-select v-model="form.target_market" filterable clearable placeholder="请选择" style="width:100%">
            <el-option v-for="m in marketOptions" :key="m.name" :label="m.name" :value="m.name" />
          </el-select>
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="气候带">
          <el-input v-model="form.climate_zone" placeholder="自由文本" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label="制冷剂">
          <el-input v-model="form.refrigerant" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="客户名称">
          <el-input v-model="form.customer_name" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="能力段">
          <el-cascader
            v-model="form.capacity_segment"
            :options="capacityOptions"
            placeholder="选择能力段"
            clearable
            style="width:100%"
          />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label="电压频率">
          <el-input v-model="form.voltage_freq" placeholder="例: 220V/50Hz" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="知识产权">
          <el-select v-model="form.ip_ownership" filterable clearable placeholder="请选择" style="width:100%">
            <el-option v-for="o in kbOptions.ip_ownership" :key="o" :label="o" :value="o" />
          </el-select>
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="开发类别">
          <el-select v-model="form.dev_category" filterable clearable placeholder="请选择" style="width:100%">
            <el-option v-for="o in kbOptions.dev_category" :key="o" :label="o" :value="o" />
          </el-select>
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label="项目来源">
          <el-select v-model="form.project_origin" filterable clearable placeholder="请选择" style="width:100%" @change="onOriginChange">
            <el-option v-for="o in kbOptions.project_origin" :key="o" :label="o" :value="o" />
          </el-select>
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="年度规划">
          <el-select
            v-model="form.annual_planning_id"
            filterable
            clearable
            placeholder="选择年度规划"
            style="width:100%"
            :disabled="form.project_origin !== '产品年度规划'"
          >
            <el-option v-for="p in annualPlans" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label="立项日期">
          <el-date-picker v-model="form.start_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width:100%" @change="calcDuration" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="计划完成">
          <el-date-picker v-model="form.plan_completion_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width:100%" @change="calcDuration" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="项目周期">
          <el-input :model-value="formattedDuration" readonly placeholder="自动计算">
            <template #suffix><span style="color:#909399">天</span></template>
          </el-input>
        </el-form-item>
      </el-col>
    </el-row>
    <el-form-item label="其他要求">
      <el-input v-model="form.other_requirements" type="textarea" :rows="2" />
    </el-form-item>

    <!-- ═══ 二、项目背景与目标 ═══ -->
    <el-divider content-position="left">二、项目背景与目标</el-divider>
    <el-form-item label="立项背景">
      <el-input v-model="form.background_basis" type="textarea" :rows="3" />
    </el-form-item>
    <el-form-item label="总体目标">
      <el-input v-model="form.overall_goal" type="textarea" :rows="2" />
    </el-form-item>
    <el-row :gutter="16">
      <el-col :span="8"><el-form-item label="技术目标"><el-input v-model="form.tech_goal" type="textarea" :rows="2" /></el-form-item></el-col>
      <el-col :span="8"><el-form-item label="成本目标"><el-input v-model="form.cost_goal" type="textarea" :rows="2" /></el-form-item></el-col>
      <el-col :span="8"><el-form-item label="销售目标"><el-input v-model="form.sales_goal" type="textarea" :rows="2" /></el-form-item></el-col>
    </el-row>
    <el-row :gutter="16">
      <el-col :span="8"><el-form-item label="认证目标"><el-input v-model="form.cert_goal" type="textarea" :rows="2" /></el-form-item></el-col>
      <el-col :span="8"><el-form-item label="进度目标"><el-input v-model="form.schedule_goal" type="textarea" :rows="2" /></el-form-item></el-col>
      <el-col :span="8"><el-form-item label="专利目标"><el-input v-model="form.patent_goal" type="textarea" :rows="2" /></el-form-item></el-col>
    </el-row>

    <!-- ═══ 三、市场分析 ═══ -->
    <el-divider content-position="left">三、市场分析</el-divider>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label="年度规划引用">
          <el-select v-model="form.annual_planning_ref" filterable clearable placeholder="引用年度规划" style="width:100%">
            <el-option v-for="p in annualPlans" :key="p.id" :label="p.name" :value="p.name" />
          </el-select>
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="市场规模">
          <el-input v-model="form.market_size" placeholder="台/年" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="售价">
          <el-input v-model="form.selling_price" placeholder="USD/CNY" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label="销量">
          <el-input v-model="form.sales_volume" placeholder="台/年" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-form-item label="竞品分析">
      <el-input v-model="form.competitor_analysis" type="textarea" :rows="3" placeholder="主要竞品、市场格局、竞争优势等" />
    </el-form-item>
    <el-form-item label="客户关键需求">
      <div class="customer-req-wrapper">
        <el-button size="small" type="primary" style="margin-bottom:6px" @click="addCustomerReq">+ 添加需求</el-button>
        <el-table :data="customerReqList" stripe border size="small" empty-text="暂无客户需求">
          <el-table-column label="需求类别" min-width="120">
            <template #default="{ row }">
              <el-input v-model="row.category" size="small" placeholder="如：能效" @input="inputChanged" />
            </template>
          </el-table-column>
          <el-table-column label="需求描述" min-width="180">
            <template #default="{ row }">
              <el-input v-model="row.description" size="small" placeholder="需求描述" @input="inputChanged" />
            </template>
          </el-table-column>
          <el-table-column label="来源" width="120">
            <template #default="{ row }">
              <el-select v-model="row.source" size="small" placeholder="来源" style="width:100%">
                <el-option label="市场调研" value="市场调研" />
                <el-option label="客户反馈" value="客户反馈" />
                <el-option label="竞品分析" value="竞品分析" />
                <el-option label="客户需求" value="客户需求" />
                <el-option label="标准要求" value="标准要求" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="技术影响" width="100">
            <template #default="{ row }">
              <el-select v-model="row.tech_impact" size="small" style="width:100%">
                <el-option label="高" value="高" />
                <el-option label="中" value="中" />
                <el-option label="低" value="低" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="市场影响" width="100">
            <template #default="{ row }">
              <el-select v-model="row.market_impact" size="small" style="width:100%">
                <el-option label="高" value="高" />
                <el-option label="中" value="中" />
                <el-option label="低" value="低" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="60">
            <template #default="{ $index }">
              <el-button link size="small" type="danger" @click="removeCustomerReq($index)">删</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-form-item>

    <!-- ═══ 四、交付物 ═══ -->
    <el-divider content-position="left">四、交付物</el-divider>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label="样机数量">
          <el-input-number v-model="form.sample_qty" :min="0" :max="9999" style="width:100%" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="需求日期">
          <el-date-picker v-model="form.required_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-form-item label="清单">
      <el-input v-model="form.deliverables" type="textarea" :rows="3" placeholder="交付物清单，每行一项" />
    </el-form-item>

    <!-- ═══ 底部：所属项目群 + 项目负责人 ═══ -->
    <el-divider />
    <el-row :gutter="16">
      <el-col :span="12">
        <el-form-item label="所属项目群">
          <el-select v-model="form.program_id" filterable clearable placeholder="选择项目群" style="width:100%">
            <el-option v-for="p in programOptions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item label="项目负责人">
          <el-select v-model="form.leader_id" filterable clearable placeholder="选择负责人" style="width:100%">
            <el-option v-for="u in userOptions" :key="u.id" :label="u.full_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
      </el-col>
    </el-row>
  </el-form>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import api from '../../api'
import * as planAPI from '../../api/productPlan'
import type { MarketOption } from '../../api/productPlan'

// ── Types ──
interface CustomerReqRow {
  category: string
  description: string
  source: string
  tech_impact: string
  market_impact: string
}

interface ProgramOption {
  id: number
  name: string
  code: string
}

interface UserInfo {
  id: number
  username: string
  full_name: string
  department: string
  position: string
  role: string
}

interface OverviewMarketForm {
  product_type: string
  target_market: string
  climate_zone: string
  refrigerant: string
  customer_name: string
  capacity_segment: string[]
  voltage_freq: string
  ip_ownership: string
  dev_category: string
  project_origin: string
  annual_planning_id: number | null
  start_date: string
  plan_completion_date: string
  project_duration: number
  other_requirements: string
  background_basis: string
  overall_goal: string
  tech_goal: string
  cost_goal: string
  sales_goal: string
  cert_goal: string
  schedule_goal: string
  patent_goal: string
  annual_planning_ref: string
  market_size: string
  selling_price: string
  sales_volume: string
  competitor_analysis: string
  sample_qty: number | null
  required_date: string
  deliverables: string
  program_id: number | null
  leader_id: number | null
}

// ── Form data ──
const form = reactive<OverviewMarketForm>({
  product_type: '',
  target_market: '',
  climate_zone: '',
  refrigerant: '',
  customer_name: '',
  capacity_segment: [],
  voltage_freq: '',
  ip_ownership: '',
  dev_category: '',
  project_origin: '',
  annual_planning_id: null,
  start_date: '',
  plan_completion_date: '',
  project_duration: 0,
  other_requirements: '',
  background_basis: '',
  overall_goal: '',
  tech_goal: '',
  cost_goal: '',
  sales_goal: '',
  cert_goal: '',
  schedule_goal: '',
  patent_goal: '',
  annual_planning_ref: '',
  market_size: '',
  selling_price: '',
  sales_volume: '',
  competitor_analysis: '',
  sample_qty: null,
  required_date: '',
  deliverables: '',
  program_id: null,
  leader_id: null,
})

// ── 客户关键需求表格 ──
const customerReqList = reactive<CustomerReqRow[]>([])

function addCustomerReq() {
  customerReqList.push({ category: '', description: '', source: '市场调研', tech_impact: '中', market_impact: '中' })
}

function removeCustomerReq(index: number) {
  customerReqList.splice(index, 1)
}

function inputChanged() {
  // placeholder to ensure reactivity on table inline inputs
}

// ── 能力段 Cascader 选项 ──
const structureTypes = ['分体壁挂']
const capacityOptions = ['7K', '9K', '12K', '18K', '24K'].map(cap => ({
  value: cap,
  label: cap,
  children: structureTypes.map(st => ({ value: st, label: st })),
}))

// ── 项目周期自动计算 ──
function calcDuration() {
  if (form.start_date && form.plan_completion_date) {
    const start = new Date(form.start_date)
    const end = new Date(form.plan_completion_date)
    const diff = Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
    form.project_duration = diff >= 0 ? diff : 0
  } else {
    form.project_duration = 0
  }
}

const formattedDuration = computed(() => {
  return form.project_duration > 0 ? String(form.project_duration) : ''
})

// ── 项目来源联动 ──
function onOriginChange(val: string) {
  if (val !== '产品年度规划') {
    form.annual_planning_id = null
  }
}

// ── 下拉选项数据 ──
const kbOptions = reactive<Record<string, string[]>>({
  product_type: [],
  ip_ownership: [],
  dev_category: [],
  project_origin: [],
})
const KB_CATEGORIES = ['product_type', 'ip_ownership', 'dev_category', 'project_origin'] as const

async function fetchKbOptions() {
  try {
    const results = await Promise.allSettled(
      KB_CATEGORIES.map(cat => api.get(`/kb/items?category=${cat}`))
    )
    results.forEach((r, i) => {
      if (r.status === 'fulfilled') {
        const data = r.value.data as string[]
        kbOptions[KB_CATEGORIES[i]] = data || []
      }
    })
  } catch { /* non-critical */ }
}

// ── 市场选项 ──
const marketOptions = ref<MarketOption[]>([])
async function fetchMarketOptions() {
  try {
    const res = await planAPI.fetchMarkets()
    marketOptions.value = (res.data || []) as MarketOption[]
  } catch {
    marketOptions.value = []
  }
}

// ── 年度规划列表 ──
interface PlanListItem {
  id: number
  name: string
  year?: string
}
const annualPlans = ref<PlanListItem[]>([])
async function fetchAnnualPlans() {
  try {
    const res = await planAPI.listPlans()
    annualPlans.value = (res.data || []) as PlanListItem[]
  } catch {
    annualPlans.value = []
  }
}

// ── 项目群选项 ──
const programOptions = ref<ProgramOption[]>([])
async function fetchPrograms() {
  try {
    const res = await api.get('/pm/programs')
    programOptions.value = (res.data || []) as ProgramOption[]
  } catch { /* non-critical */ }
}

// ── 用户选项 ──
const userOptions = ref<UserInfo[]>([])
async function fetchUsers() {
  try {
    const res = await api.get('/kb/team')
    userOptions.value = (res.data || []) as UserInfo[]
  } catch { /* non-critical */ }
}

// ── 加载初始数据 ──
onMounted(async () => {
  await Promise.allSettled([
    fetchKbOptions(),
    fetchMarketOptions(),
    fetchAnnualPlans(),
    fetchPrograms(),
    fetchUsers(),
  ])
})

// ── Expose for parent component ──
defineExpose({
  form,
  customerReqList,
  capacityOptions,
})
</script>

<style scoped>
.overview-market-form {
  max-width: 100%;
}
.customer-req-wrapper {
  width: 100%;
}
</style>
