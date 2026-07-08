<template>
  <div>
    <!-- 一、项目开发费用 -->
    <el-divider content-position="left">一、项目开发费用</el-divider>
    <el-table :data="devCostTable" border size="small" class="section-table">
      <el-table-column prop="item" label="费用项目" width="140" />
      <el-table-column label="预算(W)" width="140">
        <template #default="{ row }">
          <template v-if="row.item === '委外开发费用'">
            <el-input-number
              v-if="projectForm.has_outsourcing"
              v-model="row.budget"
              :min="0" :step="0.1" size="small" controls-position="right" style="width:100%"
            />
            <span v-else class="linked-val">0.0</span>
          </template>
          <template v-else>
            <el-input-number
              v-if="!row.linked"
              v-model="row.budget"
              :min="0" :step="0.1" size="small" controls-position="right" style="width:100%"
            />
            <span v-else class="linked-val">{{ row.budget.toFixed(1) }}</span>
          </template>
        </template>
      </el-table-column>
      <el-table-column label="占比%" width="100">
        <template #default="{ row }">
          {{ devCostGrandTotal > 0 ? ((row.budget / devCostGrandTotal) * 100).toFixed(1) : '0.0' }}%
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="说明" min-width="280">
        <template #default="{ row }">
          <span class="linked-val">{{ row.remark }}</span>
        </template>
      </el-table-column>
    </el-table>
    <div class="cost-summary">开发费用合计: <strong>¥{{ devCostGrandTotal.toFixed(1) }} 万元</strong></div>
    <div style="margin-top:8px;display:flex;align-items:center;gap:8px">
      <el-switch v-model="projectForm.has_outsourcing" size="small" active-text="有委外开发" inactive-text="无委外开发" />
    </div>

    <!-- 二、经济指标分析 -->
    <el-divider content-position="left">二、经济指标分析</el-divider>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label="目标出厂价FOB($)(美元)" label-width="150px" size="small">
          <el-input-number v-model="projectForm.fob_price" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="汇率(USD/CNY)" label-width="130px" size="small">
          <el-input :model-value="exchangeRate.toFixed(2)" disabled size="small" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="目标BOM成本(￥)(人民币)" label-width="140px" size="small">
          <el-input-number v-model="projectForm.bom_cost_target" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label-width="150px" size="small">
          <template #label>
            BOM成本占比
            <el-tooltip content="BOM成本占出厂价的比例，计算公式: BOM成本÷(FOB价格×汇率)×100%" placement="top">
              <el-icon style="margin-left:4px;cursor:help;color:#909399"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-input :model-value="bomCostRatioText" disabled size="small" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label-width="130px" size="small">
          <template #label>
            制造费用+人工(￥)
            <el-tooltip content="制造费用和人工成本合计(万元)，由系统按配置自动计算" placement="top">
              <el-icon style="margin-left:4px;cursor:help;color:#909399"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-input :model-value="manufacturingCost.toFixed(0)" disabled size="small" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label-width="140px" size="small">
          <template #label>
            毛利(￥)
            <el-tooltip content="毛利 = 出厂价 - BOM成本 - 制造费用 - 人工费用，反映项目盈利能力" placement="top">
              <el-icon style="margin-left:4px;cursor:help;color:#909399"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-input :model-value="grossMarginText" disabled size="small" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="16">
      <el-col :span="12">
        <el-form-item label="年销量预测(首年)(台)" label-width="140px" size="small">
          <el-input-number v-model="projectForm.annual_sales_forecast" :min="0" :step="1000" size="small" controls-position="right" style="width:100%" />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item label="产品生命周期" label-width="120px" size="small">
          <el-input v-model="projectForm.product_lifecycle" size="small" placeholder="如: 5年" />
        </el-form-item>
      </el-col>
    </el-row>

    <!-- 三、模具/工装费用初步核算 -->
    <el-divider content-position="left">三、模具/工装费用初步核算</el-divider>
    <div style="margin-bottom:8px">
      <el-button size="small" @click="addMoldRow">+ 添加行</el-button>
    </div>
    <el-table :data="moldCostTable" border size="small" class="section-table">
      <el-table-column label="模具名称" min-width="160">
        <template #default="{ row }">
          <el-input v-model="row.name" size="small" placeholder="模具名称" />
        </template>
      </el-table-column>
      <el-table-column label="数量(副)" width="100">
        <template #default="{ row }">
          <el-input-number v-model="row.qty" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
        </template>
      </el-table-column>
      <el-table-column label="合计(W)" width="130">
        <template #default="{ row }">
          <el-input-number v-model="row.total" :min="0" :step="0.1" size="small" controls-position="right" style="width:100%" />
        </template>
      </el-table-column>
      <el-table-column label="备注" min-width="160">
        <template #default="{ row }">
          <el-input v-model="row.remark" size="small" placeholder="备注" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="70">
        <template #default="{ $index }">
          <el-button link type="danger" size="small" @click="removeMoldRow($index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="cost-summary">模具/工装合计: <strong>¥{{ moldCostTotal.toFixed(1) }} 万元</strong></div>

    <!-- 四、试制费用（按项目等级确定数量） -->
    <el-divider content-position="left">四、试制费用</el-divider>
    <div class="cost-summary" style="background:#f0f9eb;padding:10px 16px;border-radius:6px;margin-bottom:8px">
      试制数量: <strong>{{ trialQty }}台</strong>（按项目等级「{{ projectForm.dev_category || '未设置' }}」自动确定）
      <el-tooltip content="全新开发≥20台，派生≥10台，降本优化≥5台，高难度/高复杂度项目可适当上浮" placement="top">
        <el-icon style="margin-left:4px;cursor:help;color:#909399"><QuestionFilled /></el-icon>
      </el-tooltip>
      <span v-if="trialQty > 20" style="color:#e6a23c;margin-left:8px">⚠ 建议分批试制</span>
    </div>

    <!-- 五、试制样机费用 -->
    <el-divider content-position="left">五、试制样机费用</el-divider>
    <el-table :data="protoCostTable" border size="small" class="section-table">
      <el-table-column prop="stage" label="阶段" width="80" />
      <el-table-column label="数量(台)" width="100">
        <template #default="{ row }">
          <el-input-number v-model="row.qty" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
        </template>
      </el-table-column>
      <el-table-column label="单套费用(W)" width="130">
        <template #default="{ row }">
          <el-input-number v-model="row.unit_cost" :min="0" :step="0.1" size="small" controls-position="right" style="width:100%" />
        </template>
      </el-table-column>
      <el-table-column label="合计(W)" width="120">
        <template #default="{ row }">
          {{ (row.qty * row.unit_cost).toFixed(2) }}
        </template>
      </el-table-column>
    </el-table>
    <div class="cost-summary">样机合计: P0~P2 <strong>¥{{ protoDevTotal.toFixed(2) }} 万元</strong> | 客户样机: <strong>¥{{ clientSampleCost.toFixed(2) }} 万元</strong> | 总计: <strong>¥{{ protoCostTotal.toFixed(2) }} 万元</strong></div>

    <!-- 六、人工费用初步核算 -->
    <el-divider content-position="left">六、人工费用初步核算</el-divider>
    <el-table :data="laborCostTable" border size="small" class="section-table">
      <el-table-column prop="module" label="模块" width="100" />
      <el-table-column label="人数(人)" width="80">
        <template #default="{ row }">
          <el-input-number v-model="row.people_count" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
        </template>
      </el-table-column>
      <el-table-column label="月薪(W)" width="110">
        <template #default="{ row }">
          <el-input-number v-model="row.monthly_salary" :min="0" :step="0.1" size="small" controls-position="right" style="width:100%" />
        </template>
      </el-table-column>
      <el-table-column label="人月" width="130">
        <template #default="{ row }">
          <span class="linked-val">{{ (row.months * (row.occupancy_rate || 100) / 100).toFixed(1) }}</span>
          <div style="font-size:11px;color:#909399">{{ row.months }}月 × {{ row.occupancy_rate || 100 }}%</div>
        </template>
      </el-table-column>
      <el-table-column label="占用度%" width="100">
        <template #default="{ row }">
          <el-input-number v-model="row.occupancy_rate" :min="0" :max="100" :step="10" size="small" controls-position="right" style="width:100%" />
        </template>
      </el-table-column>
      <el-table-column label="人月数" width="80">
        <template #default="{ row }">
          <el-input-number v-model="row.months" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
        </template>
      </el-table-column>
      <el-table-column label="费用(W)" width="120">
        <template #default="{ row }">
          {{ (row.people_count * row.monthly_salary * row.months * (row.occupancy_rate || 100) / 100).toFixed(1) }}
        </template>
      </el-table-column>
    </el-table>
    <div class="cost-summary">人工费用合计: <strong>¥{{ laborCostTotal.toFixed(1) }} 万元</strong></div>

    <!-- 七、测试费用 -->
    <el-divider content-position="left">七、测试费用</el-divider>
    <el-table :data="testCostTable" border size="small" class="section-table">
      <el-table-column prop="stage" label="阶段" width="80" />
      <el-table-column label="天数(天)" width="100">
        <template #default="{ row }">
          <el-input-number v-model="row.days" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
        </template>
      </el-table-column>
      <el-table-column label="单价(W)" width="120">
        <template #default="{ row }">
          <span>{{ row.unit_price.toFixed(3) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="合计(W)" width="120">
        <template #default="{ row }">
          {{ (row.days * row.unit_price).toFixed(2) }}
        </template>
      </el-table-column>
    </el-table>
    <div class="cost-summary">测试费用合计: <strong>¥{{ testCostTotal.toFixed(2) }} 万元</strong></div>

    <!-- 八、认证费用（从Tab3安全合规自动生成） -->
    <el-divider content-position="left">
      八、认证费用（从Tab3安全合规自动生成）
      <el-tooltip content="认证费用从Tab3安全合规标准自动映射，在Tab3填写标准后此处自动生成费用项，可手动调整金额" placement="top">
        <el-icon style="margin-left:6px;cursor:help;color:#909399;font-size:14px"><QuestionFilled /></el-icon>
      </el-tooltip>
    </el-divider>
    <el-table v-if="certCostTable.length > 0" :data="certCostTable" border size="small" class="section-table">
      <el-table-column prop="cert_name" label="标准名" width="100" />
      <el-table-column prop="cert_body" label="认证机构" width="100" />
      <el-table-column label="费用(W)" width="130">
        <template #default="{ row }">
          <el-input-number v-model="row.cost_wan" :min="0" :step="0.1" size="small" controls-position="right" style="width:100%" />
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="160">
        <template #default="{ row }">
          <el-input v-model="row.remark" size="small" placeholder="备注" />
        </template>
      </el-table-column>
    </el-table>
    <div v-else class="cost-summary" style="color:#909399">暂无认证费用（请在Tab3填写安全合规标准后自动生成）</div>
    <div v-if="certCostTable.length > 0" class="cost-summary">认证费用合计: <strong>¥{{ certCostTotal.toFixed(1) }} 万元</strong></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { QuestionFilled } from '@element-plus/icons-vue'

interface DevCostRow { item: string; budget: number; remark: string; linked: boolean }
interface MoldCostRow { name: string; qty: number; total: number; remark: string }
interface ProtoCostRow { stage: string; qty: number; unit_cost: number }
interface LaborCostRow { module: string; people_count: number; monthly_salary: number; months: number; occupancy_rate: number }
interface TestCostRow { stage: string; days: number; unit_price: number }
interface CertCostRow { cert_name: string; cert_body: string; cost_wan: number; remark: string }
interface ProjectForm { [key: string]: any }

const props = defineProps<{
  tabStatus: Record<string, { valid: boolean }>
  devCostTable: DevCostRow[]
  moldCostTable: MoldCostRow[]
  protoCostTable: ProtoCostRow[]
  laborCostTable: LaborCostRow[]
  testCostTable: TestCostRow[]
  certCostTable: CertCostRow[]
  projectForm: ProjectForm
  exchangeRate: number
  systemConfig: Record<string, any>
}>()

// Computed cost summaries
const moldCostTotal = computed(() =>
  props.moldCostTable.reduce((sum, r) => sum + (r.total || 0), 0)
)

const protoDevTotal = computed(() =>
  props.protoCostTable.filter(r => r.stage !== '客户样机').reduce((sum, r) => sum + (r.qty || 0) * (r.unit_cost || 0), 0)
)

const clientSampleCost = computed(() => {
  const row = props.protoCostTable.find(r => r.stage === '客户样机')
  return row ? (row.qty || 0) * (row.unit_cost || 0) : 0
})

const protoCostTotal = computed(() =>
  props.protoCostTable.reduce((sum, r) => sum + (r.qty || 0) * (r.unit_cost || 0), 0)
)

const laborCostTotal = computed(() =>
  props.laborCostTable.reduce((sum, r) => sum + (r.people_count || 0) * (r.monthly_salary || 0) * (r.months || 0) * ((r.occupancy_rate || 100) / 100), 0)
)

const testCostTotal = computed(() =>
  props.testCostTable.reduce((sum, r) => sum + (r.days || 0) * (r.unit_price || 0), 0)
)

const certCostTotal = computed(() =>
  props.certCostTable.reduce((sum, r) => sum + (Number(r.cost_wan) || 0), 0)
)

const trialQty = computed(() => {
  const dc = props.projectForm.dev_category
  if (!dc) return 5
  const raw = props.systemConfig?.trial_qty_per_class
  const map: Record<string, number> = (() => {
    if (raw) { try { return JSON.parse(raw) } catch {} }
    return { 'T': 5, 'A': 3, 'B': 2, 'C': 1 }
  })()
  return map[dc] ?? map['C'] ?? 1
})

const manufacturingCost = computed(() => {
  const cr = props.projectForm.capacity_range
  const thresholds: Array<{max_kw: number; cost: number}> = (() => {
    const raw = props.systemConfig?.mfg_cost_threshold
    if (raw) { try { return JSON.parse(raw) } catch {} }
    return [{max_kw: 12, cost: 50}, {max_kw: 999, cost: 60}]
  })()
  if (!cr) return thresholds[0]?.cost || 50
  const upper = String(cr).toUpperCase()
  const kwMatch = upper.match(/(\d+)K/)
  if (!kwMatch) return thresholds[0]?.cost || 50
  const kw = parseInt(kwMatch[1])
  for (const t of thresholds) {
    if (kw <= t.max_kw) return t.cost
  }
  return thresholds[thresholds.length - 1]?.cost || 60
})

const devCostGrandTotal = computed(() => {
  const sumFirst7 = props.devCostTable.slice(0, 7).reduce((s, r) => s + (Number(r.budget) || 0), 0)
  return sumFirst7 + certCostTotal.value
})

const bomCostRatioText = computed(() => {
  const fob = Number(props.projectForm.fob_price) || 0
  const bom = Number(props.projectForm.bom_cost_target) || 0
  const rate = Number(props.exchangeRate) || 7.2
  if (fob <= 0 || rate <= 0) return '-'
  const fobCny = fob * rate
  return ((bom / fobCny) * 100).toFixed(1) + '%'
})

const grossMarginText = computed(() => {
  const fob = Number(props.projectForm.fob_price) || 0
  const bom = Number(props.projectForm.bom_cost_target) || 0
  const rate = Number(props.exchangeRate) || 7.2
  const mfg = manufacturingCost.value
  if (fob <= 0 || rate <= 0) return '-'
  const fobCny = fob * rate
  const totalCost = bom + mfg
  const gross = fobCny - totalCost
  return '¥' + gross.toFixed(0) + ' (' + (fobCny > 0 ? ((gross / fobCny) * 100).toFixed(1) : '0.0') + '%)'
})

// Event handlers
function addMoldRow() {
  props.moldCostTable.push({ name: '', qty: 0, total: 0, remark: '' })
}
function removeMoldRow(index: number) {
  props.moldCostTable.splice(index, 1)
}
</script>
