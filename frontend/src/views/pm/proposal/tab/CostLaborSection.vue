<template>
  <div class="cost-labor-section">
    <!-- 6. 人工成本 -->
    <el-card shadow="never" class="cost-section">
      <template #header>
        <span class="section-header">6️⃣ 人工成本 <small class="section-hint">（人月 = 项目周期 × 投入占比）</small></span>
      </template>
      <el-form :model="laborForm" label-width="140px" size="small">
        <el-form-item label="项目周期(月)">
          <el-input-number v-model="laborForm.durationMonths" :min="0" :precision="1" :step="0.5" size="small" controls-position="right" style="width:100px" @change="recalcLabor" />
          <span v-if="parsedDurationMonths > 0" class="auto-hint">（从起止日期自动计算：{{ parsedDurationMonths }} 个月）</span>
        </el-form-item>
        <el-form-item label="人员投入占比(%)">
          <el-input-number v-model="laborForm.occupancyRate" :min="0" :max="100" :precision="1" :step="5" size="small" controls-position="right" style="width:100px" @change="recalcLabor" />
        </el-form-item>
        <el-form-item label="人月数">
          <el-tag type="primary" size="large" effect="dark">{{ laborForm.personMonths.toFixed(1) }} 人月</el-tag>
        </el-form-item>
        <el-form-item label="人工成本(万元)">
          <el-input-number v-model="laborForm.totalCost" :min="0" :precision="2" :step="1" size="small" controls-position="right" style="width:120px" @change="emitLaborUpdate" />
          <span class="auto-hint">（建议 = 人月 × 月费率，可手动调整）</span>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 7. 间接成本 -->
    <el-card shadow="never" class="cost-section">
      <template #header>
        <span class="section-header">7️⃣ 间接成本 <small class="section-hint">（默认从配置加载）</small></span>
      </template>
      <el-form :model="indirectForm" label-width="140px" size="small">
        <el-form-item label="间接成本(万元)">
          <el-input-number v-model="indirectForm.cost" :min="0" :precision="2" :step="0.1" size="small" controls-position="right" style="width:120px" @change="emitLaborUpdate" />
          <span class="auto-hint">（系统默认：{{ indirectCostDefault }} 万元）</span>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import api from '../../../../api'

const props = defineProps<{
  data: Record<string, unknown>
}>()

const emit = defineEmits<{
  update: [patch: Record<string, unknown>]
}>()

const formData = computed(() => props.data)

// Config
const indirectCostDefault = ref(0.5)

// Labor
function parseDurationMonths(durationStr: unknown): number {
  if (!durationStr || typeof durationStr !== 'string') return 0
  const monthMatch = durationStr.match(/(\d+(?:\.\d+)?)\s*个月/)
  if (monthMatch) return parseFloat(monthMatch[1])
  const dayMatch = durationStr.match(/(\d+(?:\.\d+)?)\s*天/)
  if (dayMatch) return parseFloat(dayMatch[1]) / 30
  const numMatch = durationStr.match(/(\d+(?:\.\d+)?)/)
  if (numMatch) return parseFloat(numMatch[1])
  return 0
}

function computeMonthsFromDates(): number {
  const sd = formData.value?.start_date
  const ed = formData.value?.target_end_date
  if (!sd || !ed || typeof sd !== 'string' || typeof ed !== 'string') return 0
  try {
    const start = new Date(sd)
    const end = new Date(ed)
    if (isNaN(start.getTime()) || isNaN(end.getTime())) return 0
    const diffMs = end.getTime() - start.getTime()
    if (diffMs <= 0) return 0
    return Math.ceil(diffMs / (1000 * 60 * 60 * 24)) / 30
  } catch (e: unknown) {
    return 0
  }
}

const parsedDurationMonths = computed(() => {
  const fromDuration = parseDurationMonths(formData.value?.project_duration)
  if (fromDuration > 0) return fromDuration
  return computeMonthsFromDates()
})

const laborForm = reactive({
  durationMonths: 6,
  occupancyRate: 50,
  personMonths: 3,
  totalCost: 0,
})

watch(parsedDurationMonths, (val) => {
  if (val > 0) {
    laborForm.durationMonths = Math.round(val * 10) / 10
    recalcLabor()
  }
}, { immediate: true })

function recalcLabor(): void {
  laborForm.personMonths = laborForm.durationMonths * (laborForm.occupancyRate / 100)
  if (laborForm.totalCost === 0) {
    laborForm.totalCost = Math.round(laborForm.personMonths * 1.5 * 100) / 100
  }
  emitLaborUpdate()
}

// Indirect
const indirectForm = reactive({
  cost: 0.5,
})

function emitLaborUpdate() {
  emit('update', {
    labor_costs: JSON.stringify({
      duration_months: laborForm.durationMonths,
      occupancy_rate: laborForm.occupancyRate,
      person_months: laborForm.personMonths,
      total_cost: laborForm.totalCost,
    }),
    indirect_cost: indirectForm.cost,
  })
}

// Restore from saved data
function restoreFromData() {
  const laborRaw = formData.value?.labor_costs
  if (laborRaw && typeof laborRaw === 'string') {
    try {
      const parsed = JSON.parse(laborRaw)
      if (parsed.duration_months !== undefined) laborForm.durationMonths = parsed.duration_months
      if (parsed.occupancy_rate !== undefined) laborForm.occupancyRate = parsed.occupancy_rate
      if (parsed.person_months !== undefined) laborForm.personMonths = parsed.person_months
      if (parsed.total_cost !== undefined) laborForm.totalCost = parsed.total_cost
    } catch (e: unknown) {
      // ignore
    }
  }
}

// Load config for indirect default
async function loadConfig(): Promise<void> {
  try {
    const res = await api.get('/admin/config/public')
    const cfg = (res.data as Record<string, unknown>)?.data as Record<string, unknown> || {}
    if (cfg.indirect_cost) {
      const val = Number(cfg.indirect_cost)
      if (!isNaN(val)) {
        indirectCostDefault.value = val / 10000
      }
    }
  } catch (e: unknown) {
    indirectCostDefault.value = 0.5
  }
  indirectForm.cost = indirectCostDefault.value
}

onMounted(() => {
  restoreFromData()
  loadConfig()
})
</script>

<style scoped>
.cost-section { margin-bottom: 16px; border-left: 3px solid #409eff; }
.section-header { font-size: 15px; font-weight: 600; color: #303133; }
.section-hint { color: #909399; font-weight: normal; font-size: 12px; margin-left: 6px; }
.auto-hint { margin-left: 8px; font-size: 12px; color: #909399; }
</style>
