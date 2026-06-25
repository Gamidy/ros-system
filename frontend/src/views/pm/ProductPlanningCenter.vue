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
        <el-row :gutter="12" class="ppc-filters">
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

        <!-- ═══════════ 策划列表 ═══════════ -->
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

        <!-- ═══════════ 分页 ═══════════ -->
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
      </el-col>
      <el-col :xs="24" :md="6" :lg="6">
        <GlobalActionCard />
      </el-col>
    </el-row>

    <!-- ═══════════ 创建策划弹窗 ═══════════ -->
    <el-dialog v-model="showCreateDialog" title="新建产品策划" width="520px" :close-on-click-modal="false">
      <el-form :model="createForm" label-width="100" size="small">
        <el-form-item label="策划名称" required>
          <el-input v-model="createForm.name" placeholder="如: 2027年越南分体机" />
        </el-form-item>
        <el-form-item label="产品系列">
          <el-input v-model="createForm.series" placeholder="如: 越南分体壁挂机" />
        </el-form-item>
        <el-form-item label="目标市场">
          <el-input v-model="createForm.market" placeholder="如: VN" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createPlan" :loading="creating">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import api from '../../api'
import GlobalActionCard from '../../components/GlobalActionCard.vue'

const router = useRouter()

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
const createForm = ref({ name: '', series: '', market: '' })

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
async function fetchPlans() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (filterStatus.value) params.status = filterStatus.value
    if (searchText.value) params.search = searchText.value
    const res = await api.get('/product-plans', { params })
    plans.value = res.data.items || []
    total.value = res.data.total || 0
  } catch { /* handled */ }
  finally { loading.value = false }
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
    await api.post('/product-plans', createForm.value)
    ElMessage.success('策划创建成功')
    showCreateDialog.value = false
    createForm.value = { name: '', series: '', market: '' }
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
</style>
