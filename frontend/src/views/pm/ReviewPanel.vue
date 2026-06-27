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

    <!-- D4-2: 自动计算偏差区域 -->
    <el-divider content-position="left">自动计算偏差 <el-tag size="small" type="info" effect="plain">D4-2</el-tag></el-divider>

    <el-row :gutter="16">
      <!-- 成本偏差 -->
      <el-col :span="8">
        <el-form-item label="成本偏差(%)">
          <div v-if="!manualOverride" class="auto-field-wrapper">
            <el-input
              :model-value="displayCostVariance"
              disabled
              :class="['auto-field-input', autoVariance.has_project_data ? 'auto-calculated' : 'awaiting-data']"
            >
              <template #suffix>
                <span v-if="autoVariance.has_project_data" class="auto-badge" title="由项目数据自动生成">自动</span>
                <span v-else class="awaiting-badge" title="等待项目数据">等待</span>
              </template>
            </el-input>
          </div>
          <el-input-number v-else v-model="reviewForm.cost_variance_pct" :precision="2" :step="0.1" style="width:100%" />
        </el-form-item>
      </el-col>

      <!-- 进度偏差 -->
      <el-col :span="8">
        <el-form-item label="进度偏差(天)">
          <div v-if="!manualOverride" class="auto-field-wrapper">
            <el-input
              :model-value="displayScheduleVariance"
              disabled
              :class="['auto-field-input', autoVariance.has_project_data ? 'auto-calculated' : 'awaiting-data']"
            >
              <template #suffix>
                <span v-if="autoVariance.has_project_data" class="auto-badge" title="由项目数据自动生成">自动</span>
                <span v-else class="awaiting-badge" title="等待项目数据">等待</span>
              </template>
            </el-input>
          </div>
          <el-input-number v-else v-model="reviewForm.schedule_variance_days" :precision="0" :step="1" style="width:100%" />
        </el-form-item>
      </el-col>

      <!-- 手动覆盖开关 -->
      <el-col :span="8">
        <el-form-item label="手动覆盖">
          <el-switch
            v-model="manualOverride"
            active-text="启用"
            inactive-text="关闭"
            @change="onManualOverrideChange"
          />
          <div v-if="manualOverride" style="font-size:12px;color:#e6a23c;margin-top:4px">
            ⚠️ 开启后偏差值由您手动输入
          </div>
        </el-form-item>
      </el-col>
    </el-row>

    <!-- 数据来源说明 -->
    <el-alert
      v-if="!manualOverride && autoVariance.has_project_data"
      title="偏差值由项目数据自动计算生成，如需手动输入请开启上方「手动覆盖」开关"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom:16px"
    />
    <el-alert
      v-else-if="!manualOverride && !autoVariance.has_project_data"
      title="暂无项目数据，偏差值将在关联项目数据录入后自动计算"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom:16px"
    />

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

  <!-- ========== D4-4 改进任务 ========== -->
  <el-divider content-position="left">🎯 改进任务</el-divider>
  <div style="margin-bottom:12px">
    <el-button size="small" type="primary" @click="showTaskDialog = true" :disabled="!reviewData?.id">+ 添加任务</el-button>
    <span v-if="!reviewData?.id" style="margin-left:8px;font-size:12px;color:#909399">请先提交复盘后再添加改进任务</span>
  </div>
  <el-table v-if="taskList.length > 0" :data="taskList" stripe border size="small" empty-text="暂无改进任务">
    <el-table-column label="描述" min-width="200">
      <template #default="{ row }">
        <span :class="{ 'task-completed': row.status === 'resolved' || row.status === 'closed' }">{{ row.description }}</span>
      </template>
    </el-table-column>
    <el-table-column label="负责人" width="100">
      <template #default="{ row }">
        <span :class="{ 'task-completed': row.status === 'resolved' || row.status === 'closed' }">{{ row.assigned_to || '—' }}</span>
      </template>
    </el-table-column>
    <el-table-column label="优先级" width="100">
      <template #default="{ row }">
        <el-tag
          :type="priorityTagType(row.priority)"
          size="small"
          :class="{ 'task-completed': row.status === 'resolved' || row.status === 'closed' }"
        >
          {{ priorityLabel(row.priority) }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="截止日期" width="120">
      <template #default="{ row }">
        <span :class="{ 'task-completed': row.status === 'resolved' || row.status === 'closed' }">{{ row.due_date || '—' }}</span>
      </template>
    </el-table-column>
    <el-table-column label="状态" width="140">
      <template #default="{ row }">
        <el-select
          v-model="row.status"
          size="small"
          :class="{ 'task-status-select': true, 'task-completed': row.status === 'resolved' || row.status === 'closed' }"
          @change="(val: string) => onChangeTaskStatus(row, val)"
        >
          <el-option label="待处理" value="open" />
          <el-option label="进行中" value="in_progress" />
          <el-option label="已解决" value="resolved" />
          <el-option label="已关闭" value="closed" />
        </el-select>
      </template>
    </el-table-column>
  </el-table>
  <div v-else style="text-align:center;padding:24px 0;color:#909399;font-size:13px">
    暂无改进任务。复盘问题点可在此转为改进任务跟踪闭环。
  </div>

  <!-- 添加任务弹窗 -->
  <el-dialog v-model="showTaskDialog" title="添加改进任务" width="500px" :close-on-click-modal="false">
    <el-form :model="taskForm" label-width="80" size="small">
      <el-form-item label="问题描述" required>
        <el-input v-model="taskForm.description" type="textarea" :rows="3" placeholder="描述复盘发现的问题点..." />
      </el-form-item>
      <el-form-item label="负责人">
        <el-input v-model="taskForm.assigned_to" placeholder="用户名" />
      </el-form-item>
      <el-form-item label="优先级">
        <el-select v-model="taskForm.priority" style="width:100%">
          <el-option label="高" value="high" />
          <el-option label="中" value="medium" />
          <el-option label="低" value="low" />
        </el-select>
      </el-form-item>
      <el-form-item label="截止日期">
        <el-date-picker v-model="taskForm.due_date" type="date" placeholder="选择截止日期" value-format="YYYY-MM-DD" style="width:100%" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showTaskDialog = false">取消</el-button>
      <el-button type="primary" @click="submitTask" :loading="savingTask">提交</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as planAPI from '../../api/productPlan'
import type {
  ReviewData, KnowledgeItem, ReviewTemplateItem, TemplateField,
  AutoVarianceData, ImprovementTaskItem, CreateImprovementTaskPayload,
} from '../../api/productPlan'

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
  cost_variance_pct: null as number | null,
  actual_launch_date: '',
  schedule_variance_days: null as number | null,
  market_feedback: '',
  lessons_learned: '',
  rating: 0,
})
const savingReview = ref(false)

// ── D4-2: 自动计算偏差 ──
const autoVariance = reactive<AutoVarianceData>({
  cost_variance_pct: null,
  schedule_variance_days: null,
  has_project_data: false,
  target_cost_total: null,
  actual_cost_total: null,
  planned_launch_date: null,
  actual_launch_date: null,
})
const manualOverride = ref(false)

/** 展示成本偏差 — 优先显示自动计算值 */
const displayCostVariance = computed(() => {
  if (manualOverride.value) return reviewForm.cost_variance_pct
  if (autoVariance.cost_variance_pct != null) {
    const pct = autoVariance.cost_variance_pct
    if (pct > 0) return `+${pct.toFixed(2)}%`
    if (pct < 0) return `${pct.toFixed(2)}%`
    return '0.00%'
  }
  return autoVariance.has_project_data ? '—' : '等待项目数据'
})

/** 展示进度偏差 — 优先显示自动计算值 */
const displayScheduleVariance = computed(() => {
  if (manualOverride.value) return reviewForm.schedule_variance_days
  if (autoVariance.schedule_variance_days != null) {
    const days = autoVariance.schedule_variance_days
    if (days > 0) return `延迟 ${days} 天`
    if (days < 0) return `提前 ${Math.abs(days)} 天`
    return '准时'
  }
  return autoVariance.has_project_data ? '—' : '等待项目数据'
})

/** 手动覆盖开关变化时，将自动计算值填入表单 */
function onManualOverrideChange(val: boolean) {
  if (val) {
    // 开启手动覆盖时，将自动计算值拷贝到表单
    if (autoVariance.cost_variance_pct != null) {
      reviewForm.cost_variance_pct = autoVariance.cost_variance_pct
    }
    if (autoVariance.schedule_variance_days != null) {
      reviewForm.schedule_variance_days = autoVariance.schedule_variance_days
    }
  } else {
    // 关闭手动覆盖时，清除手动输入值
    reviewForm.cost_variance_pct = null
    reviewForm.schedule_variance_days = null
  }
}

/** 获取自动计算的偏差值 */
async function fetchAutoVariance() {
  try {
    const res = await planAPI.getAutoVariance(props.planId)
    if (res.data) {
      Object.assign(autoVariance, res.data)
    }
  } catch {
    // 静默处理 — 自动计算失败不影响其他功能
  }
}

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

      // D4-2: 处理自动计算偏差的回显
      if (res.data.cost_variance_pct_auto != null) {
        autoVariance.cost_variance_pct = res.data.cost_variance_pct_auto
      }
      if (res.data.schedule_variance_days_auto != null) {
        autoVariance.schedule_variance_days = res.data.schedule_variance_days_auto
      }
      // 如果已经有手动输入的偏差值，开启手动覆盖
      if (res.data.cost_variance_source === 'manual' && res.data.cost_variance_pct != null) {
        manualOverride.value = true
        reviewForm.cost_variance_pct = res.data.cost_variance_pct
      }
      if (res.data.schedule_variance_source === 'manual' && res.data.schedule_variance_days != null) {
        reviewForm.schedule_variance_days = res.data.schedule_variance_days
      }

      emit('review-changed', true)
    }
    // 加载改进任务（依赖 reviewData）
    await fetchTasks()
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
      // D4-2: 手动覆盖标记
      manual_override: manualOverride.value || undefined,
    }
    // D4-2: 手动覆盖模式下，发送偏差值
    if (manualOverride.value) {
      payload.cost_variance_pct = reviewForm.cost_variance_pct ?? undefined
      payload.schedule_variance_days = reviewForm.schedule_variance_days ?? undefined
    }

    if (reviewData.value?.id) {
      await planAPI.updateReview(props.planId, payload)
      ElMessage.success('复盘更新成功')
    } else {
      await planAPI.submitReview(props.planId, payload)
      ElMessage.success('复盘提交成功')
    }
    await fetchReview()
    await fetchAutoVariance()
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

// ── 改进任务（D4-4） ──
const taskList = ref<ImprovementTaskItem[]>([])
const showTaskDialog = ref(false)
const savingTask = ref(false)
const taskForm = reactive<CreateImprovementTaskPayload>({
  description: '',
  assigned_to: '',
  priority: 'medium',
  due_date: '',
})

function priorityTagType(p: string): string {
  if (p === 'high') return 'danger'
  if (p === 'low') return 'info'
  return 'warning'
}

function priorityLabel(p: string): string {
  if (p === 'high') return '高'
  if (p === 'medium') return '中'
  if (p === 'low') return '低'
  return p
}

/** 获取改进任务列表（需要 reviewId） */
async function fetchTasks() {
  const reviewId = reviewData.value?.id
  if (!reviewId) {
    taskList.value = []
    return
  }
  try {
    const res = await planAPI.listImprovementTasks(reviewId)
    const result = res.data as { items: ImprovementTaskItem[]; total: number } | undefined
    taskList.value = result?.items ?? []
  } catch {
    taskList.value = []
  }
}

/** 提交新改进任务 */
async function submitTask() {
  if (!taskForm.description.trim()) {
    ElMessage.warning('请填写问题描述')
    return
  }
  const reviewId = reviewData.value?.id
  if (!reviewId) {
    ElMessage.warning('请先提交复盘')
    return
  }
  savingTask.value = true
  try {
    const payload: CreateImprovementTaskPayload = {
      description: taskForm.description.trim(),
      assigned_to: taskForm.assigned_to?.trim() || undefined,
      priority: taskForm.priority || 'medium',
      due_date: taskForm.due_date || undefined,
    }
    await planAPI.createImprovementTask(reviewId, payload)
    ElMessage.success('改进任务创建成功')
    showTaskDialog.value = false
    taskForm.description = ''
    taskForm.assigned_to = ''
    taskForm.priority = 'medium'
    taskForm.due_date = ''
    await fetchTasks()
  } catch (e: unknown) {
    const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
    ElMessage.error(_err || '创建任务失败')
  } finally {
    savingTask.value = false
  }
}

/** 改进任务状态变更 */
async function onChangeTaskStatus(row: ImprovementTaskItem, newStatus: string) {
  const prevStatus = row.status
  try {
    await planAPI.updateImprovementTask(row.id, { status: newStatus })
    ElMessage.success(`状态已更新为: ${['待处理', '进行中', '已解决', '已关闭'][['open', 'in_progress', 'resolved', 'closed'].indexOf(newStatus)] || newStatus}`)
    await fetchTasks()
  } catch {
    row.status = prevStatus
    ElMessage.error('状态更新失败')
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
    fetchAutoVariance(),
    fetchKnowledge(),
    fetchTemplates(),
  ])
})
</script>

<style scoped>
.knowledge-summary { color: #606266; font-size: 12px; line-height: 1.5; }

/* D4-2: 自动计算字段样式 */
.auto-field-wrapper {
  width: 100%;
}
.auto-field-input :deep(.el-input__wrapper) {
  background-color: #f5f7fa;
}
.auto-field-input.auto-calculated :deep(.el-input__wrapper) {
  background-color: #f0f9eb;
  border-color: #c2e7b0;
}
.auto-field-input.awaiting-data :deep(.el-input__wrapper) {
  background-color: #fdf6ec;
  border-color: #e6a23c;
}
.auto-field-input :deep(.el-input__inner) {
  color: #606266;
  font-weight: 500;
  cursor: default;
}
.auto-badge {
  display: inline-block;
  background: #67c23a;
  color: #fff;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  line-height: 1.6;
  white-space: nowrap;
}
.awaiting-badge {
  display: inline-block;
  background: #e6a23c;
  color: #fff;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  line-height: 1.6;
  white-space: nowrap;
}

/* D4-4: 改进任务完成态 */
.task-completed {
  text-decoration: line-through;
  color: #c0c4cc !important;
}
.task-status-select :deep(.el-input__wrapper) {
  background: transparent;
}
</style>
