<template>
  <div class="crawl-admin">
    <!-- ========== 页面标题 ========== -->
    <div class="page-header">
      <h2>🕷️ 竞品爬虫管理</h2>
      <p class="page-desc">管理竞品数据爬取任务与搜索词配置</p>
    </div>

    <!-- ========== 双 Tab 布局 ========== -->
    <el-tabs v-model="activeTab" class="crawl-tabs">
      <!-- ════════════════════════════════════════════════════════════
       Tab 1: 爬取管理
      ════════════════════════════════════════════════════════════ -->
      <el-tab-pane label="爬取管理" name="crawl">
        <!-- ── 触发爬取区域 ── -->
        <div class="trigger-section">
          <div class="trigger-row">
            <div class="trigger-item">
              <label>市场</label>
              <el-select
                v-model="crawlForm.market_code"
                placeholder="选择市场"
                clearable
                style="width:180px"
              >
                <el-option
                  v-for="m in marketOptions"
                  :key="m.code"
                  :label="m.label"
                  :value="m.code"
                />
              </el-select>
            </div>
            <div class="trigger-item">
              <label>品牌</label>
              <el-input
                v-model="crawlForm.brand"
                placeholder="如 Midea"
                clearable
                style="width:180px"
              />
            </div>
            <div class="trigger-item trigger-action">
              <el-button
                type="primary"
                :loading="crawlRunning"
                :disabled="!crawlForm.market_code"
                @click="triggerCrawl"
              >
                🚀 触发爬取
              </el-button>
            </div>
          </div>
        </div>

        <!-- ── 日志表格 ── -->
        <div class="section-title">爬取日志</div>
        <el-table
          :data="logs"
          v-loading="logsLoading"
          border
          stripe
          size="small"
          style="width:100%"
          empty-text="暂无爬取日志"
        >
          <el-table-column prop="market_code" label="市场" width="90" />
          <el-table-column prop="brand" label="品牌" width="110" />
          <el-table-column prop="started_at" label="开始时间" width="160">
            <template #default="{ row }">
              {{ row.started_at ? formatTime(row.started_at) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="finished_at" label="结束时间" width="160">
            <template #default="{ row }">
              {{ row.finished_at ? formatTime(row.finished_at) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small" effect="dark">
                {{ statusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="query_count" label="查询数" width="70" align="right" />
          <el-table-column prop="pages_fetched" label="抓取页" width="70" align="right" />
          <el-table-column prop="total_found" label="找到" width="70" align="right" />
          <el-table-column prop="new_added" label="新增" width="70" align="right" />
          <el-table-column prop="error_message" label="错误信息" min-width="160" show-overflow-tooltip />
        </el-table>

        <!-- ── 分页 ── -->
        <div class="pagination-wrap">
          <el-pagination
            v-model:current-page="logPage"
            v-model:page-size="logPageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="logTotal"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="fetchLogs"
            @size-change="fetchLogs"
          />
        </div>
      </el-tab-pane>

      <!-- ════════════════════════════════════════════════════════════
       Tab 2: 搜索词管理
      ════════════════════════════════════════════════════════════ -->
      <el-tab-pane label="搜索词管理" name="searchTerms">
        <!-- ── 操作栏 ── -->
        <div class="toolbar-row">
          <span class="toolbar-title">共 {{ searchTermTotal }} 条搜索词</span>
          <el-button type="primary" size="small" :icon="Plus" @click="openAddTermDialog">
            新建搜索词
          </el-button>
        </div>

        <!-- ── 搜索词表格 ── -->
        <el-table
          :data="searchTerms"
          v-loading="searchTermsLoading"
          border
          stripe
          size="small"
          style="width:100%"
          empty-text="暂无搜索词"
        >
          <el-table-column prop="market_code" label="市场" width="90" />
          <el-table-column prop="brand" label="品牌" width="110" />
          <el-table-column prop="search_query" label="搜索词" min-width="150" show-overflow-tooltip />
          <el-table-column prop="language" label="语言" width="80" align="center" />
          <el-table-column prop="product_type_hint" label="产品类型提示" width="110" show-overflow-tooltip />
          <el-table-column prop="priority" label="优先级" width="70" align="center">
            <template #default="{ row }">
              <el-tag
                :type="row.priority >= 80 ? 'danger' : row.priority >= 50 ? 'warning' : 'info'"
                size="small"
              >
                {{ row.priority ?? '-' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="is_active" label="启用" width="60" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'danger'" size="small" effect="plain">
                {{ row.is_active ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="last_used_at" label="最后使用" width="150">
            <template #default="{ row }">
              {{ row.last_used_at ? formatTime(row.last_used_at) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="use_count" label="使用次数" width="75" align="right" />
          <el-table-column label="操作" width="70" fixed="right" align="center">
            <template #default="{ row }">
              <el-button
                type="danger"
                size="small"
                link
                @click="handleDeleteTerm(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- ── 分页 ── -->
        <div class="pagination-wrap">
          <el-pagination
            v-model:current-page="termPage"
            v-model:page-size="termPageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="searchTermTotal"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="fetchSearchTerms"
            @size-change="fetchSearchTerms"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- ══════════════════════════════════════════════════════════════
     新建搜索词弹窗
    ══════════════════════════════════════════════════════════════ -->
    <el-dialog
      v-model="termDialogVisible"
      title="新建搜索词"
      width="520px"
      :close-on-click-modal="false"
      @close="resetTermForm"
    >
      <el-form
        ref="termFormRef"
        :model="termForm"
        :rules="termFormRules"
        label-width="120px"
        label-position="right"
        size="small"
      >
        <el-form-item label="市场" prop="market_code">
          <el-select v-model="termForm.market_code" placeholder="选择市场" style="width:100%">
            <el-option
              v-for="m in marketOptions"
              :key="m.code"
              :label="m.label"
              :value="m.code"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="品牌" prop="brand">
          <el-input v-model="termForm.brand" placeholder="如 Midea" />
        </el-form-item>
        <el-form-item label="搜索词" prop="search_query">
          <el-input v-model="termForm.search_query" placeholder="如 Midea 12000BTU split AC" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="语言" prop="language">
              <el-input v-model="termForm.language" placeholder="en / zh / ar" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级" prop="priority">
              <el-input-number v-model="termForm.priority" :min="1" :max="100" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="产品类型提示" prop="product_type_hint">
          <el-input v-model="termForm.product_type_hint" placeholder="如 壁挂分体机 / 窗机" />
        </el-form-item>
        <el-form-item label="备注" prop="notes">
          <el-input
            v-model="termForm.notes"
            type="textarea"
            :rows="3"
            placeholder="可选备注信息"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="termDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingTerm" @click="handleSaveTerm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../../api'
import type { FormInstance, FormRules } from 'element-plus'

// ── 类型定义 ──────────────────────────────────────────────────────────

interface CrawlLogItem {
  id: number
  market_code: string
  brand: string
  started_at: string | null
  finished_at: string | null
  status: 'running' | 'success' | 'partial' | 'failed'
  query_count: number
  pages_fetched: number
  total_found: number
  new_added: number
  error_message: string | null
}

interface SearchTermItem {
  id: number
  market_code: string
  brand: string
  search_query: string
  language: string
  product_type_hint: string
  priority: number
  is_active: boolean
  last_used_at: string | null
  use_count: number
  notes: string
}

interface MarketOption {
  code: string
  label: string
}

interface CrawlForm {
  market_code: string
  brand: string
}

interface TermForm {
  market_code: string
  brand: string
  search_query: string
  language: string
  product_type_hint: string
  priority: number
  notes: string
}

// ── 常量 ──────────────────────────────────────────────────────────────

const MARKET_OPTIONS: MarketOption[] = [
  { code: 'CN', label: '中国' },
  { code: 'US', label: '美国' },
  { code: 'EU', label: '欧盟' },
  { code: 'SEA', label: '东南亚' },
  { code: 'ME', label: '中东' },
  { code: 'LATAM', label: '拉美' },
  { code: 'AF', label: '非洲' },
  { code: 'OC', label: '澳洲' },
]

// ── 响应式状态 ────────────────────────────────────────────────────────

const activeTab = ref('crawl')

// 爬取部分
const crawlForm = reactive<CrawlForm>({
  market_code: '',
  brand: '',
})
const crawlRunning = ref(false)
const logs = ref<CrawlLogItem[]>([])
const logsLoading = ref(false)
const logPage = ref(1)
const logPageSize = ref(20)
const logTotal = ref(0)

// 搜索词部分
const searchTerms = ref<SearchTermItem[]>([])
const searchTermsLoading = ref(false)
const termPage = ref(1)
const termPageSize = ref(20)
const searchTermTotal = ref(0)

// 新建搜索词弹窗
const termDialogVisible = ref(false)
const savingTerm = ref(false)
const termFormRef = ref<FormInstance>()
const termForm = reactive<TermForm>({
  market_code: '',
  brand: '',
  search_query: '',
  language: '',
  product_type_hint: '',
  priority: 50,
  notes: '',
})

// 表单校验规则
const termFormRules: FormRules = {
  market_code: [{ required: true, message: '请选择市场', trigger: 'change' }],
  brand: [{ required: true, message: '请输入品牌', trigger: 'blur' }],
  search_query: [{ required: true, message: '请输入搜索词', trigger: 'blur' }],
}

// ── 市场选项（暴露给模板） ──────────────────────────────────────────────
const marketOptions = MARKET_OPTIONS

// ── 辅助函数 ──────────────────────────────────────────────────────────

function statusTagType(status: string): 'primary' | 'success' | 'warning' | 'danger' | 'info' {
  switch (status) {
    case 'running':  return 'primary'
    case 'success':  return 'success'
    case 'partial':  return 'warning'
    case 'failed':   return 'danger'
    default:         return 'info'
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'running':  return '运行中'
    case 'success':  return '成功'
    case 'partial':  return '部分成功'
    case 'failed':   return '失败'
    default:         return status
  }
}

function formatTime(iso: string): string {
  if (!iso) return '-'
  try {
    const d = new Date(iso)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  } catch {
    return iso
  }
}

// ── API 调用 ──────────────────────────────────────────────────────────

/** 触发爬取 */
async function triggerCrawl() {
  if (!crawlForm.market_code) {
    ElMessage.warning('请先选择市场')
    return
  }
  crawlRunning.value = true
  try {
    await api.post('/pm/crawls/run', {
      market_code: crawlForm.market_code,
      brand: crawlForm.brand || undefined,
    })
    ElMessage.success('爬取任务已触发')
    // 刷新日志
    fetchLogs()
  } catch (err: unknown) {
    // api interceptor 已统一弹错误提示
  } finally {
    crawlRunning.value = false
  }
}

/** 获取爬取日志 */
async function fetchLogs() {
  logsLoading.value = true
  try {
    const params: Record<string, string | number> = {
      page: logPage.value,
      page_size: logPageSize.value,
    }
    if (crawlForm.market_code) params.market_code = crawlForm.market_code
    if (crawlForm.brand) params.brand = crawlForm.brand
    const res = await api.get('/pm/crawls/logs', { params })
    const data = res.data as { items: CrawlLogItem[]; total: number }
    logs.value = data.items || []
    logTotal.value = data.total || 0
  } catch {
    logs.value = []
    logTotal.value = 0
  } finally {
    logsLoading.value = false
  }
}

/** 获取搜索词列表 */
async function fetchSearchTerms() {
  searchTermsLoading.value = true
  try {
    const params: Record<string, string | number> = {
      page: termPage.value,
      page_size: termPageSize.value,
    }
    const res = await api.get('/pm/crawls/search-terms', { params })
    const data = res.data as { items: SearchTermItem[]; total: number }
    searchTerms.value = data.items || []
    searchTermTotal.value = data.total || 0
  } catch {
    searchTerms.value = []
    searchTermTotal.value = 0
  } finally {
    searchTermsLoading.value = false
  }
}

/** 打开新建搜索词弹窗 */
function openAddTermDialog() {
  resetTermForm()
  termDialogVisible.value = true
}

/** 重置搜索词表单 */
function resetTermForm() {
  termForm.market_code = ''
  termForm.brand = ''
  termForm.search_query = ''
  termForm.language = ''
  termForm.product_type_hint = ''
  termForm.priority = 50
  termForm.notes = ''
  termFormRef.value?.clearValidate()
}

/** 保存新建搜索词 */
async function handleSaveTerm() {
  const valid = await termFormRef.value?.validate().catch(() => false)
  if (!valid) return

  savingTerm.value = true
  try {
    await api.post('/pm/crawls/search-terms', {
      market_code: termForm.market_code,
      brand: termForm.brand,
      search_query: termForm.search_query,
      language: termForm.language || undefined,
      product_type_hint: termForm.product_type_hint || undefined,
      priority: termForm.priority,
      notes: termForm.notes || undefined,
    })
    ElMessage.success('搜索词已创建')
    termDialogVisible.value = false
    fetchSearchTerms()
  } catch {
    // api interceptor 已处理
  } finally {
    savingTerm.value = false
  }
}

/** 删除搜索词 */
async function handleDeleteTerm(row: SearchTermItem) {
  try {
    await ElMessageBox.confirm(
      `确认删除搜索词「${row.search_query}」(品牌: ${row.brand})？`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await api.delete(`/pm/crawls/search-terms/${row.id}`)
    ElMessage.success('已删除')
    fetchSearchTerms()
  } catch {
    // 取消操作或 api 异常均静默处理
  }
}

// ── 初始化 ────────────────────────────────────────────────────────────

onMounted(() => {
  fetchLogs()
  fetchSearchTerms()
})
</script>

<style scoped>
/* ========== 页面布局 ========== */
.crawl-admin {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.page-desc {
  margin: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.crawl-tabs {
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

/* ========== 触发爬取区域 ========== */
.trigger-section {
  background: var(--el-fill-color-lighter);
  border-radius: 6px;
  padding: 16px 20px;
  margin-bottom: 20px;
}

.trigger-row {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
}

.trigger-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.trigger-item label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-weight: 500;
}

.trigger-action {
  justify-content: flex-end;
}

/* ========== 区域标题 ========== */
.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

/* ========== 操作栏 ========== */
.toolbar-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.toolbar-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-regular);
}

/* ========== 分页 ========== */
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 12px;
}

/* ========== 通用深色/圆角覆盖 ========== */
:deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background: var(--el-fill-color-lighter);
}

:deep(.el-tabs__header) {
  margin-bottom: 20px;
}

:deep(.el-table th.el-table__cell) {
  background-color: var(--el-fill-color-light);
  font-weight: 600;
  color: var(--el-text-color-primary);
}
</style>
