<template>
  <div class="cost-prototype-section">
    <!-- 1. 原型开发成本 -->
    <el-card shadow="never" class="cost-section">
      <template #header>
        <span class="section-header">1️⃣ 原型开发成本 <small class="section-hint">（单价按能力段查表，自动计算）</small></span>
      </template>
      <el-table :data="protoCostTable" size="small" border stripe>
        <el-table-column label="样机阶段" width="120">
          <template #default="{ row }">
            <el-tag :type="row.stage === '客户样机' ? 'warning' : 'primary'" size="small" effect="plain">{{ row.stage }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="能力段" prop="capacityKey" width="80" />
        <el-table-column label="单价(万元)" width="110">
          <template #default="{ row }">
            <el-input-number v-model="row.unitPrice" :min="0" :precision="3" :step="0.01" size="small" controls-position="right" style="width:90px" @change="emitProtoUpdate" />
          </template>
        </el-table-column>
        <el-table-column label="数量" width="80">
          <template #default="{ row }">
            <el-input-number v-model="row.qty" :min="0" :max="99" size="small" controls-position="right" style="width:65px" @change="emitProtoUpdate" />
          </template>
        </el-table-column>
        <el-table-column label="小计(万元)" width="100">
          <template #default="{ row }">
            <span class="cost-value">{{ (row.unitPrice * row.qty).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="140">
          <template #default="{ row }">
            <el-input v-model="row.remark" size="small" placeholder="备注" @input="emitProtoUpdate" />
          </template>
        </el-table-column>
      </el-table>
      <div class="section-total">小计：<el-tag type="primary" size="large" effect="dark">{{ protoCostTotal.toFixed(2) }} 万元</el-tag></div>
    </el-card>

    <!-- 2. 模具费用 -->
    <el-card shadow="never" class="cost-section">
      <template #header>
        <span class="section-header">2️⃣ 模具费用 <small class="section-hint">（数量 + 总费用 + 备注）</small></span>
      </template>
      <el-table :data="moldCostTable" size="small" border stripe>
        <el-table-column label="序号" type="index" width="50" />
        <el-table-column label="模具名称" min-width="160">
          <template #default="{ row }">
            <el-input v-model="row.name" size="small" placeholder="模具名称" @input="emitProtoUpdate" />
          </template>
        </el-table-column>
        <el-table-column label="数量" width="80">
          <template #default="{ row }">
            <el-input-number v-model="row.qty" :min="1" size="small" controls-position="right" style="width:65px" @change="emitProtoUpdate" />
          </template>
        </el-table-column>
        <el-table-column label="总费用(万元)" width="130">
          <template #default="{ row }">
            <el-input-number v-model="row.totalCost" :min="0" :precision="2" :step="0.1" size="small" controls-position="right" style="width:110px" @change="emitProtoUpdate" />
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="140">
          <template #default="{ row }">
            <el-input v-model="row.remark" size="small" placeholder="备注" @input="emitProtoUpdate" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="60" fixed="right">
          <template #default="{ $index }">
            <el-button type="danger" size="small" link @click="removeMoldRow($index)">✕</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="section-actions">
        <el-button size="small" type="primary" plain @click="addMoldRow">+ 添加模具</el-button>
        <span class="section-total">小计：<el-tag type="primary" size="large" effect="dark">{{ moldCostTotal.toFixed(2) }} 万元</el-tag></span>
      </div>
    </el-card>

    <!-- 3. 试制费用 -->
    <el-card shadow="never" class="cost-section">
      <template #header>
        <span class="section-header">3️⃣ 试制费用 <small class="section-hint">（试制数量按项目等级自动确定）</small></span>
      </template>
      <el-form :model="trialForm" label-width="120px" size="small">
        <el-form-item label="试制数量">
          <el-input-number v-model="trialForm.qty" :min="0" :max="99" size="small" controls-position="right" style="width:100px" @change="emitProtoUpdate" />
          <span v-if="formData.project_class" class="auto-hint">（项目等级「{{ formData.project_class }}」默认为 {{ autoTrialQty }} 台）</span>
        </el-form-item>
        <el-form-item label="单价(万元)">
          <el-input-number v-model="trialForm.unitPrice" :min="0" :precision="4" :step="0.01" size="small" controls-position="right" style="width:100px" @change="emitProtoUpdate" />
        </el-form-item>
        <el-form-item label="试制总费用">
          <el-tag type="primary" size="large" effect="dark">{{ trialCostTotal.toFixed(2) }} 万元</el-tag>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import api from '../../../../api'

interface ProtoCostRow {
  stage: string
  capacityKey: string
  unitPrice: number
  qty: number
  remark: string
}

interface MoldCostRow {
  name: string
  qty: number
  totalCost: number
  remark: string
}

interface CapacityCostEntry {
  btu: number
  cost: number
}

type CapacityUnitCostMap = Record<string, CapacityCostEntry>

const props = defineProps<{
  data: Record<string, unknown>
}>()

const emit = defineEmits<{
  update: [patch: Record<string, unknown>]
}>()

const formData = computed(() => props.data)

// Config
const capacityUnitCostMap = ref<CapacityUnitCostMap>({})
const trialQtyPerClass = ref<Record<string, number>>({})

// Proto Cost
const PROTO_STAGES = ['P0', 'P1', 'P2', '客户样机']
const protoCostTable = reactive<ProtoCostRow[]>([])

function initProtoCostTable(): void {
  const capKey = getCapacityKey()
  protoCostTable.length = 0
  const unitCost = lookupUnitCost(capKey)
  const baseQty = 2
  PROTO_STAGES.forEach((stage) => {
    const price = stage === '客户样机' ? unitCost * 1.2 : unitCost
    protoCostTable.push({
      stage,
      capacityKey: capKey,
      unitPrice: price,
      qty: stage === '客户样机' ? 1 : baseQty,
      remark: '',
    })
  })
  emitProtoUpdate()
}

function getCapacityKey(): string {
  const raw = formData.value?.capacity_range
  if (!raw || typeof raw !== 'string') return '12K'
  const m = raw.match(/(\d{2})K/i)
  return m ? m[0].toUpperCase() : '12K'
}

function lookupUnitCost(capKey: string): number {
  const entry = capacityUnitCostMap.value[capKey]
  if (entry && typeof entry.cost === 'number') return entry.cost
  const altKey = capKey.length === 3 ? `0${capKey}` : capKey.replace(/^0/, '')
  const alt = capacityUnitCostMap.value[altKey]
  if (alt && typeof alt.cost === 'number') return alt.cost
  const keys = Object.keys(capacityUnitCostMap.value)
  if (keys.length > 0) {
    const first = capacityUnitCostMap.value[keys[0]]
    if (first && typeof first.cost === 'number') return first.cost
  }
  return 0.105
}

const protoCostTotal = computed(() => {
  return protoCostTable.reduce((sum, row) => sum + row.unitPrice * row.qty, 0)
})

// Mold Cost
const moldCostTable = reactive<MoldCostRow[]>([])

function addMoldRow(): void {
  moldCostTable.push({ name: '', qty: 1, totalCost: 0, remark: '' })
  emitProtoUpdate()
}

function removeMoldRow(index: number): void {
  moldCostTable.splice(index, 1)
  emitProtoUpdate()
}

const moldCostTotal = computed(() => {
  return moldCostTable.reduce((sum, row) => sum + row.totalCost, 0)
})

// Trial Cost
const autoTrialQty = computed(() => {
  const pc = formData.value?.project_class
  if (pc && typeof pc === 'string' && trialQtyPerClass.value[pc] !== undefined) {
    return trialQtyPerClass.value[pc]
  }
  return 0
})

const trialForm = reactive({
  qty: 0,
  unitPrice: 0.05,
})

watch(autoTrialQty, (val) => {
  if (val > 0 && trialForm.qty === 0) {
    trialForm.qty = val
    emitProtoUpdate()
  }
}, { immediate: true })

const trialCostTotal = computed(() => {
  return trialForm.qty * trialForm.unitPrice
})

// Emit
function emitProtoUpdate() {
  emit('update', {
    dev_cost_items: JSON.stringify({
      proto_costs: protoCostTable.map((r) => ({
        stage: r.stage,
        capacity_key: r.capacityKey,
        unit_price: r.unitPrice,
        qty: r.qty,
        subtotal: r.unitPrice * r.qty,
        remark: r.remark,
      })),
      total: protoCostTotal.value,
    }),
    mold_costs: JSON.stringify({
      items: moldCostTable.map((r) => ({
        name: r.name,
        qty: r.qty,
        total_cost: r.totalCost,
        remark: r.remark,
      })),
      total: moldCostTotal.value,
    }),
    prototype_costs_detail: JSON.stringify({
      trial: {
        qty: trialForm.qty,
        unit_price: trialForm.unitPrice,
        total: trialCostTotal.value,
      },
    }),
  })
}

// Watch capacity_range
watch(() => formData.value?.capacity_range, () => {
  initProtoCostTable()
}, { immediate: false })

// Load config
async function loadConfig(): Promise<void> {
  try {
    const res = await api.get('/admin/config/public')
    const cfg = (res.data as Record<string, unknown>)?.data as Record<string, unknown> || {}
    if (cfg.capacity_unit_cost_map && typeof cfg.capacity_unit_cost_map === 'string') {
      try {
        capacityUnitCostMap.value = JSON.parse(cfg.capacity_unit_cost_map)
      } catch (e: unknown) {
        capacityUnitCostMap.value = {}
      }
    }
    if (cfg.trial_qty_per_class && typeof cfg.trial_qty_per_class === 'string') {
      try {
        trialQtyPerClass.value = JSON.parse(cfg.trial_qty_per_class)
      } catch (e: unknown) {
        trialQtyPerClass.value = {}
      }
    }
  } catch (e: unknown) {
    capacityUnitCostMap.value = {
      '07K': { btu: 7000, cost: 0.075 },
      '09K': { btu: 9000, cost: 0.095 },
      '12K': { btu: 12000, cost: 0.105 },
      '18K': { btu: 18000, cost: 0.142 },
      '22K': { btu: 22000, cost: 0.178 },
      '24K': { btu: 24000, cost: 0.178 },
    }
    trialQtyPerClass.value = { T: 5, A: 3, B: 2, C: 1 }
  }
  initProtoCostTable()
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.cost-section { margin-bottom: 16px; border-left: 3px solid #409eff; }
.section-header { font-size: 15px; font-weight: 600; color: #303133; }
.section-hint { color: #909399; font-weight: normal; font-size: 12px; margin-left: 6px; }
.section-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 10px; }
.section-total { text-align: right; margin-top: 10px; font-size: 13px; color: #606266; }
.cost-value { font-weight: 600; color: #d97757; }
.auto-hint { margin-left: 8px; font-size: 12px; color: #909399; }
</style>
