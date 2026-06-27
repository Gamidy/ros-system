<template>
  <!-- 已上市但无复盘的醒目提示 -->
  <el-alert
    v-if="planStatus === 'released' && !reviewData?.id"
    title="⚠️ 该策划已「发布」，但尚未完成复盘"
    type="warning"
    :closable="false"
    show-icon
    style="margin-bottom:16px"
    description="请尽快补充复盘数据，完成产品全生命周期闭环。"
  />

  <!-- 模板选择器 -->
  <el-form label-width="160" size="small" style="margin-bottom:12px">
    <el-form-item label="复盘模板">
      <el-select
        v-model="selectedTemplateId"
        placeholder="选择模板（可选）"
        clearable
        style="width:100%"
        @change="onTemplateChange"
      >
        <el-option
          v-for="tpl in templateOptions"
          :key="tpl.id"
          :label="tpl.name"
          :value="tpl.id"
        />
      </el-select>
      <div v-if="selectedTemplateId && currentTemplate" style="margin-top:4px;font-size:12px;color:#909399">
        已选模板：{{ currentTemplate.name }}（{{ currentTemplate.product_type }}）
        <el-tag size="small" type="info" style="margin-left:4px">{{ currentTemplate.template_fields.length }}个字段</el-tag>
      </div>
    </el-form-item>
  </el-form>

  <el-form :model="reviewForm" label-width="160" size="small">
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item :label="fieldLabel('review_date', '复盘日期')">
          <el-date-picker v-model="reviewForm.review_date" type="date" placeholder="选择复盘日期" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item :label="fieldLabel('actual_cost_total', '实际成本总计')">
          <el-input-number v-model="reviewForm.actual_cost_total" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item :label="fieldLabel('actual_launch_date', '实际上市日期')">
          <el-date-picker v-model="reviewForm.actual_launch_date" type="date" placeholder="选择实际上市日期" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
      </el-col>
    </el-row>

    <el-form-item :label="fieldLabel('market_feedback', '市场反馈')">
      <el-input v-model="reviewForm.market_feedback" type="textarea" :rows="3" placeholder="市场反馈信息" />
    </el-form-item>
    <el-form-item :label="fieldLabel('lessons_learned', '经验教训')">
      <el-input v-model="reviewForm.lessons_learned" type="textarea" :rows="3" placeholder="总结的经验教训" />
    </el-form-item>
    <el-form-item :label="fieldLabel('rating', '综合评分')">
      <el-rate v-model="reviewForm.rating" :max="5" show-text :texts="['很差', '较差', '一般', '较好', '很好']" />
    </el-form-item>
    <el-form-item>
      <el-button type="primary" size="small" @click="saveReview" :loading="savingReview">
        {{ reviewData?.id ? '更新复盘' : '提交复盘' }}
      </el-button>
      <el-button v-if="reviewData?.id" size="small" @click="resetReviewForm">重置</el-button>
    </el-form-item>
  </el-form>

  <!-- 成本对比 -->
  <el-divider content-position="left">成本对比</el-divider>
  <el-descriptions :column="3" border size="small" style="margin-bottom:16px">
    <el-descriptions-item label="目标成本总计">
      <span style="font-weight:600">{{ formatCost(totalTargetCost) }}</span>
    </el-descriptions-item>
    <el-descriptions-item label="实际成本总计">
      <span style="font-weight:600">{{ reviewForm.actual_cost_total != null ? formatCost(reviewForm.actual_cost_total) : '待填写' }}</span>
    </el-descriptions-item>
    <el-descriptions-item label="偏差">
      <el-tag :type="costDeviationType" size="small">
        {{ costDeviationLabel }}
      </el-tag>
    </el-descriptions-item>
  </el-descriptions>

  <!-- 上市日期对比 -->
  <el-divider content-position="left">上市日期对比</el-divider>
  <el-descriptions :column="3" border size="small" style="margin-bottom:16px">
    <el-descriptions-item label="计划上市日期">
      <span>{{ plannedLaunchDate || '未设定' }}</span>
    </el-descriptions-item>
    <el-descriptions-item label="实际上市日期">
      <span>{{ reviewForm.actual_launch_date || '待填写' }}</span>
    </el-descriptions-item>
    <el-descriptions-item label="偏差天数">
      <el-tag :type="launchDeviationType" size="small">
        {{ launchDeviationLabel }}
      </el-tag>
    </el-descriptions-item>
  </el-descriptions>

  <!-- ========== P5 知识沉淀 ========== -->
  <el-divider content-position="left">📚 知识沉淀</el-divider>
  <div style="margin-bottom:12px">
    <el-button size="small" type="primary" @click="showKnowledgeDialog = true">+ 沉淀经验到知识库</el-button>
  </div>
  <div v-if="knowledgeList.length === 0" style="text-align:center;padding:24px 0;color:#909399;font-size:13px">
    暂无关联知识。点击上方按钮将复盘经验沉淀到知识库。
  </div>
  <el-table v-else :data="knowledgeList" stripe border size="small" empty-text="暂无关联知识">
    <el-table-column prop="title" label="知识标题" min-width="160">
      <template #default="{ row }">
        <el-link type="primary" @click="goToKnowledge(row)">{{ row.title }}</el-link>
      </template>
    </el-table-column>
    <el-table-column prop="category" label="分类" width="120">
      <template #default="{ row }"><el-tag size="small">{{ row.category }}</el-tag></template>
    </el-table-column>
    <el-table-column prop="content" label="内容摘要" min-width="240">
      <template #default="{ row }">
        <span class="knowledge-summary">{{ row.content?.substring(0, 80) }}{{ row.content?.length > 80 ? '...' : '' }}</span>
      </template>
    </el-table-column>
    <el-table-column prop="created_by" label="创建人" width="100" />
    <el-table-column prop="created_at" label="创建时间" width="160" />
  </el-table>

  <!-- 知识沉淀弹窗 -->
  <el-dialog v-model="showKnowledgeDialog" title="沉淀经验到知识库" width="550px" :close-on-click-modal="false">
    <el-form :model="knowledgeForm" label-width="80" size="small">
      <el-form-item label="标题"><el-input v-model="knowledgeForm.title" placeholder="知识标题" /></el-form-item>
      <el-form-item label="分类">
        <el-select v-model="knowledgeForm.category" placeholder="选择分类" style="width:100%">
          <el-option label="项目经验" value="项目经验" />
          <el-option label="技术方案" value="技术方案" />
          <el-option label="市场洞察" value="市场洞察" />
          <el-option label="成本控制" value="成本控制" />
          <el-option label="质量改进" value="质量改进" />
          <el-option label="流程优化" value="流程优化" />
          <el-option label="其他" value="其他" />
        </el-select>
      </el-form-item>
      <el-form-item label="内容"><el-input v-model="knowledgeForm.content" type="textarea" :rows="5" placeholder="详细描述经验内容..." /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showKnowledgeDialog = false">取消</el-button>
      <el-button type="primary" @click="submitKnowledge" :loading="savingKnowledge">提交</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as planAPI from '../../api/productPlan'
import type { ReviewData, KnowledgeItem, ReviewTemplateItem, TemplateField } from '../../api/productPlan'

const props = defineProps<{
  planId: string
  planStatus: string
  plannedLaunchDate?: string
  totalTargetCost: number
  productType?: string
}>()

const emit = defineEmits<{
  refresh: []
  'review-changed': [value: boolean]
}>()

// ── 复盘 ──
const reviewData = ref<ReviewData | null>(null)
const reviewForm = reactive({
  review_date: '',
  actual_cost_total: null as number | null,
  actual_launch_date: '',
  market_feedback: '',
  lessons_learned: '',
  rating: 0,
})
const savingReview = ref(false)

// ── 复盘模板 ──
const templateOptions = ref<ReviewTemplateItem[]>([])
const selectedTemplateId = ref<string>('')
const currentTemplate = computed<ReviewTemplateItem | undefined>(() => {
  if (!selectedTemplateId.value) return undefined
  return templateOptions.value.find(t => t.id === selectedTemplateId.value)
})

/** 字段名映射：前端 form key → 后端 field name */
const FIELD_MAP: Record<string, string> = {
  review_date: 'review_date',
  actual_cost_total: 'actual_cost_total',
  actual_launch_date: 'actual_launch_date',
  market_feedback: 'market_feedback',
  lessons_learned: 'lessons_learned',
  rating: 'rating',
}

/** 从模板中查找字段配置，若匹配则返回 label，否则返回默认 label */
function fieldLabel(fieldKey: string, defaultLabel: string): string {
  if (!currentTemplate.value) return defaultLabel
  const config = currentTemplate.value.template_fields.find((tf: TemplateField) => tf.field === FIELD_MAP[fieldKey] || tf.field === fieldKey)
  if (!config) return defaultLabel
  return config.required ? `${config.label} *` : config.label
}

async function fetchTemplates() {
  try {
    const res = await planAPI.listReviewTemplates(props.productType)
    templateOptions.value = (res.data || []) as ReviewTemplateItem[]
  } catch {
    templateOptions.value = []
  }
}

function onTemplateChange(val: string) {
  if (!val) return
  // 模板选择后无需额外操作，fieldLabel 会基于 currentTemplate 自动更新
}

async function fetchReview() {
  try {
    const res = await planAPI.getReview(props.planId)
    if (res.data) {
      reviewData.value = res.data
      reviewForm.review_date = res.data.review_date || ''
      reviewForm.actual_cost_total = res.data.actual_cost_total ?? null
      reviewForm.actual_launch_date = res.data.actual_launch_date || ''
      reviewForm.market_feedback = res.data.market_feedback || ''
      reviewForm.lessons_learned = res.data.lessons_learned || ''
      reviewForm.rating = res.data.rating || 0
      selectedTemplateId.value = res.data.review_template_id || ''
      emit('review-changed', true)
    }
  } catch {
    // 404 = 无复盘数据，不报错
    reviewData.value = null
    emit('review-changed', false)
  }
}

function resetReviewForm() {
  if (reviewData.value) {
    reviewForm.review_date = reviewData.value.review_date || ''
    reviewForm.actual_cost_total = reviewData.value.actual_cost_total ?? null
    reviewForm.actual_launch_date = reviewData.value.actual_launch_date || ''
    reviewForm.market_feedback = reviewData.value.market_feedback || ''
    reviewForm.lessons_learned = reviewData.value.lessons_learned || ''
    reviewForm.rating = reviewData.value.rating || 0
  } else {
    reviewForm.review_date = ''
    reviewForm.actual_cost_total = null
    reviewForm.actual_launch_date = ''
    reviewForm.market_feedback = ''
    reviewForm.lessons_learned = ''
    reviewForm.rating = 0
  }
}

async function saveReview() {
  savingReview.value = true
  try {
    const payload: ReviewData = {
      review_date: reviewForm.review_date || undefined,
      actual_cost_total: reviewForm.actual_cost_total ?? undefined,
      actual_launch_date: reviewForm.actual_launch_date || undefined,
      market_feedback: reviewForm.market_feedback || undefined,
      lessons_learned: reviewForm.lessons_learned || undefined,
      rating: reviewForm.rating || undefined,
      review_template_id: selectedTemplateId.value || undefined,
    }
    if (reviewData.value?.id) {
      await planAPI.updateReview(props.planId, payload)
      ElMessage.success('复盘更新成功')
    } else {
      await planAPI.submitReview(props.planId, payload)
      ElMessage.success('复盘提交成功')
    }
    await fetchReview()
    emit('refresh')
  } catch (e: unknown) {
    const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
    ElMessage.error(_err || '操作失败，请重试')
  } finally {
    savingReview.value = false
  }
}

// ── 知识沉淀 ──
const knowledgeList = ref<KnowledgeItem[]>([])
const showKnowledgeDialog = ref(false)
const savingKnowledge = ref(false)
const knowledgeForm = reactive({
  title: '',
  category: '',
  content: '',
})

async function fetchKnowledge() {
  try {
    const res = await planAPI.listPlanKnowledge(props.planId)
    knowledgeList.value = res.data || []
  } catch {
    knowledgeList.value = []
  }
}

async function submitKnowledge() {
  if (!knowledgeForm.title || !knowledgeForm.content) {
    ElMessage.warning('请填写标题和内容')
    return
  }
  savingKnowledge.value = true
  try {
    const payload: Record<string, unknown> = {
      title: knowledgeForm.title,
      category: knowledgeForm.category || '其他',
      content: knowledgeForm.content,
      source_type: 'product_plan',
      source_id: props.planId,
    }
    await planAPI.createKnowledge(payload)
    ElMessage.success('知识沉淀成功')
    showKnowledgeDialog.value = false
    knowledgeForm.title = ''
    knowledgeForm.category = ''
    knowledgeForm.content = ''
    await fetchKnowledge()
  } catch (e: unknown) {
    const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
    ElMessage.error(_err || '操作失败，请重试')
  } finally {
    savingKnowledge.value = false
  }
}

function goToKnowledge(row: KnowledgeItem) {
  ElMessage.info(`知识: ${row.title}`)
}

// ── 复盘对比计算 ──
function formatCost(val: number): string {
  return `¥${val.toLocaleString('zh-CN')}`
}

const costDeviationType = computed(() => {
  const target = props.totalTargetCost
  const actual = reviewForm.actual_cost_total
  if (target === 0 || actual == null) return 'info'
  if (actual > target * 1.05) return 'danger'
  if (actual < target * 0.95) return 'success'
  return 'warning'
})

const costDeviationLabel = computed(() => {
  const target = props.totalTargetCost
  const actual = reviewForm.actual_cost_total
  if (target === 0 && (actual == null || actual === 0)) return '无数据'
  if (target === 0) return '目标未设定'
  if (actual == null) return '待填写实际成本'
  const pct = ((actual - target) / target * 100).toFixed(1)
  if (actual > target) return `超支 ${pct}%`
  if (actual < target) return `节省 ${Math.abs(Number(pct))}%`
  return '持平'
})

const launchDeviationType = computed(() => {
  const planned = props.plannedLaunchDate
  const actual = reviewForm.actual_launch_date
  if (!planned || !actual) return 'info'
  const days = Math.round((new Date(actual).getTime() - new Date(planned).getTime()) / (1000 * 60 * 60 * 24))
  if (days > 7) return 'danger'
  if (days < -7) return 'success'
  if (days === 0) return 'success'
  return 'warning'
})

const launchDeviationLabel = computed(() => {
  const planned = props.plannedLaunchDate
  const actual = reviewForm.actual_launch_date
  if (!planned && !actual) return '无数据'
  if (!planned) return '计划日未设定'
  if (!actual) return '待填写实际日期'
  const days = Math.round((new Date(actual).getTime() - new Date(planned).getTime()) / (1000 * 60 * 60 * 24))
  if (days > 0) return `延迟 ${days} 天`
  if (days < 0) return `提前 ${Math.abs(days)} 天`
  return '准时上市'
})

onMounted(async () => {
  await Promise.all([
    fetchReview(),
    fetchKnowledge(),
    fetchTemplates(),
  ])
})
</script>

<style scoped>
.knowledge-summary { color: #606266; font-size: 12px; line-height: 1.5; }
</style>
