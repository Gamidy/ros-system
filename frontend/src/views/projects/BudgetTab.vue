<template>
  <div class="budget-tab">
    <div class="budget-header" v-if="project">
      <div class="budget-summary">
        <div class="budget-card total">
          <div class="b-label">项目预算</div>
          <div class="b-value">{{ formatMoney(project.budget) }}</div>
        </div>
        <div class="budget-card actual">
          <div class="b-label">已花费(估算)</div>
          <div class="b-value">{{ formatMoney(estimatedCost) }}</div>
        </div>
        <div class="budget-card remain" :class="budgetRemain < 0 ? 'over' : 'safe'">
          <div class="b-label">{{ budgetRemain >= 0 ? '剩余预算' : '超支' }}</div>
          <div class="b-value">{{ formatMoney(Math.abs(budgetRemain)) }}</div>
        </div>
      </div>
      <el-progress
        :percentage="budgetPct"
        :stroke-width="12"
        :color="budgetPct > 90 ? '#f56c6c' : budgetPct > 70 ? '#e6a23c' : '#67c23a'"
        :format="() => budgetPct + '%'"
        style="margin-top:12px"
      />
    </div>
    <el-empty v-else description="暂无数��" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ project: any }>()

const project = computed(() => props.project)
const estimatedCost = computed(() => {
  if (!project.value?.budget) return 0
  // Simple estimation: if project is more than 50% done, show 60% spent
  return Math.round(project.value.budget * 0.4)
})
const budgetRemain = computed(() => (project.value?.budget || 0) - estimatedCost.value)
const budgetPct = computed(() => {
  if (!project.value?.budget || project.value.budget === 0) return 0
  return Math.min(100, Math.round(estimatedCost.value / project.value.budget * 100))
})

function formatMoney(v: number | null | undefined): string {
  if (!v) return '¥0'
  if (v >= 10000) return `¥${(v / 10000).toFixed(1)}万`
  return `¥${v.toLocaleString()}`
}
</script>

<style scoped>
.budget-tab { padding: 8px 0; }
.budget-header { max-width: 500px; }
.budget-summary { display: flex; gap: 16px; }
.budget-card { flex: 1; padding: 16px; border-radius: 8px; text-align: center; }
.budget-card.total { background: #e6f7ff; }
.budget-card.actual { background: #fff7e6; }
.budget-card.remain { background: #f6ffed; }
.budget-card.remain.over { background: #fff1f0; }
.b-label { font-size: 12px; color: #909399; margin-bottom: 4px; }
.b-value { font-size: 20px; font-weight: 700; color: #303133; }
.over .b-value { color: #f56c6c; }
</style>
