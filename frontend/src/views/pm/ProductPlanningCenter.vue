<template>
  <div class="product-planning-center">
    <!-- ═══════════ 顶部标题 ═══════════ -->
    <div class="ppc-header">
      <h2>🧠 产品策划中心</h2>
      <div class="ppc-header-actions">
        <el-button type="primary" @click="showCreateDialog = true">+ 新建策划</el-button>
        <el-button @click="fetchPlans">刷新</el-button>
      </div>
    </div>

    <!-- ═══════════ 主体区 + 全局待办 ═══════════ -->
    <el-row :gutter="16">
      <el-col :xs="24" :md="18" :lg="18">
        <!-- ═══════════ 筛选栏 ═══════════ -->
        <div class="ppc-filters">
          <!-- 桌面端：正常两列布局 -->
          <el-row v-if="!isMobile" :gutter="12">
            <el-col :span="6">
              <el-select v-model="filterStatus" placeholder="按状态筛选" clearable size="small" style="width:100%" @change="fetchPlans">
                <el-option label="草稿" value="draft" />
                <el-option label="竞品分析" value="competitor" />
                <el-option label="产品定义" value="definition" />
                <el-option label="成本目标" value="costing" />
                <el-option label="技术方案" value="tech_input" />
                <el-option label="立项审批" value="project_init" />
                <el-option label="已批准" value="approved" />
                <el-option label="已发布" value="released" />
              </el-select>
            </el-col>
            <el-col :span="6">
              <el-input v-model="searchText" placeholder="搜索策划名称" size="small" clearable @change="fetchPlans" />
            </el-col>
          </el-row>
          <!-- 移动端：状态筛选 + 可折叠搜索 -->
          <div v-else class="mobile-filter-bar">
            <div class="mobile-filter-row">
              <el-select v-model="filterStatus" placeholder="状态" clearable size="small" style="width:110px" @change="fetchPlans">
                <el-option label="草稿" value="draft" />
                <el-option label="竞品分析" value="competitor" />
                <el-option label="产品定义" value="definition" />
                <el-option label="成本目标" value="costing" />
                <el-option label="技术方案" value="tech_input" />
                <el-option label="立项审批" value="project_init" />
                <el-option label="已批准" value="approved" />
                <el-option label="已发布" value="released" />
              </el-select>
              <el-button
                :icon="Search"
                circle
                size="small"
                @click="toggleSearch"
              />
            </div>
            <el-input
              v-if="searchExpanded"
              v-model="searchText"
              placeholder="搜索策划名称"
              size="small"
              clearable
              @change="fetchPlans"
              class="mobile-search-input"
            />
          </div>
        </div>

        <!-- ═══════════ 下一步动作引导 ═══════════ -->
        <el-card v-if="selectedPlanNextAction" shadow="never" class="next-action-card">
          <div class="next-action-header">
            <span class="next-action-label">下一步动作</span>
            <el-tag size="small" type="warning" effect="dark">{{ selectedPlanName }}</el-tag>
          </div>
          <div class="next-action-body">
            <el-steps :active="nextActionStepIndex" align-center finish-status="success" size="small">
              <el-step :title="selectedPlanNextAction.current_stage" />
              <el-step v-if="selectedPlanNextAction.next_stage" :title="selectedPlanNextAction.next_stage" />
            </el-steps>
            <div class="next-action-text">
              <el-alert
                :title="selectedPlanNextAction.next_action"
                :type="selectedPlanNextAction.can_advance ? 'success' : 'warning'"
                show-icon
                :closable="false"
              />
            </div>
            <div v-if="selectedPlanNextAction.missing_fields.length > 0" class="missing-fields">
              <div v-for="f in selectedPlanNextAction.missing_fields" :key="f" class="missing-field-item">· {{ f }}</div>
            </div>
            <el-button
              v-if="selectedPlanNextAction.can_advance && selectedPlanId"
              type="primary"
              size="small"
              @click="advancePlan(selectedPlanId!)"
              :loading="advancing"
            >推进到下一阶段</el-button>
          </div>
        </el-card>

        <!-- ═══════════ 桌面端：表格视图 ═══════════ -->
        <template v-if="!isMobile">
          <el-table :data="plans" stripe border size="small" v-loading="loading" @row-click="selectPlan" highlight-current-row>
            <el-table-column prop="name" label="策划名称" min-width="180">
              <template #default="{ row }">
                <div class="plan-name-cell">{{ row.name }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="series" label="系列" width="100" />
            <el-table-column prop="market" label="市场" width="100" />
            <el-table-column label="当前阶段" width="120">
              <template #default="{ row }">
                <el-tag :type="stageTagType(row.status)" size="small">{{ stageLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="进度" width="180">
              <template #default="{ row }">
                <el-progress :percentage="stageProgress(row.status)" :stroke-width="8" :color="progressColor(row.status)" />
              </template>
            </el-table-column>
            <el-table-column label="关联项目" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.project_id" size="small" type="success">已关联</el-tag>
                <span v-else class="no-project">-</span>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="160">
              <template #default="{ row }">{{ row.created_at?.substring(0, 10) || '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button link size="small" type="primary" @click.stop="viewDetail(row)">详情</el-button>
                <el-button link size="small" type="danger" @click.stop="deletePlan(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <!-- ═══════════ 桌面端分页 ═══════════ -->
          <div class="ppc-pagination">
            <el-pagination
              v-model:current-page="page"
              :page-size="pageSize"
              :total="total"
              layout="prev, pager, next, total"
              small
              @current-change="fetchPlans"
            />
          </div>
        </template>

        <!-- ═══════════ 移动端：卡片列表视图（无限滚动） ═══════════ -->
        <template v-if="isMobile">
          <div
            class="plan-cards-container"
            v-infinite-scroll="loadMore"
            :infinite-scroll-disabled="loading || !hasMore"
            infinite-scroll-distance="100"
          >
            <div
              v-for="plan in plans"
              :key="plan.id"
              class="plan-card"
              :class="{ 'is-selected': selectedPlanId === plan.id }"
              @click="selectPlan(plan)"
            >
              <div class="card-header">
                <span class="card-name">{{ plan.name }}</span>
                <el-tag :type="stageTagType(plan.status)" size="small" class="card-stage-tag">{{ stageLabel(plan.status) }}</el-tag>
              </div>
              <div class="card-body">
                <div class="card-field">
                  <span class="field-label">负责人</span>
                  <span class="field-value">{{ plan.created_by || '-' }}</span>
                </div>
                <div class="card-field">
                  <span class="field-label">截止日期</span>
                  <span class="field-value">{{ plan.created_at?.substring(0, 10) || '-' }}</span>
                </div>
                <div class="card-field">
                  <span class="field-label">下一步动作</span>
                  <span class="field-value">
                    <template v-if="selectedPlanId === plan.id && selectedPlanNextAction">
                      {{ selectedPlanNextAction.next_action }}
                    </template>
                    <el-button
                      v-else
                      link
                      size="small"
                      type="primary"
                      @click.stop="selectPlan(plan)"
                    >查看下一步</el-button>
                  </span>
                </div>
              </div>
            </div>
            <div v-if="!hasMore && plans.length > 0" class="no-more-data">— 已加载全部 —</div>
            <div v-if="loading && plans.length === 0" class="loading-placeholder">加载中...</div>
            <div v-if="!loading && plans.length === 0 && !hasMore" class="loading-placeholder">暂无数据</div>
          </div>
        </template>
      </el-col>
      <el-col :xs="24" :md="6" :lg="6">
        <GlobalActionCard />
      </el-col>
    </el-row>

    <!-- ═══════════ 创建策划弹窗（含 AI 智能生成草案） ═══════════ -->
    <el-dialog v-model="showCreateDialog" title="新建产品策划" width="620px" :close-on-click-modal="false" :destroy-on-close="true">
      <!-- 步骤指示器 -->
      <el-steps :active="createStep" align-center finish-status="success" size="small" style="margin-bottom:20px">
        <el-step title="选择条件" />
        <el-step title="AI生成" />
        <el-step title="预览确认" />
      </el-steps>

      <!-- ── Step 0: 选择条件 ── -->
      <template v-if="createStep === 0">
        <el-form :model="createForm" label-width="100" size="small">
          <el-form-item label="策划名称" required>
            <el-input v-model="createForm.name" placeholder="如: 2027年越南分体机" :disabled="!!aiDraft" />
          </el-form-item>
          <el-form-item label="目标市场" required>
            <el-select v-model="createForm.market_id" placeholder="请选择目标市场" filterable style="width:100%"
              :disabled="aiGenerating || !!aiDraft"
              @change="onMarketChange">
              <el-option
                v-for="m in targetMarkets"
                :key="m.id"
                :label="`${m.market_code} — ${m.market_name}`"
                :value="m.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="产品类型" required>
            <el-select v-model="createForm.product_type" placeholder="请选择产品类型" style="width:100%"
              :disabled="aiGenerating || !!aiDraft">
              <el-option label="壁挂分体机 (Split Wall)" value="split_wall" />
              <el-option label="柜机 (Floor Standing)" value="floor_standing" />
              <el-option label="嵌入式 (Cassette)" value="cassette" />
              <el-option label="风管机 (Duct)" value="duct" />
              <el-option label="窗机 (Window)" value="window" />
              <el-option label="移动空调 (Portable)" value="portable" />
            </el-select>
          </el-form-item>
          <el-form-item label="产品系列">
            <el-input v-model="createForm.series" placeholder="如: 越南分体壁挂机" :disabled="!!aiDraft" />
          </el-form-item>

          <!-- AI 智能生成按钮（仅在选择市场+产品类型后出现） -->
          <el-form-item v-if="createForm.market_id && createForm.product_type">
            <el-button
              type="success"
              size="small"
              @click="generateAIDraft"
              :loading="aiGenerating"
              :icon="AIIcon"
              style="width:100%"
            >🤖 AI智能生成草案</el-button>
          </el-form-item>
        </el-form>
      </template>

      <!-- ── Step 1: AI 生成中 — Loading 骨架屏 → 流式渲染 ── -->
      <template v-if="createStep === 1">
        <div class="ai-loading-container">
          <!-- 骨架屏 -->
          <template v-if="aiStreamingText === ''">
            <div class="skeleton-card">
              <div class="skeleton-line skeleton-line-title" />
              <div class="skeleton-line skeleton-line-short" />
              <div class="skeleton-line" />
              <div class="skeleton-line skeleton-line-short" />
              <div class="skeleton-line skeleton-line-half" />
              <div class="skeleton-line" />
              <div class="skeleton-line skeleton-line-long" />
              <div class="skeleton-line" />
              <div class="skeleton-line skeleton-line-half" />
            </div>
            <div class="ai-status-text">🤖 AI正在分析市场数据，生成策划草案...</div>
          </template>
          <!-- 流式渲染内容 -->
          <template v-else>
            <div class="ai-streaming-content">
              <pre class="ai-streaming-text">{{ aiStreamingText }}<span v-if="aiStreaming" class="cursor-blink">|</span></pre>
            </div>
          </template>
        </div>
      </template>

      <!-- ── Step 2: 预览确认 — 草案概要卡片 ── -->
      <template v-if="createStep === 2">
        <div class="draft-preview">
          <el-alert title="AI策划草案已生成" type="success" show-icon :closable="false" style="margin-bottom:16px" />
          <el-card shadow="never" class="draft-summary-card">
            <template #header>
              <div class="draft-card-header">
                <span class="draft-card-title">📋 草案概要</span>
                <el-tag size="small" type="success">AI生成</el-tag>
              </div>
            </template>
            <div class="draft-summary-body">
              <el-descriptions :column="2" border size="small">
                <el-descriptions-item label="策划名称">{{ aiDraft?.plan_name || '-' }}</el-descriptions-item>
                <el-descriptions-item label="产品类型">{{ aiDraft?.product_type || '-' }}</el-descriptions-item>
                <el-descriptions-item label="系列">{{ aiDraft?.series || '-' }}</el-descriptions-item>
                <el-descriptions-item label="目标市场">{{ aiDraft?.target_market_detail || '-' }}</el-descriptions-item>
                <el-descriptions-item label="容量范围">{{ aiDraft?.capacity_range || '-' }}</el-descriptions-item>
                <el-descriptions-item label="建议开发周期">{{ aiDraft?.development_timeline?.suggested_duration_months || '-' }} 个月</el-descriptions-item>
              </el-descriptions>
              <el-divider />
              <h4 class="draft-section-title">🎯 核心性能</h4>
              <el-descriptions :column="2" border size="small" v-if="aiDraft?.core_performance">
                <el-descriptions-item label="制冷能力 (BTU/h)">{{ aiDraft.core_performance.cooling_capacity_btu || '-' }}</el-descriptions-item>
                <el-descriptions-item label="制冷能力 (W)">{{ aiDraft.core_performance.cooling_capacity_w || '-' }}</el-descriptions-item>
                <el-descriptions-item label="能效比 EER">{{ aiDraft.core_performance.cooling_eer || '-' }}</el-descriptions-item>
                <el-descriptions-item label="制冷剂">{{ aiDraft.core_performance.refrigerant || '-' }}</el-descriptions-item>
                <el-descriptions-item label="能效等级">{{ aiDraft.core_performance.energy_rating || '-' }}</el-descriptions-item>
                <el-descriptions-item label="电压频率">{{ aiDraft.core_performance.voltage_freq || '-' }}</el-descriptions-item>
              </el-descriptions>
              <el-divider />
              <h4 class="draft-section-title">🏷️ 市场定位</h4>
              <el-descriptions :column="1" border size="small" v-if="aiDraft?.market_positioning">
                <el-descriptions-item label="目标细分市场">{{ aiDraft.market_positioning.target_market_segment || '-' }}</el-descriptions-item>
                <el-descriptions-item label="建议价格区间">{{ aiDraft.market_positioning.suggested_price_range || '-' }}</el-descriptions-item>
                <el-descriptions-item label="差异化卖点">
                  <span v-for="(d, i) in aiDraft.market_positioning.key_differentiators" :key="i">
                    <el-tag size="small" style="margin-right:4px;margin-bottom:4px">{{ d }}</el-tag>
                  </span>
                  <span v-if="!aiDraft.market_positioning.key_differentiators?.length">-</span>
                </el-descriptions-item>
              </el-descriptions>
              <el-divider />
              <h4 class="draft-section-title">⚙️ 技术规格</h4>
              <el-descriptions :column="2" border size="small" v-if="aiDraft?.technical_specs">
                <el-descriptions-item label="室内机噪音">{{ aiDraft.technical_specs.noise_indoor_db_max || '-' }} dB(A)</el-descriptions-item>
                <el-descriptions-item label="室外机噪音">{{ aiDraft.technical_specs.noise_outdoor_db_max || '-' }} dB(A)</el-descriptions-item>
                <el-descriptions-item label="循环风量">{{ aiDraft.technical_specs.airflow_m3h || '-' }} m³/h</el-descriptions-item>
                <el-descriptions-item label="室内机尺寸">{{ aiDraft.technical_specs.dimensions_indoor || '-' }}</el-descriptions-item>
              </el-descriptions>
              <el-divider />
              <h4 class="draft-section-title">💰 成本目标</h4>
              <el-descriptions :column="2" border size="small" v-if="aiDraft?.cost_targets">
                <el-descriptions-item label="目标工厂成本">{{ aiDraft.cost_targets.target_factory_cost || '-' }} 元</el-descriptions-item>
                <el-descriptions-item label="主要成本驱动">
                  <span v-for="(d, i) in aiDraft.cost_targets.key_cost_drivers" :key="i">
                    <el-tag size="small" style="margin-right:4px;margin-bottom:4px">{{ d }}</el-tag>
                  </span>
                </el-descriptions-item>
              </el-descriptions>
              <el-divider />
              <h4 class="draft-section-title">⚠️ 风险评估</h4>
              <el-descriptions :column="1" border size="small" v-if="aiDraft?.risk_assessment">
                <el-descriptions-item label="技术风险">
                  <span v-for="(r, i) in aiDraft.risk_assessment.technical_risks" :key="i" class="risk-item">{{ r }}</span>
                  <span v-if="!aiDraft.risk_assessment.technical_risks?.length">-</span>
                </el-descriptions-item>
                <el-descriptions-item label="市场风险">
                  <span v-for="(r, i) in aiDraft.risk_assessment.market_risks" :key="i" class="risk-item">{{ r }}</span>
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </el-card>

          <!-- 操作按钮 -->
          <div class="draft-actions">
            <el-button type="primary" @click="acceptDraft" :loading="acceptingDraft">📋 采纳填充表单</el-button>
            <el-button @click="regenerateDraft" :disabled="aiGenerating">🔄 重新生成</el-button>
            <el-button @click="manualFill">✏️ 手动填写</el-button>
          </div>
        </div>
      </template>

      <!-- ── 底部通用按钮（Step 0 时显示） ── -->
      <template #footer>
        <template v-if="createStep === 0">
          <el-button @click="closeCreateDialog">取消</el-button>
          <el-button type="primary" @click="createPlan" :loading="creating">创建</el-button>
        </template>
        <template v-else-if="createStep === 1">
          <el-button @click="cancelGeneration">取消生成</el-button>
        </template>
        <template v-else-if="createStep === 2">
          <el-button @click="backToStep(0)">返回修改条件</el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { Search, MagicStick } from '@element-plus/icons-vue'
import { useResponsive } from '../../composables/useResponsive'
import api from '../../api'
import { generatePlanDraft } from '../../api/ai'
import GlobalActionCard from '../../components/GlobalActionCard.vue'

const router = useRouter()
const AIIcon = MagicStick

// ── Responsive ──
const { isMobile } = useResponsive()
const searchExpanded = ref(false)
const hasMore = ref(true)

// ── Data ──
const plans = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterStatus = ref<string | null>(null)
const searchText = ref('')

// ── 下一步动作 ──
const selectedPlanId = ref<string | null>(null)
const selectedPlanName = ref('')
const selectedPlanNextAction = ref<any>(null)
const advancing = ref(false)

// ── 创建 ──
const showCreateDialog = ref(false)
const creating = ref(false)
const createForm = ref({ name: '', series: '', market: '', market_id: null as number | null, product_type: '' })
const createStep = ref(0) // 0=选择条件, 1=AI生成中, 2=预览确认

// ── 目标市场列表 ──
const targetMarkets = ref<any[]>([])

// ── AI 生成 ──
const aiGenerating = ref(false)
const aiStreaming = ref(false)
const aiStreamingText = ref('')
const aiDraft = ref<any>(null)
const acceptingDraft = ref(false)

// ── 监听对话框打开时加载目标市场 ──
function onMarketChange() {
  // 当市场改变时，自动填充市场名称
  const market = targetMarkets.value.find((m: any) => m.id === createForm.value.market_id)
  if (market) {
    createForm.value.market = market.market_code
  }
}

watch(showCreateDialog, async (val) => {
  if (val) {
    createStep.value = 0
    aiDraft.value = null
    aiStreamingText.value = ''
    aiGenerating.value = false
    aiStreaming.value = false
    createForm.value = { name: '', series: '', market: '', market_id: null, product_type: '' }
    await fetchTargetMarkets()
  }
})

async function fetchTargetMarkets() {
  try {
    const res = await api.get('/target-markets')
    targetMarkets.value = res.data || []
  } catch {
    targetMarkets.value = []
  }
}

// ── AI 智能生成草案 ──
async function generateAIDraft() {
  if (!createForm.value.market_id || !createForm.value.product_type) {
    ElMessage.warning('请先选择目标市场和产品类型')
    return
  }

  createStep.value = 1
  aiGenerating.value = true
  aiStreaming.value = true
  aiStreamingText.value = ''

  // 先显示骨架屏（空文本），然后逐步模拟流式输出
  await sleep(400)

  try {
    const res = await generatePlanDraft({
      market_id: createForm.value.market_id!,
      product_type: createForm.value.product_type,
    })

    const draft = res.data?.data || res.data
    aiDraft.value = draft

    // 模拟逐字流式渲染（将 JSON 格式化为可读文本）显示给用户
    const formattedText = formatDraftForStream(draft)
    await typewriteEffect(formattedText, 15)

    aiStreaming.value = false
    // 短暂延迟后进入预览确认步骤
    await sleep(500)
    createStep.value = 2
  } catch (e: any) {
    aiStreaming.value = false
    aiGenerating.value = false
    aiStreamingText.value = ''
    const msg = e?.response?.data?.detail || e?.message || 'AI生成失败，请稍后重试'
    ElMessage.error(msg)
    createStep.value = 0
  } finally {
    aiGenerating.value = false
  }
}

function formatDraftForStream(draft: any): string {
  const parts: string[] = []
  if (draft.plan_name) parts.push(`📋 策划名称: ${draft.plan_name}`)
  if (draft.product_type) parts.push(`🏭 产品类型: ${draft.product_type}`)
  if (draft.series) parts.push(`📦 系列: ${draft.series}`)
  if (draft.target_market_detail) parts.push(`🌍 目标市场: ${draft.target_market_detail}`)
  if (draft.capacity_range) parts.push(`📏 容量范围: ${draft.capacity_range}`)
  if (draft.core_performance) {
    parts.push(`\n🎯 核心性能:`)
    if (draft.core_performance.cooling_capacity_w) parts.push(`  制冷能力: ${draft.core_performance.cooling_capacity_w}W`)
    if (draft.core_performance.cooling_eer) parts.push(`  能效比 EER: ${draft.core_performance.cooling_eer}`)
    if (draft.core_performance.refrigerant) parts.push(`  制冷剂: ${draft.core_performance.refrigerant}`)
    if (draft.core_performance.energy_rating) parts.push(`  能效等级: ${draft.core_performance.energy_rating}`)
  }
  if (draft.market_positioning) {
    parts.push(`\n🏷️ 市场定位:`)
    if (draft.market_positioning.target_market_segment) parts.push(`  细分市场: ${draft.market_positioning.target_market_segment}`)
    if (draft.market_positioning.suggested_price_range) parts.push(`  建议价格: ${draft.market_positioning.suggested_price_range}`)
    if (draft.market_positioning.key_differentiators?.length) {
      parts.push(`  差异化卖点: ${draft.market_positioning.key_differentiators.join(', ')}`)
    }
  }
  if (draft.technical_specs) {
    parts.push(`\n⚙️ 技术规格:`)
    if (draft.technical_specs.noise_indoor_db_max) parts.push(`  室内噪音: ${draft.technical_specs.noise_indoor_db_max} dB(A)`)
    if (draft.technical_specs.noise_outdoor_db_max) parts.push(`  室外噪音: ${draft.technical_specs.noise_outdoor_db_max} dB(A)`)
    if (draft.technical_specs.airflow_m3h) parts.push(`  循环风量: ${draft.technical_specs.airflow_m3h} m³/h`)
  }
  if (draft.cost_targets) {
    parts.push(`\n💰 成本目标:`)
    if (draft.cost_targets.target_factory_cost) parts.push(`  目标工厂成本: ${draft.cost_targets.target_factory_cost} 元`)
  }
  if (draft.development_timeline) {
    parts.push(`\n📅 开发周期: ${draft.development_timeline.suggested_duration_months || '-'} 个月`)
  }
  if (draft.compliance_requirements?.required_certifications?.length) {
    parts.push(`🔖 所需认证: ${draft.compliance_requirements.required_certifications.join(', ')}`)
  }
  return parts.join('\n')
}

async function typewriteEffect(text: string, intervalMs: number) {
  let displayed = ''
  // 分段逐字显示，每段包含若干字符
  const chars = text.split('')
  let i = 0
  while (i < chars.length) {
    // 每批显示 1-3 个字符模拟打字效果
    const batchSize = Math.floor(Math.random() * 3) + 1
    const batch = chars.slice(i, i + batchSize).join('')
    displayed += batch
    aiStreamingText.value = displayed
    i += batchSize
    await sleep(intervalMs)
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// ── AI 草案操作 ──
function cancelGeneration() {
  aiGenerating.value = false
  aiStreaming.value = false
  aiStreamingText.value = ''
  createStep.value = 0
}

async function acceptDraft() {
  if (!aiDraft.value) return
  acceptingDraft.value = true
  try {
    // 从 AI 草案中提取数据填充表单
    const draft = aiDraft.value
    const payload: Record<string, any> = {
      name: draft.plan_name || createForm.value.name || '',
      series: draft.series || createForm.value.series || '',
      market: createForm.value.market || '',
      market_id: createForm.value.market_id,
    }

    // 调用 API 创建策划
    await api.post('/product-plans', payload)
    ElMessage.success('策划已创建，AI草案已采纳')
    showCreateDialog.value = false
    createForm.value = { name: '', series: '', market: '', market_id: null, product_type: '' }
    aiDraft.value = null
    aiStreamingText.value = ''
    createStep.value = 0
    await fetchPlans()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '创建策划失败')
  } finally {
    acceptingDraft.value = false
  }
}

async function regenerateDraft() {
  aiDraft.value = null
  aiStreamingText.value = ''
  aiStreaming.value = false
  createStep.value = 0
  // 自动再次触发生成
  await sleep(100)
  await generateAIDraft()
}

function manualFill() {
  // 退回 Step 0，让用户手动填写
  createStep.value = 0
  aiDraft.value = null
  aiStreamingText.value = ''
  ElMessage.info('已切换到手动填写模式')
}

function backToStep(step: number) {
  createStep.value = step
}

function closeCreateDialog() {
  showCreateDialog.value = false
  createStep.value = 0
  aiDraft.value = null
  aiStreamingText.value = ''
}

// ── 阶段映射 ──
const STAGE_ORDER = ['draft', 'competitor', 'definition', 'costing', 'tech_input', 'project_init', 'approved', 'released']
const STAGE_LABELS: Record<string, string> = {
  draft: '草稿', competitor: '竞品分析', definition: '产品定义',
  costing: '成本目标', tech_input: '技术方案', project_init: '立项审批',
  approved: '已批准', released: '已发布',
}
const STAGE_TAGS: Record<string, string> = {
  draft: 'info', competitor: 'primary', definition: '',
  costing: 'warning', tech_input: 'primary', project_init: 'warning',
  approved: 'success', released: '',
}

function stageLabel(s: string): string { return STAGE_LABELS[s] || s }
function stageTagType(s: string): string { return STAGE_TAGS[s] || 'info' }
function stageProgress(s: string): number {
  const idx = STAGE_ORDER.indexOf(s)
  return idx >= 0 ? Math.round((idx / (STAGE_ORDER.length - 1)) * 100) : 0
}
function progressColor(s: string): string {
  const p = stageProgress(s)
  if (p >= 80) return '#67c23a'
  if (p >= 40) return '#409eff'
  return '#e6a23c'
}

// ── 下一步动作计算 ──
const nextActionStepIndex = ref(0)

// ── API ──
async function fetchPlans(resetPage = true) {
  loading.value = true
  if (resetPage) {
    page.value = 1
    plans.value = []
    hasMore.value = true
  }
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (filterStatus.value) params.status = filterStatus.value
    if (searchText.value) params.search = searchText.value
    const res = await api.get('/product-plans', { params })
    const items = res.data.items || []
    if (resetPage) {
      plans.value = items
    } else {
      plans.value = [...plans.value, ...items]
    }
    total.value = res.data.total || 0
    hasMore.value = items.length >= pageSize.value
  } catch { /* handled */ }
  finally { loading.value = false }
}

async function loadMore() {
  if (loading.value || !hasMore.value) return
  page.value++
  await fetchPlans(false)
}

function toggleSearch() {
  searchExpanded.value = !searchExpanded.value
}

async function selectPlan(row: any) {
  if (selectedPlanId.value === row.id) return
  selectedPlanId.value = row.id
  selectedPlanName.value = row.name
  try {
    const res = await api.get(`/product-plans/${row.id}/next-action`)
    selectedPlanNextAction.value = res.data
    nextActionStepIndex.value = res.data.can_advance ? 1 : 0
  } catch {
    selectedPlanNextAction.value = null
  }
}

async function advancePlan(planId: string) {
  advancing.value = true
  try {
    await api.post(`/product-plans/${planId}/advance`)
    ElMessage.success('已推进到下一阶段')
    await fetchPlans()
    if (selectedPlanId.value === planId) {
      await selectPlan({ id: planId, name: selectedPlanName.value })
    }
  } catch { /* handled */ }
  finally { advancing.value = false }
}

function viewDetail(row: any) {
  router.push(`/product-plans/${row.id}`)
}

async function deletePlan(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除策划「${row.name}」？此操作不可恢复。`, '删除确认', {
      confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning',
    })
    await api.delete(`/product-plans/${row.id}`)
    ElMessage.success('已删除')
    await fetchPlans()
  } catch { /* cancelled or error */ }
}

async function createPlan() {
  if (!createForm.value.name.trim()) {
    ElMessage.warning('请输入策划名称')
    return
  }
  creating.value = true
  try {
    const payload: Record<string, any> = { name: createForm.value.name }
    if (createForm.value.series) payload.series = createForm.value.series
    if (createForm.value.market) payload.market = createForm.value.market
    if (createForm.value.market_id) payload.market_id = createForm.value.market_id
    if (createForm.value.product_type) payload.product_type = createForm.value.product_type
    await api.post('/product-plans', payload)
    ElMessage.success('策划创建成功')
    showCreateDialog.value = false
    createForm.value = { name: '', series: '', market: '', market_id: null, product_type: '' }
    await fetchPlans()
  } catch { /* handled */ }
  finally { creating.value = false }
}

onMounted(fetchPlans)
</script>

<style scoped>
.ppc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.ppc-header h2 { margin: 0; font-size: 20px; }
.ppc-header-actions { display: flex; gap: 8px; }
.ppc-filters { margin-bottom: 16px; }
.ppc-pagination { margin-top: 16px; display: flex; justify-content: flex-end; }

/* 极小屏幕下标题行换行保护 */
@media (max-width: 480px) {
  .ppc-header {
    flex-wrap: wrap;
    gap: 8px;
  }
  .ppc-header h2 {
    font-size: 17px;
    width: 100%;
  }
  .ppc-header-actions {
    width: 100%;
    justify-content: flex-start;
  }
}

.plan-name-cell { font-weight: 500; color: #303133; }
.no-project { color: #c0c4cc; }

/* 下一步动作卡片 */
.next-action-card { margin-bottom: 16px; border-left: 4px solid #409eff; }
.next-action-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.next-action-label { font-weight: 600; font-size: 14px; }
.next-action-body { margin-top: 12px; }
.next-action-text { margin-top: 12px; }
.missing-fields {
  margin-top: 8px;
  font-size: 13px;
  color: #e6a23c;
}
.missing-field-item { line-height: 1.6; }

/* ═══ 移动端专属样式 ═══ */
.mobile-filter-bar {
  margin-bottom: 12px;
}
.mobile-filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.mobile-search-input {
  margin-top: 8px;
}
.plan-cards-container {
  min-height: 200px;
}
.plan-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.plan-card:active {
  transform: scale(0.98);
}
.plan-card.is-selected {
  border-color: #409eff;
  box-shadow: 0 0 0 1px #409eff;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}
.card-name {
  font-weight: 600;
  font-size: 15px;
  color: #303133;
  flex: 1;
  margin-right: 8px;
  word-break: break-all;
}
.card-stage-tag {
  flex-shrink: 0;
}
.card-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.card-field {
  display: flex;
  align-items: center;
  font-size: 13px;
}
.field-label {
  color: #909399;
  min-width: 70px;
  flex-shrink: 0;
}
.field-value {
  color: #303133;
}
.no-more-data {
  text-align: center;
  color: #c0c4cc;
  font-size: 13px;
  padding: 16px 0;
}
.loading-placeholder {
  text-align: center;
  color: #909399;
  padding: 40px 0;
  font-size: 14px;
}

/* ═══════════ AI 骨架屏 & 流式渲染 ═══════════ */
.ai-loading-container {
  min-height: 240px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.skeleton-card {
  width: 100%;
  max-width: 480px;
  background: #f5f7fa;
  border-radius: 8px;
  padding: 20px;
}
.skeleton-line {
  height: 12px;
  background: linear-gradient(90deg, #e8e8e8 25%, #f0f0f0 50%, #e8e8e8 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
  border-radius: 4px;
  margin-bottom: 12px;
}
.skeleton-line-title { height: 18px; width: 60%; }
.skeleton-line-short { width: 40%; }
.skeleton-line-half { width: 50%; }
.skeleton-line-long { width: 80%; }
@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.ai-status-text {
  margin-top: 16px;
  font-size: 14px;
  color: #909399;
  text-align: center;
}
.ai-streaming-content {
  width: 100%;
  max-height: 400px;
  overflow-y: auto;
  background: #1a1a2e;
  border-radius: 8px;
  padding: 16px;
}
.ai-streaming-text {
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #00ff88;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}
.cursor-blink {
  animation: blink 0.8s step-end infinite;
  color: #00ff88;
}
@keyframes blink {
  50% { opacity: 0; }
}

/* ═══════════ 草案预览卡片 ═══════════ */
.draft-preview {
  max-height: 480px;
  overflow-y: auto;
}
.draft-summary-card {
  margin-bottom: 16px;
}
.draft-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.draft-card-title {
  font-weight: 600;
  font-size: 15px;
}
.draft-summary-body {
  padding: 4px 0;
}
.draft-section-title {
  margin: 0 0 8px;
  font-size: 14px;
  color: #303133;
}
.risk-item {
  display: inline-block;
  background: #fef0f0;
  color: #f56c6c;
  padding: 2px 8px;
  border-radius: 4px;
  margin: 2px 4px 2px 0;
  font-size: 12px;
}
.draft-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 16px;
}
.draft-actions .el-button {
  flex: 1;
}
</style>
