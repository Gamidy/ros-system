<template>
  <div class="cost-sheet-list">
    <!-- 顶部导航 tabs -->
    <el-menu
      :default-active="activeTab"
      mode="horizontal"
      class="nav-tabs"
      @select="handleTabSelect"
    >
      <el-menu-item index="/cost-accounting/periods">核算期间</el-menu-item>
      <el-menu-item index="/cost-accounting/labor-rates">工时费率</el-menu-item>
      <el-menu-item index="/cost-accounting/overhead-rules">分摊规则</el-menu-item>
      <el-menu-item index="/cost-accounting/analysis">成本分析</el-menu-item>
    </el-menu>

    <!-- 筛选区域 -->
    <div class="filter-bar">
      <el-form :inline="true" size="default">
        <el-form-item label="核算期间">
          <el-select
            v-model="query.period_id"
            placeholder="选择期间"
            clearable
            style="width: 180px"
            @change="loadData"
          >
            <el-option
              v-for="p in periods"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="状态">
          <el-select
            v-model="query.status"
            placeholder="选择状态"
            clearable
            style="width: 140px"
            @change="loadData"
          >
            <el-option label="草稿" value="draft" />
            <el-option label="已定稿" value="finalized" />
          </el-select>
        </el-form-item>

        <el-form-item label="产品策划">
          <el-select
            v-model="query.plan_id"
            placeholder="搜索产品"
            clearable
            filterable
            remote
            :remote-method="searchProductPlans"
            :loading="searchLoading"
            style="width: 240px"
            @change="loadData"
          >
            <el-option
              v-for="p in productPlans"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <div class="filter-actions">
        <el-button type="success" @click="showGenerateDialog">
          + 生成核算单
        </el-button>
      </div>
    </div>

    <!-- 核算单列表 -->
    <el-table
      :data="sheetList"
      v-loading="tableLoading"
      border
      stripe
      style="width: 100%"
      @sort-change="handleSortChange"
    >
      <el-table-column prop="sheet_no" label="核算单编号" min-width="160" sortable="custom" />
      <el-table-column prop="product_plan_id" label="产品策划ID" min-width="120" />
      <el-table-column prop="period_id" label="期间ID" min-width="80" />
      <el-table-column prop="material_cost_actual" label="物料成本(实际)" width="120" align="right">
        <template #default="{ row }">
          {{ formatMoney(row.material_cost_actual) }}
        </template>
      </el-table-column>
      <el-table-column prop="labor_cost_actual" label="人工成本(实际)" width="120" align="right">
        <template #default="{ row }">
          {{ formatMoney(row.labor_cost_actual) }}
        </template>
      </el-table-column>
      <el-table-column prop="overhead_cost_actual" label="制造费用(实际)" width="120" align="right">
        <template #default="{ row }">
          {{ formatMoney(row.overhead_cost_actual) }}
        </template>
      </el-table-column>
      <el-table-column prop="total_cost_actual" label="总成本(实际)" width="120" align="right" sortable="custom">
        <template #default="{ row }">
          {{ formatMoney(row.total_cost_actual) }}
        </template>
      </el-table-column>
      <el-table-column prop="total_cost_target" label="总成本(目标)" width="120" align="right" sortable="custom">
        <template #default="{ row }">
          {{ formatMoney(row.total_cost_target) }}
        </template>
      </el-table-column>
      <el-table-column prop="variance_pct" label="差异率" width="100" align="right">
        <template #default="{ row }">
          <span :class="varianceClass(row.variance_pct)">
            {{ formatPercent(row.variance_pct) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 'finalized' ? 'success' : 'warning'" size="small">
            {{ row.status === 'finalized' ? '已定稿' : '草稿' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="340" fixed="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            link
            size="small"
            @click="viewDetail(row)"
          >
            查看详情
          </el-button>
          <el-button
            type="success"
            link
            size="small"
            :loading="finalizingId === row.id"
            :disabled="row.status === 'finalized'"
            @click="handleFinalize(row)"
          >
            定稿
          </el-button>
          <el-button
            type="warning"
            link
            size="small"
            :loading="recalculatingId === row.id"
            :disabled="row.status === 'draft'"
            @click="handleRecalculate(row)"
          >
            重新核算
          </el-button>
          <el-button
            type="danger"
            link
            size="small"
            :loading="deletingId === row.id"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <el-empty v-if="!tableLoading && sheetList.length === 0" description="暂无核算单数据" :image-size="60" />

    <!-- 分页器 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.size"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadData"
        @current-change="loadData"
      />
    </div>

    <!-- 生成核算单 弹窗 -->
    <el-dialog
      v-model="generateDialogVisible"
      title="生成核算单"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="generateFormRef"
        :model="generateForm"
        :rules="generateRules"
        label-width="100px"
        @submit.prevent
      >
        <el-form-item label="产品策划" prop="product_plan_id">
          <el-select
            v-model="generateForm.product_plan_id"
            placeholder="搜索产品策划"
            filterable
            remote
            :remote-method="remoteSearchProductPlan"
            :loading="generateSearchLoading"
            style="width: 100%"
          >
            <el-option
              v-for="p in generateProductPlans"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="核算期间" prop="period_id">
          <el-select
            v-model="generateForm.period_id"
            placeholder="选择期间"
            style="width: 100%"
          >
            <el-option
              v-for="p in periods"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="generateDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="generating"
          @click="handleGenerate"
        >
          确认生成
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as API from '../../api/costAccounting'

const router = useRouter()

/* ===================== 顶部导航 ===================== */
const activeTab = ref('/cost-accounting/sheets')

const handleTabSelect = (index: string) => {
  router.push(index)
}

/* ===================== 筛选 ===================== */
interface Period {
  id: number
  name: string
}
interface ProductPlan {
  id: number
  name: string
}
interface SheetRecord {
  id: number
  sheet_no: string
  material_cost_actual: number
  labor_cost_actual: number
  overhead_cost_actual: number
  total_cost_actual: number
  total_cost_target: number
  variance_pct: number
  status: string
}

const periods = ref<Period[]>([])
const productPlans = ref<ProductPlan[]>([])
const searchLoading = ref(false)
const sheetList = ref<SheetRecord[]>([])
const total = ref(0)
const tableLoading = ref(false)

const query = reactive({
  page: 1,
  size: 20,
  period_id: undefined as number | undefined,
  status: undefined as string | undefined,
  plan_id: undefined as number | undefined,
  order_field: undefined as string | undefined,
  order_dir: undefined as string | undefined,
})

const loadData = async () => {
  tableLoading.value = true
  try {
    const params: Record<string, string | number | undefined> = {
      page: query.page,
      size: query.size,
    }
    if (query.period_id) params.period_id = query.period_id
    if (query.status) params.status = query.status
    if (query.plan_id) params.plan_id = query.plan_id
    if (query.order_field) {
      params.order_field = query.order_field
      params.order_dir = query.order_dir
    }
    const res = await API.listSheets(params)
    sheetList.value = res.data?.items ?? res.data ?? []
    total.value = (res.data as Record<string, unknown>)?.total ?? 0
  } catch (e: unknown) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '加载核算单列表失败')
  } finally {
    tableLoading.value = false
  }
}

const resetQuery = () => {
  query.page = 1
  query.size = 20
  query.period_id = undefined
  query.status = undefined
  query.plan_id = undefined
  query.order_field = undefined
  query.order_dir = undefined
  loadData()
}

const handleSortChange = ({ prop, order }: { prop?: string; order?: string }) => {
  if (prop && order) {
    query.order_field = prop
    query.order_dir = order === 'ascending' ? 'asc' : 'desc'
  } else {
    query.order_field = undefined
    query.order_dir = undefined
  }
  query.page = 1
  loadData()
}

/* ===================== 远程搜索产品策划（顶部筛选） ===================== */
const searchProductPlans = async (keyword: string) => {
  if (!keyword) {
    productPlans.value = []
    return
  }
  searchLoading.value = true
  try {
    const res = await API.listProductPlans({ keyword, page: 1, size: 20 })
    productPlans.value = res.data?.items ?? res.data ?? []
  } catch {
    productPlans.value = []
  } finally {
    searchLoading.value = false
  }
}

/* ===================== 格式化 ===================== */
const formatMoney = (val?: number) => {
  if (val === null || val === undefined) return '-'
  return `¥${Number(val).toFixed(2)}`
}
const formatPercent = (val?: number) => {
  if (val === null || val === undefined) return '-'
  return `${Number(val).toFixed(2)}%`
}
const varianceClass = (val?: number) => {
  if (val === null || val === undefined) return ''
  if (val > 0) return 'variance-up'
  if (val < 0) return 'variance-down'
  return ''
}

/* ===================== 生成核算单 ===================== */
const generateDialogVisible = ref(false)
const generating = ref(false)
const generateFormRef = ref()
const generateSearchLoading = ref(false)
const generateProductPlans = ref<ProductPlan[]>([])

interface GenerateForm {
  product_plan_id: number | undefined
  period_id: number | undefined
}
const generateForm = reactive<GenerateForm>({
  product_plan_id: undefined,
  period_id: undefined,
})
const generateRules = {
  product_plan_id: [{ required: true, message: '请选择产品策划', trigger: 'change' }],
  period_id: [{ required: true, message: '请选择核算期间', trigger: 'change' }],
}

const showGenerateDialog = () => {
  generateForm.product_plan_id = undefined
  generateForm.period_id = undefined
  generateProductPlans.value = []
  generateDialogVisible.value = true
}

const remoteSearchProductPlan = async (keyword: string) => {
  if (!keyword) {
    generateProductPlans.value = []
    return
  }
  generateSearchLoading.value = true
  try {
    const res = await API.listProductPlans({ keyword, page: 1, size: 20 })
    generateProductPlans.value = res.data?.items ?? res.data ?? []
  } catch {
    generateProductPlans.value = []
  } finally {
    generateSearchLoading.value = false
  }
}

const handleGenerate = async () => {
  if (!generateFormRef.value) return
  try {
    await generateFormRef.value.validate()
  } catch {
    return
  }
  generating.value = true
  try {
    await API.generateSheet(String(generateForm.product_plan_id!), generateForm.period_id!)
    ElMessage.success('核算单生成成功')
    generateDialogVisible.value = false
    loadData()
  } catch (e: unknown) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '生成核算单失败')
  } finally {
    generating.value = false
  }
}

/* ===================== 操作 ===================== */
const finalizingId = ref<number | null>(null)
const recalculatingId = ref<number | null>(null)
const deletingId = ref<number | null>(null)

const viewDetail = (row: SheetRecord) => {
  router.push(`/cost-accounting/sheets/${row.id}`)
}

const handleFinalize = async (row: SheetRecord) => {
  try {
    await ElMessageBox.confirm('确认定稿该核算单？定稿后不可修改。', '提示', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  finalizingId.value = row.id
  try {
    await API.finalizeSheet(row.id)
    ElMessage.success('定稿成功')
    loadData()
  } catch (e: unknown) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '定稿失败')
  } finally {
    finalizingId.value = null
  }
}

const handleRecalculate = async (row: SheetRecord) => {
  try {
    await ElMessageBox.confirm('确认重新核算该核算单？', '提示', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  recalculatingId.value = row.id
  try {
    await API.recalculateSheet(row.id)
    ElMessage.success('重新核算成功')
    loadData()
  } catch (e: unknown) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '重新核算失败')
  } finally {
    recalculatingId.value = null
  }
}

const handleDelete = async (row: SheetRecord) => {
  try {
    await ElMessageBox.confirm(`确认删除核算单「${row.sheet_no}」？`, '警告', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'error',
    })
  } catch {
    return
  }
  deletingId.value = row.id
  try {
    await API.deleteSheet(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e: unknown) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '删除失败')
  } finally {
    deletingId.value = null
  }
}

/* ===================== 初始化 ===================== */
const init = async () => {
  try {
    const res = await API.listPeriods({ page: 1, size: 999 })
    periods.value = res.data?.items ?? res.data ?? []
  } catch {
    periods.value = []
  }
  loadData()
}

onMounted(() => {
  init()
})
</script>

<style scoped>
.cost-sheet-list {
  padding: 16px 20px;
  background: #f5f7fa;
  min-height: 100%;
}

.nav-tabs {
  margin-bottom: 16px;
  background: #fff;
  border-radius: 6px;
  padding: 0 8px;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  background: #fff;
  padding: 16px 20px 0 20px;
  border-radius: 6px;
  margin-bottom: 16px;
}

.filter-actions {
  padding-bottom: 18px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 16px 0;
  background: #fff;
  border-radius: 6px;
  margin-top: 16px;
}

.variance-up {
  color: #f56c6c;
  font-weight: 600;
}

.variance-down {
  color: #67c23a;
  font-weight: 600;
}
</style>
