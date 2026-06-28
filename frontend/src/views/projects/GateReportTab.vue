<template>
  <div class="report-tab">
    <div class="report-header" v-if="project">
      <h3>{{ project.code }} {{ project.name }} — Gate 评审报告</h3>
      <el-button size="small" @click="print">打印</el-button>
    </div>

    <el-descriptions :column="2" border size="small" v-if="project" style="margin-bottom:16px">
      <el-descriptions-item label="项目等级"><el-tag :type="classTag" size="small">{{ project.project_class }}级</el-tag></el-descriptions-item>
      <el-descriptions-item label="状态">{{ statusLabel(project.status) }}</el-descriptions-item>
      <el-descriptions-item label="项目经理">{{ project.owner || '-' }}</el-descriptions-item>
      <el-descriptions-item label="截止日期">{{ project.target_end_date || '-' }}</el-descriptions-item>
      <el-descriptions-item label="预算">{{ project.budget ? '¥' + (project.budget/10000).toFixed(1) + '万' : '-' }}</el-descriptions-item>
    </el-descriptions>

    <el-table :data="gates" stripe border size="small" style="width:100%">
      <el-table-column prop="gate_code" label="Gate" width="60" />
      <el-table-column prop="gate_name" label="名称" min-width="120" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }"><el-tag :type="gateTag(row.status)" size="small">{{ gateLabel(row.status) }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="decision_level" label="决策层" width="90" />
      <el-table-column prop="planned_date" label="计划日期" width="100" />
      <el-table-column prop="actual_date" label="实际日期" width="100" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ project: any; gates: any[] }>()
const project = computed(() => props.project)
const gates = computed(() => props.gates || [])

function classTag() { return ({ T: 'danger', A: 'warning', B: 'success', C: 'info' } as Record<string, string>)[project.value?.project_class || ''] || 'info' }
function statusLabel(s: string) { return ({ planning: '规划中', running: '进行中', completed: '已完成', paused: '已暂停' })[s] || s }
function gateTag(s: string) { return ({ pending: 'info', passed: 'success', failed: 'danger', skipped: 'warning' })[s] || 'info' }
function gateLabel(s: string) { return ({ pending: '待定', passed: '通过', failed: '失败', skipped: '跳过' })[s] || s }
function print() { window.print() }
</script>

<style scoped>
.report-tab { width: 100%; }
.report-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.report-header h3 { margin: 0; font-size: 16px; }
@media print { .report-tab .el-button { display: none; } }
</style>
