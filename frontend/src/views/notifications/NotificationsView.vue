<template>
  <div class="notifications-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>通知中心</h2>
      <div class="header-actions">
        <el-button
          :disabled="!hasSelection"
          type="primary"
          plain
          size="small"
          @click="batchMarkRead"
        >
          批量已读
        </el-button>
        <el-button
          :disabled="!hasSelection"
          type="danger"
          plain
          size="small"
          @click="batchDelete"
        >
          批量删除
        </el-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" :model="filters" size="small" label-width="auto">
        <el-form-item label="渠道">
          <el-select
            v-model="filters.channel"
            placeholder="全部渠道"
            clearable
            style="width: 140px"
            @change="onFilterChange"
          >
            <el-option
              v-for="(label, key) in CHANNEL_LABELS"
              :key="key"
              :label="label"
              :value="key"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="状态">
          <el-select
            v-model="filters.is_read"
            placeholder="全部状态"
            clearable
            style="width: 120px"
            @change="onFilterChange"
          >
            <el-option label="未读" :value="false" />
            <el-option label="已读" :value="true" />
          </el-select>
        </el-form-item>

        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DDTHH:mm:ss"
            :shortcuts="dateShortcuts"
            @change="onDateChange"
          />
        </el-form-item>

        <el-form-item label="搜索">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索标题或内容..."
            clearable
            style="width: 200px"
            @clear="onFilterChange"
            @keyup.enter="onFilterChange"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 通知列表 -->
    <el-card shadow="never" class="list-card">
      <el-table
        :data="pageData.items"
        v-loading="loading"
        stripe
        border
        style="width: 100%"
        @selection-change="onSelectionChange"
        @row-click="handleRowClick"
      >
        <el-table-column type="selection" width="45" />

        <el-table-column label="渠道" width="100">
          <template #default="{ row }">
            <el-tag :type="channelTagType(row.channel)" size="small" effect="plain">
              {{ CHANNEL_LABELS[row.channel] || row.channel }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small" effect="plain" :type="eventTagType(row.title)">
              {{ guessEventType(row.title) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="通知内容" min-width="300">
          <template #default="{ row }">
            <div class="notif-content">
              <div class="notif-title" :class="{ unread: !row.is_read }">
                {{ row.title }}
              </div>
              <div class="notif-body" v-if="row.content">
                {{ truncate(row.content, 120) }}
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="时间" width="170">
          <template #default="{ row }">
            <span class="notif-time">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_read ? 'info' : 'warning'" size="small">
              {{ row.is_read ? '已读' : '未读' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty v-if="!loading && pageData.items.length === 0" description="暂无通知" />

      <!-- 分页 -->
      <div class="pagination-wrapper" v-if="pageData.total > 0">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pageData.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="onPageChange"
          @current-change="onPageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import type { NotificationItem, NotificationPage } from '../../api/notification'
import {
  CHANNEL_LABELS,
  fetchNotifications,
  deleteNotificationsBatch,
  markNotificationRead,
} from '../../api/notification'

// ── 响应式状态 ──────────────────────────────────────────────────────

const loading = ref(false)
const selectedRows = ref<NotificationItem[]>([])

const pageData = reactive<NotificationPage>({
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
  total_pages: 0,
})

const currentPage = ref(1)
const pageSize = ref(20)

const dateRange = ref<[string, string] | null>(null)

const filters = reactive({
  channel: '',
  is_read: null as boolean | null,
  keyword: '',
  date_from: null as string | null,
  date_to: null as string | null,
})

const dateShortcuts = [
  { text: '今天', value: () => {
    const start = new Date()
    start.setHours(0, 0, 0, 0)
    const end = new Date()
    return [start, end] as [Date, Date]
  }},
  { text: '最近7天', value: () => {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - 7)
    return [start, end] as [Date, Date]
  }},
  { text: '最近30天', value: () => {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - 30)
    return [start, end] as [Date, Date]
  }},
]

const hasSelection = computed(() => selectedRows.value.length > 0)

// ── 辅助函数 ────────────────────────────────────────────────────────

function channelTagType(channel: string): string {
  const map: Record<string, string> = {
    websocket: '',
    wecom: 'success',
    dingtalk: 'warning',
    email: 'info',
  }
  return map[channel] || ''
}

function eventTagType(title: string): string {
  if (title.includes('审批') || title.includes('approval')) return 'primary'
  if (title.includes('预警') || title.includes('alert')) return 'danger'
  if (title.includes('评审') || title.includes('review')) return 'warning'
  if (title.includes('策划') || title.includes('plan')) return 'success'
  return ''
}

function guessEventType(title: string): string {
  if (title.includes('审批') || title.includes('approval')) return '审批'
  if (title.includes('预警') || title.includes('alert') || title.includes('超期')) return '预警'
  if (title.includes('评审') || title.includes('review')) return '评审'
  if (title.includes('策划') || title.includes('plan')) return '策划'
  return '通知'
}

function truncate(text: string, maxLen: number): string {
  if (!text) return ''
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
}

function formatTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// ── 数据加载 ────────────────────────────────────────────────────────

async function loadData(): Promise<void> {
  loading.value = true
  try {
    // 默认只查当前用户的通知
    const result = await fetchNotifications({
      target_user: '',
      channel: filters.channel || undefined,
      is_read: filters.is_read,
      keyword: filters.keyword || undefined,
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
      page: currentPage.value,
      page_size: pageSize.value,
    })
    pageData.items = result.items
    pageData.total = result.total
    pageData.page = result.page
    pageData.page_size = result.page_size
    pageData.total_pages = result.total_pages
  } catch {
    // 错误由 api 拦截器处理
  } finally {
    loading.value = false
  }
}

// ── 事件处理 ────────────────────────────────────────────────────────

function onFilterChange(): void {
  currentPage.value = 1
  loadData()
}

function onDateChange(): void {
  if (dateRange.value && dateRange.value[0] && dateRange.value[1]) {
    filters.date_from = dateRange.value[0]
    filters.date_to = dateRange.value[1]
  } else {
    filters.date_from = null
    filters.date_to = null
  }
  onFilterChange()
}

function onPageChange(): void {
  loadData()
}

function onSelectionChange(rows: NotificationItem[]): void {
  selectedRows.value = rows
}

async function handleRowClick(row: NotificationItem): Promise<void> {
  // 点击行切换已读状态
  if (!row.is_read) {
    try {
      await markNotificationRead(row.id)
      row.is_read = true
    } catch {
      // 静默
    }
  }
}

async function batchMarkRead(): Promise<void> {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择通知')
    return
  }
  try {
    await Promise.all(
      selectedRows.value.map((n) => markNotificationRead(n.id)),
    )
    ElMessage.success(`已标记 ${selectedRows.value.length} 条为已读`)
    await loadData()
    selectedRows.value = []
  } catch {
    ElMessage.error('批量已读失败')
  }
}

async function batchDelete(): Promise<void> {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择通知')
    return
  }
  const ids = selectedRows.value.map((n) => n.id)
  try {
    const res = await deleteNotificationsBatch(ids)
    ElMessage.success(`已删除 ${res.deleted_count} 条通知`)
    await loadData()
    selectedRows.value = []
  } catch {
    ElMessage.error('批量删除失败')
  }
}

// 监听 filters.keyword 变化延迟搜索
let debounceTimer: ReturnType<typeof setTimeout> | null = null
watch(
  () => filters.keyword,
  () => {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      onFilterChange()
    }, 400)
  },
)

// ── 生命周期 ────────────────────────────────────────────────────────

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.notifications-view {
  padding: 20px;
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
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.filter-card {
  margin-bottom: 16px;
}

.filter-card :deep(.el-form) {
  margin-bottom: -18px;
}

.list-card {
  min-height: 400px;
}

.notif-content {
  line-height: 1.5;
}

.notif-title {
  font-size: 14px;
  color: var(--c-text-primary, #303133);
}

.notif-title.unread {
  font-weight: 600;
}

.notif-body {
  font-size: 12px;
  color: var(--c-text-secondary, #909399);
  margin-top: 2px;
  line-height: 1.4;
}

.notif-time {
  font-size: 13px;
  color: var(--c-text-secondary, #909399);
  white-space: nowrap;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
