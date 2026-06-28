<template>
  <el-form label-width="120px" label-position="top">
    <el-form-item label="项目名称">
      <el-input v-model="data.name" placeholder="输入项目名称" @input="onFieldChange('name')" />
    </el-form-item>
    <el-form-item label="背景与依据">
      <el-input v-model="data.background_basis" type="textarea" :rows="3" @input="onFieldChange('background_basis')" />
    </el-form-item>
    <el-form-item label="市场需求概述">
      <el-input v-model="data.market_demand_overview" type="textarea" :rows="3" @input="onFieldChange('market_demand_overview')" />
    </el-form-item>
    <el-form-item label="竞品分析">
      <el-input v-model="data.competitor_analysis" type="textarea" :rows="3" @input="onFieldChange('competitor_analysis')" />
    </el-form-item>
    <el-form-item label="总体目标">
      <el-input v-model="data.overall_goal" type="textarea" :rows="3" @input="onFieldChange('overall_goal')" />
    </el-form-item>
    <el-form-item label="技术目标">
      <el-input v-model="data.tech_goal" type="textarea" :rows="2" @input="onFieldChange('tech_goal')" />
    </el-form-item>
    <el-form-item label="成本目标">
      <el-input v-model="data.cost_goal" type="textarea" :rows="2" @input="onFieldChange('cost_goal')" />
    </el-form-item>
    <el-form-item label="销售目标">
      <el-input v-model="data.sales_goal" type="textarea" :rows="2" @input="onFieldChange('sales_goal')" />
    </el-form-item>
    <el-form-item label="交付物">
      <el-input v-model="data.deliverables" type="textarea" :rows="2" @input="onFieldChange('deliverables')" />
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type { ProposalForm } from '../ProductProposalForm.vue'

const props = defineProps({
  data: { type: Object as PropType<ProposalForm>, required: true },
})
const emit = defineEmits<{ update: [patch: Partial<ProposalForm>] }>()

function onFieldChange(field: keyof ProposalForm) {
  emit('update', { [field]: props.data[field] })
}
</script>
