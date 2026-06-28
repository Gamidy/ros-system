<template>
  <div class="standard-manage">
    <el-page-header title="标准监控管理" @back="$router.push('/dashboard')" />

    <el-card class="manage-card">
      <el-tabs v-model="activeTab">
        <!-- Tab 1: 地区配置 -->
        <el-tab-pane label="地区配置" name="regions">
          <div class="toolbar">
            <el-button type="primary" size="small" @click="showRegionDialog()">新增地区</el-button>
            <el-button size="small" @click="triggerCrawl()">
              <el-icon><Refresh /></el-icon> 手动爬取全部
            </el-button>
          </div>
          <el-table :data="regions" stripe>
            <el-table-column prop="code" label="代码" width="80" />
            <el-table-column prop="name" label="名称" width="120" />
            <el-table-column prop="name_en" label="英文名称" width="180" />
            <el-table-column prop="scan_method" label="爬取方式" width="100">
              <template #default="{ row }">
                <el-tag :type="row.scan_method === 'rss' ? 'primary' :
                  row.scan_method === 'api' ? 'success' : 'warning'" size="small">
                  {{ row.scan_method }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="is_active" label="启用" width="80">
              <template #default="{ row }">
                <el-switch v-model="row.is_active" @change="toggleRegionActive(row)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button link size="small" @click="showRegionDialog(row)">编辑</el-button>
                <el-button link size="small" @click="triggerCrawl(row.id)">立即爬取</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- Tab 2: 标准条目管理 -->
        <el-tab-pane label="标准条目管理" name="entries">
          <div class="toolbar">
            <el-button type="primary" size="small" @click="showEntryDialog()">手动录入</el-button>
          </div>
          <el-table :data="entries" stripe v-loading="entriesLoading" max-height="500">
            <el-table-column prop="std_number" label="标准编号" width="180" />
            <el-table-column prop="title" label="标题" min-width="280" show-overflow-tooltip />
            <el-table-column prop="region_name" label="地区" width="80" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag
                  :type="row.status === 'active' ? 'success' : 'info'"
                  size="small"
                >{{ row.status === 'active' ? '生效' : '废止' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button link size="small" @click="showEntryDialog(row)">编辑</el-button>
                <el-button link size="small" type="danger" @click="deleteEntry(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-if="entriesPage.total > entriesPage.page_size"
            v-model:current-page="entriesPage.page"
            :page-size="entriesPage.page_size"
            :total="entriesPage.total"
            small
            layout="prev, pager, next"
            @change="loadEntries"
            class="pagination-wrap"
          />
        </el-tab-pane>

        <!-- Tab 3: 爬取日志 -->
        <el-tab-pane label="爬取日志" name="logs">
          <div class="toolbar">
            <el-select v-model="logFilter.region_id" clearable placeholder="全部地区" size="small" style="width:140px">
              <el-option v-for="r in regions" :key="r.id" :label="r.name" :value="r.id" />
            </el-select>
            <el-select v-model="logFilter.status" clearable placeholder="全部状态" size="small" style="width:120px">
              <el-option label="运行中" value="running" />
              <el-option label="成功" value="success" />
              <el-option label="失败" value="failed" />
            </el-select>
            <el-button size="small" @click="loadLogs">刷新</el-button>
          </div>
          <el-table :data="logs" stripe max-height="500">
            <el-table-column prop="region_name" label="地区" width="100" />
            <el-table-column prop="started_at" label="开始时间" width="160" />
            <el-table-column prop="finished_at" label="结束时间" width="160" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag
                  :type="row.status === 'success' ? 'success' :
                    row.status === 'running' ? 'warning' : 'danger'"
                  size="small"
                >{{ row.status === 'success' ? '成功' :
                     row.status === 'running' ? '运行中' : '失败' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="total_fetched" label="抓取" width="60" align="center" />
            <el-table-column prop="new_added" label="新增" width="60" align="center" />
            <el-table-column prop="updated" label="更新" width="60" align="center" />
            <el-table-column prop="error_message" label="错误信息" min-width="200" show-overflow-tooltip />
          </el-table>
          <el-pagination
            v-if="logsPage.total > logsPage.page_size"
            v-model:current-page="logsPage.page"
            :page-size="logsPage.page_size"
            :total="logsPage.total"
            small
            layout="prev, pager, next"
            @change="loadLogs"
            class="pagination-wrap"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 地区编辑对话框 -->
    <el-dialog v-model="regionVisible" :title="regionForm.id ? '编辑地区' : '新增地区'" width="500px">
      <el-form :model="regionForm" label-width="100px" size="small">
        <el-form-item label="地区代码">
          <el-input v-model="regionForm.code" :disabled="!!regionForm.id" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="regionForm.name" />
        </el-form-item>
        <el-form-item label="英文名称">
          <el-input v-model="regionForm.name_en" />
        </el-form-item>
        <el-form-item label="官网URL">
          <el-input v-model="regionForm.base_url" />
        </el-form-item>
        <el-form-item label="爬取方式">
          <el-select v-model="regionForm.scan_method">
            <el-option label="RSS" value="rss" />
            <el-option label="HTML" value="html" />
            <el-option label="API" value="api" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="regionVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRegion">保存</el-button>
      </template>
    </el-dialog>

    <!-- 标准录入对话框 -->
    <el-dialog v-model="entryVisible" :title="entryForm.id ? '编辑标准' : '手动录入'" width="700px">
      <el-form :model="entryForm" label-width="100px" size="small">
        <el-form-item label="地区">
          <el-select v-model="entryForm.region_id" style="width:100%">
            <el-option v-for="r in regions" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="entryForm.category_id" clearable style="width:100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="标准编号">
          <el-input v-model="entryForm.std_number" />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="entryForm.title" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="英文标题">
          <el-input v-model="entryForm.title_en" type="textarea" :rows="2" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="版本">
              <el-input v-model="entryForm.version" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="修订信息">
              <el-input v-model="entryForm.amendment" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="entryForm.status">
                <el-option label="已生效" value="active" />
                <el-option label="已废止" value="superseded" />
                <el-option label="草案" value="draft" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="影响等级">
              <el-select v-model="entryForm.impact_level" clearable>
                <el-option label="严重" value="critical" />
                <el-option label="高" value="high" />
                <el-option label="中" value="medium" />
                <el-option label="低" value="low" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="来源链接">
          <el-input v-model="entryForm.source_url" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="entryVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEntry">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import type { RegionItem, CategoryItem } from '@/api/standards'
import {
  listAdminRegions, createRegion, updateRegion,
  triggerCrawl as apiTriggerCrawl,
  listStandards, listCategories,
  createStandard, updateStandard, deleteStandard,
  listCrawlLogs,
} from '@/api/standards'

// ── Tab ──
const activeTab = ref('regions')

// ── 地区 ──
const regions = ref<RegionItem[]>([])
const regionVisible = ref(false)
const regionForm = reactive<Record<string, any>>({ code: '', name: '', name_en: '', base_url: '', scan_method: 'rss' })

async function loadRegions() {
  try {
    regions.value = await listAdminRegions()
  } catch { /* ignore */ }
}

function showRegionDialog(row?: RegionItem) {
  if (row) {
    Object.assign(regionForm, { ...row })
  } else {
    Object.assign(regionForm, { code: '', name: '', name_en: '', base_url: '', scan_method: 'rss' })
  }
  regionVisible.value = true
}

async function saveRegion() {
  try {
    if (regionForm.id) {
      await updateRegion(regionForm.id, regionForm)
      ElMessage.success('更新成功')
    } else {
      await createRegion(regionForm)
      ElMessage.success('创建成功')
    }
    regionVisible.value = false
    await loadRegions()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function toggleRegionActive(row: RegionItem) {
  await updateRegion(row.id!, { is_active: row.is_active })
}

// ── 标准条目 ──
const categories = ref<CategoryItem[]>([])
const entries = ref<any[]>([])
const entriesLoading = ref(false)
const entriesPage = reactive({ page: 1, page_size: 20, total: 0 })
const entryVisible = ref(false)
const entryForm = reactive<Record<string, any>>({})

async function loadEntries() {
  entriesLoading.value = true
  try {
    const res = await listStandards({ page: entriesPage.page, page_size: entriesPage.page_size })
    entries.value = res.items
    entriesPage.total = res.total
  } finally {
    entriesLoading.value = false
  }
}

function showEntryDialog(row?: any) {
  if (row) {
    Object.assign(entryForm, { ...row })
  } else {
    Object.assign(entryForm, {
      region_id: '', category_id: null, std_number: '', title: '',
      title_en: '', version: '', amendment: '', status: 'active',
      impact_level: null, source_url: '',
    })
  }
  entryVisible.value = true
}

async function saveEntry() {
  try {
    if (entryForm.id) {
      await updateStandard(entryForm.id, entryForm)
      ElMessage.success('更新成功')
    } else {
      await createStandard(entryForm as Parameters<typeof createStandard>[0])
      ElMessage.success('创建成功')
    }
    entryVisible.value = false
    await loadEntries()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function deleteEntry(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除标准「${row.std_number}」？`, '确认')
    await deleteStandard(row.id)
    ElMessage.success('已删除')
    await loadEntries()
  } catch { /* cancel or error */ }
}

// ── 爬取日志 ──
const logs = ref<any[]>([])
const logsPage = reactive({ page: 1, page_size: 20, total: 0 })
const logFilter = reactive({ region_id: undefined as number | undefined, status: '' })

async function loadLogs() {
  try {
    const res = await listCrawlLogs({
      region_id: logFilter.region_id,
      status: logFilter.status || undefined,
      page: logsPage.page,
      page_size: logsPage.page_size,
    })
    logs.value = res.items
    logsPage.total = res.total
  } catch { /* ignore */ }
}

async function triggerCrawl(regionId?: number) {
  try {
    const res = await apiTriggerCrawl(regionId)
    ElMessage.success(`爬取已触发 (${res.crawl_ids?.length || 0} 个任务)`)
    await loadLogs()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '触发失败')
  }
}

onMounted(async () => {
  await loadRegions()
  try {
    categories.value = await listCategories()
  } catch { /* ignore */ }
  await loadEntries()
  await loadLogs()
})
</script>

<style scoped>
.standard-manage { padding: 16px; }
.manage-card { margin-top: 16px; }
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; align-items: center; }
.pagination-wrap { margin-top: 12px; display: flex; justify-content: flex-end; }
</style>
