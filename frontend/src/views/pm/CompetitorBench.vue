<template>
  <div class="competitor-bench">
    <el-divider content-position="left">🔍 竞品对标</el-divider>

    <!-- No market selected -->
    <el-empty v-if="!market" description="请先在 Tab1 选择目标市场" :image-size="60" />

    <!-- Loading / Error states -->
    <div v-else-if="loading" style="text-align:center;padding:20px">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <p style="color:#909399;font-size:13px;margin-top:8px">正在加载竞品数据...</p>
    </div>

    <!-- Data available -->
    <template v-else-if="benchmarkData.length > 0">
      <el-table :data="benchmarkData" border size="small" class="bench-table">
        <el-table-column prop="param_name" label="参数" width="100" />
        <el-table-column prop="our_target" label="我方目标" width="100">
          <template #default="{ row }">
            <strong>{{ row.our_target }}</strong>
          </template>
        </el-table-column>
        <el-table-column
          v-for="brand in brands"
          :key="brand"
          :label="brand"
          min-width="150"
        >
          <template #default="{ row }">
            <div
              :class="[
                'competitor-cell',
                { 'competitor-cell--adopted': isAdopted(row.param_key, brand) }
              ]"
            >
              <span class="cell-value">{{ getCompetitorValue(row, brand) }}</span>
              <el-button
                v-if="getCompetitorValue(row, brand) !== '-'"
                :type="isAdopted(row.param_key, brand) ? 'success' : 'primary'"
                size="small"
                link
                @click="handleAdopt(row, brand)"
              >
                {{ isAdopted(row.param_key, brand) ? '✓ 已采纳' : '[采纳]' }}
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <!-- No data after load -->
    <el-empty v-else description="暂无竞品对标数据" :image-size="60" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import api from '../../api'

const props = defineProps<{
  market: string
  coolingCapacity?: string
}>()

const emit = defineEmits<{
  adopt: [payload: { paramKey: string; value: number; brand: string }]
}>()

interface CompetitorEntry {
  value: number
  model?: string
}

interface BenchmarkRow {
  param_key: string
  param_name: string
  our_target: string
  competitors: Record<string, CompetitorEntry>
}

const benchmarkData = ref<BenchmarkRow[]>([])
const loading = ref(false)
const adoptedKeys = ref<Set<string>>(new Set())

// Compute unique brand names from all rows
const brands = computed(() => {
  const brandSet = new Set<string>()
  for (const row of benchmarkData.value) {
    if (row.competitors) {
      Object.keys(row.competitors).forEach(b => brandSet.add(b))
    }
  }
  return Array.from(brandSet)
})

function getCompetitorValue(row: BenchmarkRow, brand: string): string {
  const entry = row.competitors?.[brand]
  if (!entry || entry.value === undefined || entry.value === null) return '-'
  return String(entry.value)
}

function isAdopted(paramKey: string, brand: string): boolean {
  return adoptedKeys.value.has(`${paramKey}|${brand}`)
}

function handleAdopt(row: BenchmarkRow, brand: string) {
  const entry = row.competitors?.[brand]
  if (!entry) return

  const key = `${row.param_key}|${brand}`
  adoptedKeys.value.add(key)
  // Trigger reactivity
  adoptedKeys.value = new Set(adoptedKeys.value)

  emit('adopt', {
    paramKey: row.param_key,
    value: entry.value,
    brand: brand,
  })
}

/** 将后端返回的 {market, competitors, param_names} 转换为 BenchmarkRow[] */
function transformBenchmarkData(raw: any): BenchmarkRow[] {
  if (!raw || !raw.param_names || !raw.competitors) return []

  const competitors = raw.competitors as any[]
  const paramNames = raw.param_names as Array<{ key: string; label: string; unit: string }>

  // 收集所有品牌名
  const brandSet = new Set<string>()
  for (const c of competitors) {
    if (c.brand) brandSet.add(c.brand)
  }

  return paramNames.map((p) => {
    const row: BenchmarkRow = {
      param_key: p.key,
      param_name: p.unit ? `${p.label} (${p.unit})` : p.label,
      our_target: '—',
      competitors: {},
    }

    for (const c of competitors) {
      const val = c[p.key]
      if (val !== undefined && val !== null) {
        row.competitors[c.brand] = { value: Number(val), model: c.model || '' }
      }
    }

    return row
  })
}

async function fetchBenchmark(market: string) {
  if (!market) return
  loading.value = true
  try {
    const res = await api.get('/pm/competitors/benchmark', { params: { market } })
    benchmarkData.value = transformBenchmarkData(res.data)
    // Reset adopted state when market changes
    adoptedKeys.value = new Set()
  } catch {
    benchmarkData.value = []
  } finally {
    loading.value = false
  }
}

// Watch market changes
watch(() => props.market, (newMarket) => {
  if (newMarket) {
    fetchBenchmark(newMarket)
  } else {
    benchmarkData.value = []
  }
}, { immediate: true })
</script>

<style scoped>
.competitor-bench {
  margin-top: 16px;
}

.bench-table {
  margin-top: 8px;
}

.competitor-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 0;
}

.competitor-cell--adopted {
  background-color: #f0f9eb;
  border: 1px solid #67c23a;
  border-radius: 4px;
  padding: 4px 8px;
}

.cell-value {
  font-variant-numeric: tabular-nums;
}
</style>
