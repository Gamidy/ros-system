<template>
  <div class="product-proposal-form">
    <div class="page-header">
      <h2>📝 产品立项</h2>
      <el-button @click="$router.push('/proposals')">← 返回列表</el-button>
    </div>
    <el-card shadow="never">
      <el-tabs v-model="activeTab" type="border-card">
        <el-tab-pane label="项目概述与市场" name="overview">
          <OverviewMarketTab :data="formData" @update="handleUpdate" />
        </el-tab-pane>
        <el-tab-pane label="技术要求" name="tech">
          <TechSpecTab :data="formData" @update="handleUpdate" />
        </el-tab-pane>
        <el-tab-pane label="成本核算" name="cost">
          <CostTab :data="formData" @update="handleUpdate" />
        </el-tab-pane>
        <el-tab-pane label="团队与职责" name="team">
          <TeamTab :data="formData" @update="handleUpdate" />
        </el-tab-pane>
      </el-tabs>
      <div class="form-actions">
        <el-button @click="saveDraft" :loading="saving" type="default">保存草稿</el-button>
        <el-button @click="submitApproval" :loading="submitting" type="primary">提交审批</el-button>
      </div>
    </el-card>
  </div>
</template>

<!-- TypeScript export block (non-setup) for type imports from child components -->
<script lang="ts">
export interface ProposalForm {
  name: string
  background_basis: string
  market_demand_overview: string
  competitor_analysis: string
  overall_goal: string
  tech_goal: string
  cost_goal: string
  sales_goal: string
  deliverables: string
  core_performance: string
  safety_compliance: string
  material_components: string
  accessory_config: string
  feature_config: string
  dev_cost_items: string
  mold_costs: string
  prototype_costs_detail: string
  test_costs: string
  labor_costs: string
  cert_costs: string
  team_members: string
}
</script>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../../../api'
import OverviewMarketTab from './tab/OverviewMarketTab.vue'
import TechSpecTab from './tab/TechSpecTab.vue'
import CostTab from './tab/CostTab.vue'
import TeamTab from './tab/TeamTab.vue'

const router = useRouter()
const route = useRoute()
const activeTab = ref('overview')
const saving = ref(false)
const submitting = ref(false)

const formData = reactive<ProposalForm>({
  name: '',
  background_basis: '',
  market_demand_overview: '',
  competitor_analysis: '',
  overall_goal: '',
  tech_goal: '',
  cost_goal: '',
  sales_goal: '',
  deliverables: '',
  core_performance: '',
  safety_compliance: '',
  material_components: '',
  accessory_config: '',
  feature_config: '',
  dev_cost_items: '',
  mold_costs: '',
  prototype_costs_detail: '',
  test_costs: '',
  labor_costs: '',
  cert_costs: '',
  team_members: '',
})

onMounted(async () => {
  const draftId = route.query.draft
  if (draftId) {
    try {
      const res = await api.get(`/pm/proposals/${draftId}`)
      if (res.data) Object.assign(formData, res.data)
    } catch (e: unknown) {
      ElMessage.warning('草稿加载失败')
    }
  }
})

function handleUpdate(patch: Partial<ProposalForm>) {
  Object.assign(formData, patch)
}

async function saveDraft() {
  saving.value = true
  try {
    await api.post('/pm/proposals', { ...formData, is_draft: true })
    ElMessage.success('草稿保存成功')
    router.push('/proposals')
  } catch (e: unknown) {
    // error handled by interceptor
  } finally {
    saving.value = false
  }
}

async function submitApproval() {
  submitting.value = true
  try {
    await api.post('/pm/proposals', { ...formData, is_draft: false })
    ElMessage.success('提案已提交审批')
    router.push('/proposals')
  } catch (e: unknown) {
    // error handled by interceptor
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.product-proposal-form {
  padding: 0;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}
.form-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}
</style>
