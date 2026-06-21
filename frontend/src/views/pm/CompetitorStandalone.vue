<template>
  <div class="competitor-standalone">
    <!-- ========== 页面标题 ========== -->
    <div class="page-header">
      <h2>🔍 竞品对标</h2>
      <p class="page-desc">查看各市场竞品参数对比数据</p>
    </div>

    <!-- ========== 筛选栏 ========== -->
    <div class="filters-bar">
      <div class="filter-item">
        <label>目标市场</label>
        <el-select
          v-model="selectedMarket"
          placeholder="请选择市场"
          @change="onMarketChange"
        >
          <el-option
            v-for="m in markets"
            :key="m"
            :label="m"
            :value="m"
          />
        </el-select>
      </div>
      <div class="filter-item">
        <label>冷量段</label>
        <el-select
          v-model="selectedCapacity"
          placeholder="全部"
          clearable
          @change="fetchData"
        >
          <el-option
            v-for="c in capacities"
            :key="c"
            :label="c"
            :value="c"
          />
        </el-select>
      </div>
    </div>

    <!-- ========== 统计卡片 ========== -->
    <div v-if="selectedMarket && !loading" class="stats-row">
      <div class="stat-card">
        <div class="stat-label">品牌数</div>
        <div class="stat-value">{{ brandCount }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">机型数</div>
        <div class="stat-value">{{ modelCount }}</div>
      </div>
    </div>

    <!-- ========== 加载状态 ========== -->
    <div v-if="loading" class="loading-wrap">
      <el-icon class="is-loading" :size="28"><Loading /></el-icon>
      <p>正在加载竞品数据...</p>
    </div>

    <!-- ========== 空状态 ========== -->
    <el-empty
      v-else-if="!selectedMarket"
      description="请选择目标市场查看竞品对标数据"
      :image-size="80"
    />

    <!-- ========== 数据表格 ========== -->
    <template v-else-if="benchmarkData.length > 0">
      <div class="table-card">
        <el-table
          :data="benchmarkData"
          border
          size="small"
          class="bench-table"
          :header-cell-style="headerCellStyle"
        >
          <el-table-column
            prop="param_name"
            label="参数"
            width="140"
            fixed="left"
          />
          <el-table-column
            prop="our_target"
            label="我方目标"
            width="110"
          >
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
              <span class="cell-value">{{ getCompetitorValue(row, brand) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </template>

    <!-- ========== 无数据 ========== -->
    <el-empty
      v-else
      description="该市场暂无竞品数据"
      :image-size="80"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import api from '../../api'

// ── 市场 & 冷量段选项 ──────────────────────────────────────────────
const markets = ['越南', '泰国', '印尼', '中东']
const capacities = ['9000BTU', '12000BTU', '18000BTU', '24000BTU']

const selectedMarket = ref('')
const selectedCapacity = ref('')

// ── 数据状态 ──────────────────────────────────────────────────────
const loading = ref(false)
const allItems = ref<any[]>([])

// ── 参数定义（与后端 PARAM_NAMES 对齐）────────────────────────────
const PARAM_DEFS = [
  { key: 'cooling_w',         label: '制冷功率',       unit: 'W' },
  { key: 'heating_w',         label: '制热功率',       unit: 'W' },
  { key: 'eer',               label: '能效比 EER',     unit: '' },
  { key: 'noise_indoor_db',   label: '室内噪音',       unit: 'dB' },
  { key: 'noise_outdoor_db',  label: '室外噪音',       unit: 'dB' },
  { key: 'airflow_m3h',       label: '循环风量',       unit: 'm³/h' },
  { key: 'indoor_size_mm',    label: '内机尺寸',       unit: 'mm' },
  { key: 'outdoor_size_mm',   label: '外机尺寸',       unit: 'mm' },
  { key: 'factory_price',     label: '出厂价',         unit: '' },
  { key: 'launch_year',       label: '上市年份',       unit: '' },
  { key: 'energy_rating',     label: '能效等级',       unit: '' },
]

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

// ── 统计 ──────────────────────────────────────────────────────────
const brandCount = computed(() => {
  const brands = new Set(allItems.value.map((it: any) => it.brand))
  return brands.size
})

const modelCount = computed(() => allItems.value.length)

// ── 品牌列表 ──────────────────────────────────────────────────────
const brands = computed(() => {
  const brandSet = new Set<string>()
  for (const row of benchmarkData.value) {
    Object.keys(row.competitors).forEach(b => brandSet.add(b))
  }
  return Array.from(brandSet)
})

// ── 数据转换 ──────────────────────────────────────────────────────
function transformToBenchmark(items: any[]): BenchmarkRow[] {
  if (!items || items.length === 0) return []

  return PARAM_DEFS.map((p) => {
    const row: BenchmarkRow = {
      param_key: p.key,
      param_name: p.unit ? `${p.label} (${p.unit})` : p.label,
      our_target: '—',
      competitors: {},
    }

    for (const item of items) {
      const val = item[p.key]
      if (val !== undefined && val !== null && val !== '') {
        // 每个品牌取首个有值的机型
        if (!row.competitors[item.brand]) {
          row.competitors[item.brand] = {
            value: Number(val),
            model: item.model || '',
          }
        }
      }
    }

    return row
  })
}

// ── 表格数据 ──────────────────────────────────────────────────────
const benchmarkData = computed(() => transformToBenchmark(allItems.value))

function getCompetitorValue(row: BenchmarkRow, brand: string): string {
  const entry = row.competitors?.[brand]
  if (!entry || entry.value === undefined || entry.value === null) return '-'
  return String(entry.value)
}

// ── 表头样式 ──────────────────────────────────────────────────────
const headerCellStyle = {
  background: '#fdfaf3',
  color: '#5c4a3a',
  fontWeight: 600,
  fontSize: '13px',
}

// ── 数据获取 ──────────────────────────────────────────────────────
async function fetchData() {
  if (!selectedMarket.value) {
    allItems.value = []
    return
  }

  loading.value = true
  try {
    const params: Record<string, any> = {
      market: selectedMarket.value,
      page: 1,
      page_size: 200,
    }
    if (selectedCapacity.value) {
      params.capacity = selectedCapacity.value
    }

    const res = await api.get('/pm/competitors', { params })
    allItems.value = res.data.items || []
  } catch {
    allItems.value = []
  } finally {
    loading.value = false
  }
}

function onMarketChange() {
  selectedCapacity.value = ''
  fetchData()
}
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════════════
   Claude 暖纸色风格
   ═══════════════════════════════════════════════════════════════════ */

.competitor-standalone {
  --c-bg-page: #f5f4ed;
  --c-bg-card: #fffdf7;
  --c-accent: #d97757;
  --c-text: #4a3f35;
  --c-text-muted: #8c8279;
  --c-border: #e5dfd3;

  min-height: calc(100vh - 80px);
  padding: 24px 28px;
  background: var(--c-bg-page);
  color: var(--c-text);
}

/* ── 页面标题 ──────────────────────────────────────────────────── */
.page-header {
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 700;
  color: var(--c-text);
}
.page-desc {
  margin: 0;
  font-size: 13px;
  color: var(--c-text-muted);
}

/* ── 筛选栏 ────────────────────────────────────────────────────── */
.filters-bar {
  display: flex;
  gap: 20px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.filter-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.filter-item label {
  font-size: 12px;
  font-weight: 600;
  color: var(--c-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.filter-item :deep(.el-select) {
  width: 180px;
}

/* ── 统计卡片 ──────────────────────────────────────────────────── */
.stats-row {
  display: flex;
  gap: 16px;
  margin-bottom: 18px;
}
.stat-card {
  background: var(--c-bg-card);
  border: 1px solid var(--c-border);
  border-radius: 8px;
  padding: 14px 24px;
  min-width: 120px;
  text-align: center;
}
.stat-label {
  font-size: 12px;
  color: var(--c-text-muted);
  margin-bottom: 4px;
}
.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--c-accent);
}

/* ── 加载 ──────────────────────────────────────────────────────── */
.loading-wrap {
  text-align: center;
  padding: 48px 0;
  color: var(--c-text-muted);
}
.loading-wrap p {
  margin-top: 10px;
  font-size: 13px;
}

/* ── 表格卡片 ──────────────────────────────────────────────────── */
.table-card {
  background: var(--c-bg-card);
  border: 1px solid var(--c-border);
  border-radius: 10px;
  padding: 16px;
  overflow-x: auto;
}

.bench-table {
  font-size: 13px;
}

/* 表格行 hover */
.bench-table :deep(.el-table__body tr:hover > td) {
  background: #fdfaf3 !important;
}

/* 单元格值 */
.cell-value {
  font-variant-numeric: tabular-nums;
  color: var(--c-text);
}

/* Select 下拉面板暖色 */
:deep(.el-select-dropdown__item.selected) {
  color: var(--c-accent);
  font-weight: 600;
}
:deep(.el-select-dropdown__item:hover) {
  background: #fdf6ee;
}

/* Empty 组件适配暖色 */
:deep(.el-empty__description p) {
  color: var(--c-text-muted);
}
</style>
