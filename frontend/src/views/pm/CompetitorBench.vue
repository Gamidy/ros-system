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
      <!-- 完整性提示 -->
      <div v-if="!allComplete" style="margin-bottom:12px;padding:8px 12px;background:#fdf6ec;border-radius:6px;font-size:13px;color:#e6a23c;border:1px solid #faecd8;">
        ⚠️ 部分竞品数据不完整，请在「竞品对标」页面补全数据
      </div>
      <div v-else style="margin-bottom:12px;padding:8px 12px;background:#f0f9eb;border-radius:6px;font-size:13px;color:#67c23a;border:1px solid #e1f3d8;">
        ✅ 所有竞品数据完整
      </div>

      <el-table :data="benchmarkData" border size="small" class="bench-table" empty-text="暂无竞品对标数据">
        <el-table-column prop="param_name" label="参数" width="110" />
        <el-table-column prop="our_target" label="我方目标" width="100">
          <template #default="{ row }">
            <strong>{{ row.our_target }}</strong>
          </template>
        </el-table-column>
        <el-table-column
          v-for="brand in brands"
          :key="brand"
          :label="brand"
          min-width="130"
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
  value: number | string
  model?: string
}

interface BenchmarkRow {
  param_key: string
  param_name: string
  our_target: string
  competitors: Record<string, CompetitorEntry>
}

interface MarketOption {
  code: string
  name: string
  is_active?: string
}

interface CompetitorDataItem {
  brand: string
  model?: string
  is_complete?: boolean
  [key: string]: unknown
}

interface BenchmarkApiResponse {
  competitors?: CompetitorDataItem[]
  param_names?: Array<{ key: string; label: string; unit: string }>
}

const competitorData = ref<CompetitorDataItem[]>([])
const benchmarkData = ref<BenchmarkRow[]>([])
const loading = ref(false)
const adoptedKeys = ref<Set<string>>(new Set())
const allComplete = ref(false)

// 市场代码/名称映射（从父组件传入的 props.market 可能是代码如"VN"，需转名称如"越南"）
const marketOptions = ref<Array<{code: string; name: string}>>([])

// 初始化时加载市场选项（代码→名称映射）
api.get('/pm/markets/all').then((res: { data: MarketOption[] }) => {
  const data = res.data
  if (Array.isArray(data)) {
    marketOptions.value = data
      .filter((m) => m.is_active !== 'false' && /^[A-Z]{2}$/.test(m.code))
      .map((m) => ({ code: m.code, name: m.name }))
  }
}).catch(() => {
  // 回退：从知识库加载
  api.get('/kb/items', { params: { category: 'market' } }).then((res2: { data: MarketOption[] }) => {
    const data = res2.data
    if (Array.isArray(data)) marketOptions.value = data
  }).catch(() => {})
})

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
  adoptedKeys.value = new Set(adoptedKeys.value)

  emit('adopt', {
    paramKey: row.param_key,
    value: typeof entry.value === 'number' ? entry.value : parseFloat(String(entry.value)) || 0,
    brand: brand,
  })
}

/** 将后端返回的 {market, competitors, param_names} 转换为 BenchmarkRow[] */
function transformBenchmarkData(raw: BenchmarkApiResponse): BenchmarkRow[] {
  if (!raw || !raw.param_names || !raw.competitors) return []

  const competitors = raw.competitors
  const paramNames = raw.param_names

  return paramNames.map((p) => {
    const row: BenchmarkRow = {
      param_key: p.key,
      param_name: p.unit ? `${p.label} (${p.unit})` : p.label,
      our_target: '—',
      competitors: {},
    }

    for (const c of competitors) {
      let val = c[p.key]
      // 对能效字段做市场适配
      if (val === undefined || val === null) {
        // 如果是EER字段且不存在，尝试用 cspf/iseer/seer
        if (p.key === 'eer') {
          val = c.cspf ?? c.iseer ?? c.seer
        }
      }
      if (val !== undefined && val !== null) {
        row.competitors[c.brand] = { value: Number(val) || val, model: c.model || '' }
      }
    }

    return row
  })
}

async function fetchBenchmark(market: string) {
  if (!market) return
  loading.value = true
  try {
    // 市场代码 → 名称转换
    const mkt = marketOptions.value.find((m) => m.code === market || m.name === market)
    const marketName = mkt ? mkt.name : market
    const res = await api.get('/pm/competitors/benchmark', { params: { market: marketName } })
    competitorData.value = res.data.competitors || []
    benchmarkData.value = transformBenchmarkData(res.data)
    // Check completeness
    allComplete.value = competitorData.value.every((c) => c.is_complete)
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
