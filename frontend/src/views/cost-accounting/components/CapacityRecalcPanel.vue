<template>
  <div class="recalc-panel">
    <!-- 触发重算按钮 -->
    <div class="recalc-actions">
      <el-button type="warning" @click="handleRunRecalc" :loading="running" :disabled="!productPlanId">
        ⚡ 冷量联动重算
      </el-button>
      <span v-if="running" class="hint">正在匹配冷量基准…</span>
    </div>

    <!-- 无冷量参数提示 -->
    <el-alert v-if="noCapacity" title="产品无冷量参数配置" type="warning" show-icon :closable="false"
      description="请先在「产品策划→立项数据」中填写主销容量或覆盖容量，才能进行冷量联动重算。" class="mb-16" />

    <!-- 最近重算结果 -->
    <div v-if="recalcHistory.length > 0" class="recalc-history">
      <h4>历史重算记录</h4>

      <!-- 当前最新结果卡片 -->
      <div v-if="latestResult" class="result-card" :class="scoreLevel">
        <el-row :gutter="16">
          <el-col :span="6">
            <div class="metric">
              <div class="label">冷量段</div>
              <div class="value">{{ latestResult.capacity_key || '-' }}
                <span v-if="latestResult.matched_btu" class="sub">({{ latestResult.matched_btu }} BTU)</span>
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric">
              <div class="label">基准物料成本</div>
              <div class="value mono">¥{{ formatMoney(latestResult.baseline_material_cost) }}</div>
              <div class="sub" v-if="latestResult.complexity_factor !== 1">
                复杂度系数: {{ latestResult.complexity_factor }}
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric">
              <div class="label">实际BOM成本</div>
              <div class="value mono">¥{{ formatMoney(latestResult.actual_bom_cost) }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric">
              <div class="label">成本效率评分</div>
              <div class="value large" :style="{ color: scoreColor }">{{ latestResult.cost_efficiency_score }}</div>
            </div>
          </el-col>
        </el-row>

        <el-divider />

        <!-- 差异对比 -->
        <el-row :gutter="16" class="variance-row">
          <el-col :span="8">
            <div class="variance-item">
              <span class="dim-label">差异额</span>
              <span class="dim-value mono" :class="latestResult.variance_amount > 0 ? 'over' : 'under'">
                {{ latestResult.variance_amount > 0 ? '+' : '' }}{{ formatMoney(latestResult.variance_amount) }} 元
              </span>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="variance-item">
              <span class="dim-label">差异率</span>
              <span class="dim-value" :class="latestResult.variance_pct > 0 ? 'over' : 'under'">
                {{ latestResult.variance_pct > 0 ? '+' : '' }}{{ latestResult.variance_pct }}%
              </span>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="variance-item">
              <span class="dim-label">触发方式</span>
              <span class="dim-value">{{ triggerLabel(latestResult.trigger_source) }}</span>
            </div>
          </el-col>
        </el-row>

        <!-- 明细行 -->
        <el-table :data="latestResult.items || []" size="small" border stripe class="detail-table">
          <el-table-column prop="dimension" label="维度" width="100">
            <template #default="{ row }">
              <el-tag :type="dimTagType(row.dimension)" size="small">{{ dimLabel(row.dimension) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="item_name" label="项目" min-width="140" />
          <el-table-column prop="baseline_amount" label="基准(元)" width="120" align="right">
            <template #default="{ row }">{{ formatMoney(row.baseline_amount) }}</template>
          </el-table-column>
          <el-table-column prop="actual_amount" label="实际(元)" width="120" align="right">
            <template #default="{ row }">{{ formatMoney(row.actual_amount) }}</template>
          </el-table-column>
          <el-table-column prop="variance" label="差异(元)" width="120" align="right">
            <template #default="{ row }">
              <span :class="row.variance > 0 ? 'over' : 'under'">
                {{ row.variance > 0 ? '+' : '' }}{{ formatMoney(row.variance) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="variance_pct" label="差异率" width="100" align="right">
            <template #default="{ row }">
              <span :class="row.variance_pct > 0 ? 'over' : 'under'">
                {{ row.variance_pct > 0 ? '+' : '' }}{{ row.variance_pct }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="180" />
        </el-table>

        <div class="recalc-time">
          上次重算: {{ latestResult.created_at }} | {{ latestResult.created_by || 'system' }}
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <el-empty v-if="!loading && recalcHistory.length === 0 && !running" description="暂无重算记录" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  triggerRecalculation, getRecalcResultsByPlan,
} from '../../../api/costAccounting'

const props = defineProps<{
  productPlanId?: string
  periodId?: number
  sheetId?: number
}>()

const loading = ref(false)
const running = ref(false)
const recalcHistory = ref<any[]>([])
const noCapacity = ref(false)

const latestResult = computed(() => recalcHistory.value.length > 0 ? recalcHistory.value[0] : null)

const scoreLevel = computed(() => {
  if (!latestResult.value) return ''
  const s = latestResult.value.cost_efficiency_score
  if (s >= 80) return 'score-good'
  if (s >= 60) return 'score-ok'
  return 'score-poor'
})

const scoreColor = computed(() => {
  if (!latestResult.value) return '#909399'
  const s = latestResult.value.cost_efficiency_score
  if (s >= 80) return '#67c23a'
  if (s >= 60) return '#e6a23c'
  return '#f56c6c'
})

function formatMoney(v: number) {
  if (v == null) return '0.00'
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function dimTagType(dim: string) {
  const map: Record<string, string> = { material: 'primary', labor: 'success', overhead: 'warning' }
  return map[dim] || 'info'
}

function dimLabel(dim: string) {
  const map: Record<string, string> = { material: '物料', labor: '人工', overhead: '费用' }
  return map[dim] || dim
}

function triggerLabel(src: string) {
  const map: Record<string, string> = { manual: '手动', eco_effective: 'ECO生效', auto: '自动' }
  return map[src] || src
}

async function fetchHistory() {
  if (!props.productPlanId) return
  loading.value = true
  try {
    const res = await getRecalcResultsByPlan(props.productPlanId, 5)
    const data = (res as any).data || []
    recalcHistory.value = data
    noCapacity.value = data.length > 0 && data[0].status === 'skipped'
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

async function handleRunRecalc() {
  if (!props.productPlanId) {
    ElMessage.warning('请先选择产品策划')
    return
  }
  running.value = true
  try {
    const res = await triggerRecalculation({
      product_plan_id: props.productPlanId,
      period_id: props.periodId,
      sheet_id: props.sheetId,
    })
    const data = (res as any).data || res
    if (data.status === 'skipped') {
      if (data.reason?.includes('无冷量参数')) {
        noCapacity.value = true
        ElMessage.warning('产品无冷量参数，请在立项中配置主销容量')
      } else if (data.reason?.includes('冷量段单价未配置')) {
        ElMessage.warning('请先配置冷量段单价')
      } else {
        ElMessage.info('跳过重算: ' + (data.reason || ''))
      }
    } else if (data.status === 'completed') {
      ElMessage.success('重算完成！效率评分: ' + data.data?.cost_efficiency_score)
    }
    await fetchHistory()
  } catch (e: any) {
    ElMessage.error('重算失败: ' + (e.response?.data?.detail || e.message || ''))
  } finally {
    running.value = false
  }
}

onMounted(fetchHistory)
watch(() => props.productPlanId, fetchHistory)
</script>

<style scoped>
.recalc-panel {
  margin-top: 8px;
}
.recalc-actions {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.hint {
  color: #909399;
  font-size: 12px;
}
.mb-16 {
  margin-bottom: 16px;
}
.recalc-history h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: #303133;
}
.result-card {
  background: #fafafa;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 20px;
}
.result-card.score-good { border-left: 4px solid #67c23a; }
.result-card.score-ok { border-left: 4px solid #e6a23c; }
.result-card.score-poor { border-left: 4px solid #f56c6c; }
.metric {
  text-align: center;
  padding: 8px 0;
}
.metric .label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}
.metric .value {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.metric .value.large {
  font-size: 28px;
}
.metric .sub {
  font-size: 11px;
  color: #909399;
}
.variance-row {
  margin-bottom: 12px;
}
.variance-item {
  text-align: center;
  padding: 8px;
  background: #fff;
  border-radius: 4px;
}
.dim-label {
  font-size: 12px;
  color: #909399;
  display: block;
  margin-bottom: 4px;
}
.dim-value {
  font-size: 16px;
  font-weight: 600;
}
.mono {
  font-family: 'Courier New', Courier, monospace;
}
.over { color: #f56c6c; }
.under { color: #67c23a; }
.detail-table {
  margin-top: 12px;
}
.recalc-time {
  margin-top: 8px;
  font-size: 12px;
  color: #c0c4cc;
  text-align: right;
}
</style>
