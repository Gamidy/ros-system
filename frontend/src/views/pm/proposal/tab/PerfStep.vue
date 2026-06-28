<template>
  <div class="perf-step">
    <h3 class="step-title">❶ 核心性能参数</h3>
    <el-alert
      title="制冷量从项目概述能力段自动计算 (BTU ÷ 3.4128 取整)，标记为自动填充"
      type="info"
      show-icon
      :closable="false"
      style="margin-bottom:12px"
    />
    <el-table :data="performanceItems" border size="small" style="width:100%">
      <el-table-column prop="label" label="参数名称" width="160" />
      <el-table-column label="参数值" width="180">
        <template #default="{ row }">
          <el-input
            v-model="row.value"
            size="small"
            :disabled="row.source === 'auto'"
            :class="{ 'auto-fill': row.source === 'auto' }"
          >
            <template #suffix v-if="row.source === 'auto'">
              <el-tag size="small" type="warning" style="margin-right:4px">auto</el-tag>
            </template>
          </el-input>
        </template>
      </el-table-column>
      <el-table-column prop="unit" label="单位" width="80" />
      <el-table-column prop="source" label="来源" width="80">
        <template #default="{ row }">
          <el-tag :type="row.source === 'auto' ? 'warning' : ''" size="small">
            {{ row.source === 'auto' ? '自动' : '手动' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="说明" min-width="180">
        <template #default="{ row }">
          <span style="font-size:12px;color:#909399">{{ row.hint }}</span>
        </template>
      </el-table-column>
    </el-table>

    <h3 class="step-title" style="margin-top:20px">能效等级参考</h3>
    <el-alert
      title="以下能效等级默认值从管理员配置加载，可根据实际调整"
      type="success"
      show-icon
      :closable="false"
      style="margin-bottom:12px"
    />
    <el-table :data="energyLevelDefaults" border size="small" style="width:100%">
      <el-table-column prop="level_name" label="等级名称" width="120" />
      <el-table-column prop="seer_min" label="SEER" width="120" />
      <el-table-column prop="eer_min" label="EER" width="120" />
      <el-table-column prop="cspf_min" label="CSPF" width="120" />
      <el-table-column prop="is_primary" label="主销" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_primary === 'true' ? 'success' : 'info'" size="small">
            {{ row.is_primary === 'true' ? '是' : '否' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { reactive, computed, watch, onMounted } from 'vue'
import api from '../../../../api'

interface PerformanceItem {
  key: string
  label: string
  value: string | number
  unit: string
  source: 'auto' | 'manual'
  hint: string
}

interface EnergyLevelDefault {
  level_name: string
  seer_min: number | null
  eer_min: number | null
  cspf_min: number | null
  is_primary: string
}

const props = defineProps<{
  data: Record<string, unknown>
}>()

const emit = defineEmits<{
  update: [patch: Record<string, unknown>]
}>()

/** 目标市场（从 data 中推断） */
const targetMarket = computed(() => {
  return (props.data?.target_market as string) || (props.data?.market as string) || ''
})

/** BTU 能力值（从 Tab1 数据获取，可能在 main_capacity 或 btu 字段） */
const btuCapacity = computed(() => {
  const raw = props.data?.main_capacity ?? props.data?.btu_capacity ?? props.data?.capacity_btu ?? ''
  const num = parseFloat(String(raw))
  return isNaN(num) ? 0 : num
})

/** 性能参数表 */
const performanceItems = reactive<PerformanceItem[]>([
  { key: 'cooling_capacity', label: '制冷量', value: 0, unit: 'W', source: 'auto', hint: 'BTU÷3.4128 自动计算' },
  { key: 'heating_capacity', label: '制热量', value: '', unit: 'W', source: 'manual', hint: '' },
  { key: 'voltage', label: '电压', value: '', unit: 'V', source: 'manual', hint: '' },
  { key: 'frequency', label: '频率', value: '', unit: 'Hz', source: 'manual', hint: '' },
  { key: 'tolerance', label: '容差', value: '', unit: '%', source: 'manual', hint: '如: ±10%' },
  { key: 'energy_rating', label: '能效等级', value: '', unit: '-', source: 'manual', hint: '如: 一级' },
  { key: 'cspf', label: 'CSPF', value: '', unit: '-', source: 'manual', hint: '全年能源消耗效率' },
])

/** 能效等级默认值（从管理员配置加载） */
const energyLevelDefaults = reactive<EnergyLevelDefault[]>([])

function autoCalcCoolingCapacity() {
  const btu = btuCapacity.value
  if (btu > 0) {
    const cooling = Math.round(btu / 3.4128)
    const item = performanceItems.find(p => p.key === 'cooling_capacity')
    if (item) {
      item.value = cooling
      item.source = 'auto'
    }
  }
}

/** 从 API 加载能效等级默认值 */
async function loadEnergyLevelDefaults() {
  if (!targetMarket.value) return
  try {
    const res = await api.get(`/pm/markets/energy-levels`, {
      params: { market_code: targetMarket.value },
    })
    const items: EnergyLevelDefault[] = res.data?.items || res.data || []
    energyLevelDefaults.length = 0
    items.forEach(item => energyLevelDefaults.push({ ...item }))
  } catch (e: unknown) {
    // 非关键 — 使用静态示例数据
    if (energyLevelDefaults.length === 0) {
      energyLevelDefaults.push(
        { level_name: '一级', seer_min: 5.0, eer_min: 3.6, cspf_min: 5.0, is_primary: 'true' },
        { level_name: '二级', seer_min: 4.5, eer_min: 3.2, cspf_min: 4.5, is_primary: 'false' },
        { level_name: '三级', seer_min: 4.0, eer_min: 2.8, cspf_min: 4.0, is_primary: 'false' },
      )
    }
  }
}

function serializePerformanceData(): string {
  return JSON.stringify({
    items: performanceItems.map(p => ({
      key: p.key,
      label: p.label,
      value: p.value,
      unit: p.unit,
      source: p.source,
    })),
    energy_levels: energyLevelDefaults.map(e => ({ ...e })),
  })
}

function emitUpdate() {
  emit('update', { core_performance: serializePerformanceData() })
}

// 监听变化自动 emit
watch(performanceItems, () => emitUpdate(), { deep: true })
watch(energyLevelDefaults, () => emitUpdate(), { deep: true })

// 从父组件已有数据恢复状态
function restoreFromData() {
  if (props.data?.core_performance) {
    try {
      const parsed = JSON.parse(props.data.core_performance as string)
      if (parsed.items && Array.isArray(parsed.items)) {
        parsed.items.forEach((item: Record<string, unknown>) => {
          const target = performanceItems.find(p => p.key === item.key)
          if (target) {
            target.value = item.value as string | number
            target.source = (item.source as 'auto' | 'manual') || 'manual'
          }
        })
      }
      if (parsed.energy_levels && Array.isArray(parsed.energy_levels)) {
        energyLevelDefaults.length = 0
        parsed.energy_levels.forEach((e: Record<string, unknown>) => energyLevelDefaults.push(e as unknown as EnergyLevelDefault))
      }
    } catch (e: unknown) {
      // 忽略字符串格式的旧数据
    }
  }
}

onMounted(async () => {
  restoreFromData()
  autoCalcCoolingCapacity()
  await loadEnergyLevelDefaults()
})
</script>

<style scoped>
.perf-step { min-height: 200px; }
.step-title { font-size: 16px; font-weight: 600; color: #303133; margin: 0 0 12px 0; }
.auto-fill :deep(.el-input__wrapper) { background-color: #fdf6ec; }
</style>
