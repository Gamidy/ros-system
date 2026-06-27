<template>
  <div class="event-monitor-view">
    <!-- ═══════ 顶部标题 ═══════ -->
    <div class="em-header">
      <h2>📊 事件监控面板</h2>
      <el-button size="small" @click="refreshAll" :loading="loading">刷新</el-button>
    </div>

    <!-- ═══════ 桌面端: 左(类型概览) + 右(事件列表) / 移动端: 堆叠 ═══════ -->
    <el-row :gutter="16" class="em-body">
      <!-- 左栏: 事件类型统计概览 -->
      <el-col :xs="24" :md="8" :lg="7" class="em-left-col">
        <el-card shadow="never" class="type-overview-card">
          <template #header>
            <span style="font-weight: 600">📋 事件类型概览 ({{ typeTotal }})</span>
          </template>
          <div v-loading="typesLoading" class="type-list">
            <el-empty v-if="!typesLoading && eventTypes.length === 0" description="暂无事件类型" :image-size="50" />
            <div
              v-for="t in eventTypes"
              :key="t"
              class="type-item"
              :class="{ active: filterType === t }"
              @click="filterByType(t)"
            >
              <el-tag :type="tagType(t)" size="small" effect="plain">
                {{ t }}
              </el-tag>
              <el-tag v-if="t === filterType" type="warning" size="small" effect="dark" class="filter-badge">过滤中</el-tag>
            </div>
          </div>
          <div class="type-footer">
            <el-button v-if="filterType" link size="small" @click="clearTypeFilter">清除过滤</el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 右栏: 事件列表表格 -->
      <el-col :xs="24" :md="16" :lg="17" class="em-right-col">
        <el-card shadow="never" class="event-list-card">
          <template #header>
            <div class="event-list-header">
              <span style="font-weight: 600">📄 事件列表 ({{ totalEvents }})</span>
              <div class="filter-row">
                <el-select
                  v-model="filterType"
                  placeholder="事件类型"
                  clearable
                  size="small"
                  style="width: 150px"
                  @change="onFilterChange"
                >
                  <el-option
                    v-for="t in eventTypes"
                    :key="t"
                    :label="t"
                    :value="t"
                  />
                </el-select>
                <el-select
                  v-model="filterStatus"
                  placeholder="状态"
                  clearable
                  size="small"
                  style="width: 130px"
                  @change="onFilterChange"
                >
                  <el-option label="emitted" value="emitted" />
                  <el-option label="processed" value="processed" />
                  <el-option label="failed" value="failed" />
                  <el-option label="partial_failed" value="partial_failed" />
                </el-select>
              </div>
            </div>
          </template>

          <div v-loading="loading">
            <el-table
              :data="events"
              stripe
              style="width: 100%"
              @row-click="toggleRowExpand"
              :row-class-name="rowClass"
            >
              <el-table-column type="expand" width="1">
                <template #default="{ row }">
                  <div class="expanded-payload">
                    <div class="payload-meta">
                      <span class="meta-label">ID:</span> {{ row.id }}
                      <span class="meta-label" style="margin-left: 16px">Event Version:</span> {{ row.event_version || '-' }}
                      <span class="meta-label" style="margin-left: 16px">Saga ID:</span> {{ row.saga_id || '-' }}
                    </div>
                    <div class="payload-section" v-if="row.payload">
                      <div class="payload-label">📦 Payload:</div>
                      <pre class="payload-json">{{ JSON.stringify(row.payload, null, 2) }}</pre>
                    </div>
                    <div class="payload-section" v-if="row.state_snapshot">
                      <div class="payload-label">📸 State Snapshot:</div>
                      <pre class="payload-json">{{ JSON.stringify(row.state_snapshot, null, 2) }}</pre>
                    </div>
                    <div class="payload-section" v-if="row.handler_summary">
                      <div class="payload-label">⚙️ Handler Summary:</div>
                      <pre class="payload-json">{{ JSON.stringify(row.handler_summary, null, 2) }}</pre>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="event_type" label="事件类型" width="140">
                <template #default="{ row }">
                  <el-tag :type="tagType(row.event_type)" size="small">{{ row.event_type }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="plan_id" label="关联 ID (plan_id)" width="120" />
              <el-table-column prop="status" label="状态" width="120">
                <template #default="{ row }">
                  <el-tag :type="statusTagType(row.status)" size="small" effect="dark">
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="时间" min-width="160">
                <template #default="{ row }">
                  {{ formatTime(row.created_at) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" fixed="right">
                <template #default="{ row }">
                  <el-button link size="small" type="primary" @click.stop="toggleRowExpand(row)">
                    {{ expandedRows.has(row.id) ? '收起' : '详情' }}
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <el-empty v-if="!loading && events.length === 0" description="暂无事件数据" :image-size="60" style="margin: 40px 0" />

            <!-- 分页 -->
            <div class="pagination-wrap" v-if="totalPages > 1">
              <el-pagination
                v-model:current-page="currentPage"
                :page-size="pageSize"
                :total="totalEvents"
                layout="prev, pager, next, total"
                background
                small
                @current-change="fetchEvents"
              />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '../../api'

interface EventDto {
  id: number
  event_version?: string
  saga_id?: string
  payload?: Record<string, unknown>
  state_snapshot?: Record<string, unknown>
  handler_summary?: Record<string, unknown>
  event_type: string
  plan_id?: string | number
  status: string
  created_at: string
}

// ── Data ──
const events = ref<EventDto[]>([])
const eventTypes = ref<string[]>([])
const loading = ref(false)
const typesLoading = ref(false)
const totalEvents = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const filterType = ref<string | null>(null)
const filterStatus = ref<string | null>(null)
const expandedRows = ref<Set<number>>(new Set())

// computed
const totalPages = computed(() => Math.ceil(totalEvents.value / pageSize.value))
const typeTotal = computed(() => eventTypes.value.length)

// ── Helpers ──
function formatTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function tagType(type: string): string {
  const map: Record<string, string> = {
    created: 'success',
    updated: 'primary',
    deleted: 'danger',
    submitted: 'warning',
    approved: 'success',
    rejected: 'danger',
    reverted: 'info',
  }
  return map[type] || 'info'
}

function statusTagType(status: string): string {
  const map: Record<string, string> = {
    emitted: 'info',
    processed: 'success',
    failed: 'danger',
    partial_failed: 'warning',
  }
  return map[status] || 'info'
}

function rowClass({ row }: { row: EventDto }): string {
  return expandedRows.value.has(row.id) ? 'expanded-row' : ''
}

// ── API: 获取事件类型列表 ──
async function fetchEventTypes() {
  typesLoading.value = true
  try {
    const res = await api.get('/events/types')
    const data = res.data
    eventTypes.value = data?.types || []
  } catch {
    eventTypes.value = []
  } finally {
    typesLoading.value = false
  }
}

// ── API: 获取事件列表 ──
async function fetchEvents() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (filterType.value) params.event_type = filterType.value
    if (filterStatus.value) params.status = filterStatus.value

    const res = await api.get('/events', { params })
    const data = res.data
    events.value = data?.items || []
    totalEvents.value = data?.total || 0
  } catch {
    events.value = []
    totalEvents.value = 0
  } finally {
    loading.value = false
  }
}

// ── Events ──
function toggleRowExpand(row: EventDto) {
  const id = row.id
  if (expandedRows.value.has(id)) {
    expandedRows.value.delete(id)
  } else {
    expandedRows.value.add(id)
  }
  // Force reactivity
  expandedRows.value = new Set(expandedRows.value)
}

function filterByType(type: string) {
  filterType.value = filterType.value === type ? null : type
  onFilterChange()
}

function clearTypeFilter() {
  filterType.value = null
  onFilterChange()
}

function onFilterChange() {
  currentPage.value = 1
  fetchEvents()
}

async function refreshAll() {
  await Promise.all([fetchEventTypes(), fetchEvents()])
}

// ── Lifecycle ──
onMounted(() => {
  refreshAll()
})
</script>

<style scoped>
.event-monitor-view {
  padding: 0 4px;
}

.em-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.em-header h2 {
  margin: 0;
  font-size: 18px;
}

.em-body {
  min-height: 400px;
}

/* ── 左栏: 事件类型概览 ── */
.type-overview-card {
  border-radius: 8px;
  margin-bottom: 16px;
}
.type-list {
  max-height: 480px;
  overflow-y: auto;
}
.type-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}
.type-item:hover {
  background: #f5f7fa;
}
.type-item.active {
  background: #ecf5ff;
}
.filter-badge {
  flex-shrink: 0;
}
.type-footer {
  padding-top: 8px;
  border-top: 1px solid #ebeef5;
  margin-top: 8px;
  text-align: center;
}

/* ── 右栏: 事件列表 ── */
.event-list-card {
  border-radius: 8px;
}
.event-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.filter-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 16px;
  padding-bottom: 8px;
}

/* ── Expanded row payload ── */
.expanded-payload {
  padding: 12px 16px;
  background: #fafafa;
  border-radius: 6px;
}
.payload-meta {
  font-size: 12px;
  color: #606266;
  margin-bottom: 12px;
}
.meta-label {
  color: #909399;
  font-weight: 500;
}
.payload-section {
  margin-top: 8px;
}
.payload-label {
  font-size: 12px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}
.payload-json {
  background: #f0f2f5;
  padding: 10px;
  border-radius: 4px;
  font-size: 11px;
  line-height: 1.5;
  max-height: 250px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  color: #303133;
}

/* ── Mobile adjustments ── */
@media (max-width: 767px) {
  .em-header h2 {
    font-size: 16px;
  }
  .event-list-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .filter-row {
    width: 100%;
  }
  .filter-row .el-select {
    flex: 1;
  }
}
</style>
