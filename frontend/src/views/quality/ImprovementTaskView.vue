<template>
  <div class="page">
    <el-card shadow="never" class="main-card">
      <template #header>
        <div class="card-header">
          <span>改善任务管理</span>
          <el-button type="primary" size="small" @click="openCreateDialog" :disabled="!selectedReviewId">
            新建任务
          </el-button>
        </div>
      </template>

      <el-row :gutter="16" style="min-height: 500px">
        <!-- 左侧：复盘选择列表 -->
        <el-col :span="6" style="min-width: 280px">
          <div class="review-panel">
            <div class="panel-title">复盘列表</div>
            <el-input
              v-model="reviewSearch"
              placeholder="搜索复盘..."
              size="small"
              clearable
              style="margin-bottom: 8px"
            />
            <div class="review-list" v-loading="reviewLoading">
              <div
                v-for="r in filteredReviews"
                :key="r.id"
                class="review-item"
                :class="{ active: selectedReviewId === r.id }"
                @click="selectReview(r)"
              >
                <div class="review-name">{{ r.plan_name }}</div>
                <div class="review-meta">
                  <span>{{ r.plan_series }}</span>
                  <span>{{ r.review_date }}</span>
                </div>
                <el-tag
                  :type="ratingTag(r.rating)"
                  size="small"
                  effect="plain"
                >
                  {{ ratingLabel(r.rating) }}
                </el-tag>
              </div>
              <el-empty v-if="!reviewLoading && filteredReviews.length === 0" :description="reviews.length === 0 ? '暂无复盘' : '无匹配结果'" />
            </div>
          </div>
        </el-col>

        <!-- 右侧：改善任务看板 -->
        <el-col :span="18">
          <div v-if="!selectedReviewId" class="placeholder">
            <el-empty description="请从左侧选择一个复盘" />
          </div>
          <div v-else>
            <el-row :gutter="12" class="board-row">
              <el-col :span="6" v-for="col in columns" :key="col.key">
                <div class="kanban-column">
                  <div class="column-header">
                    <span class="column-title">{{ col.label }}</span>
                    <el-tag size="small" type="info" effect="plain" round>
                      {{ groupedTasks[col.key]?.length || 0 }}
                    </el-tag>
                  </div>
                  <div
                    class="column-body"
                    v-loading="taskLoading"
                  >
                    <div
                      v-for="t in groupedTasks[col.key] || []"
                      :key="t.id"
                      class="task-card"
                      @click="openEditDialog(t)"
                    >
                      <div class="task-desc">{{ truncate(t.description, 50) }}</div>
                      <div class="task-meta">
                        <span class="task-assignee">👤 {{ t.assigned_to || '-' }}</span>
                        <el-tag
                          :type="priorityType(t.priority)"
                          size="small"
                          effect="dark"
                        >
                          {{ priorityLabel(t.priority) }}
                        </el-tag>
                      </div>
                      <div class="task-due" v-if="t.due_date">
                        📅 {{ t.due_date }}
                      </div>
                    </div>
                    <el-empty
                      v-if="!taskLoading && (groupedTasks[col.key] || []).length === 0"
                      :description="col.emptyText"
                      :image-size="60"
                    />
                  </div>
                </div>
              </el-col>
            </el-row>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 新建/编辑任务弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingTaskId ? '编辑任务' : '新建任务'"
      width="520px"
      destroy-on-close
    >
      <el-form :model="form" label-width="90px" size="small">
        <el-form-item label="描述" required>
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入改善任务描述"
          />
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="form.assigned_to" placeholder="负责人姓名" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="优先级">
              <el-select v-model="form.priority" style="width: 100%">
                <el-option label="高" value="high" />
                <el-option label="中" value="medium" />
                <el-option label="低" value="low" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="截止日期">
              <el-date-picker
                v-model="form.due_date"
                type="date"
                style="width: 100%"
                value-format="YYYY-MM-DD"
                placeholder="选择日期"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="状态" v-if="editingTaskId">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="待处理" value="open" />
            <el-option label="进行中" value="in_progress" />
            <el-option label="已完成" value="resolved" />
            <el-option label="已关闭" value="closed" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" @click="dialogVisible = false">取消</el-button>
        <el-button size="small" type="primary" :loading="saving" @click="saveTask">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

// --- 类型定义 ---
interface Review {
  id: number
  plan_id: number
  plan_name: string
  plan_series: string
  review_date: string
  rating: string
}

interface TaskItem {
  id: number
  review_id: number
  description: string
  assigned_to: string
  priority: string
  status: string
  due_date: string | null
  resolved_at: string | null
}

interface ColumnDef {
  key: string
  label: string
  emptyText: string
}

// --- 看板列定义 ---
const columns: ColumnDef[] = [
  { key: 'open', label: '待处理', emptyText: '暂无待处理任务' },
  { key: 'in_progress', label: '进行中', emptyText: '暂无进行中任务' },
  { key: 'resolved', label: '已完成', emptyText: '暂无已完成任务' },
  { key: 'closed', label: '已关闭', emptyText: '暂无已关闭任务' },
]

// --- 状态 ---
const reviews = ref<Review[]>([])
const selectedReviewId = ref<number | null>(null)
const selectedReviewName = ref('')
const reviewLoading = ref(false)
const taskLoading = ref(false)
const tasks = ref<TaskItem[]>([])
const dialogVisible = ref(false)
const editingTaskId = ref<number | null>(null)
const saving = ref(false)
const reviewSearch = ref('')

const form = ref<{
  description: string
  assigned_to: string
  priority: string
  status: string
  due_date: string | null
}>({
  description: '',
  assigned_to: '',
  priority: 'medium',
  status: 'open',
  due_date: null,
})

// --- 计算属性 ---
const filteredReviews = computed(() => {
  const q = reviewSearch.value.trim().toLowerCase()
  if (!q) return reviews.value
  return reviews.value.filter(
    (r) =>
      r.plan_name.toLowerCase().includes(q) ||
      r.plan_series.toLowerCase().includes(q)
  )
})

const groupedTasks = computed(() => {
  const map: Record<string, TaskItem[]> = {
    open: [],
    in_progress: [],
    resolved: [],
    closed: [],
  }
  for (const t of tasks.value) {
    const key = t.status || 'open'
    if (map[key]) {
      map[key].push(t)
    } else {
      map.open.push(t)
    }
  }
  return map
})

// --- 辅助函数 ---
function truncate(text: string, len: number): string {
  if (!text) return ''
  return text.length > len ? text.slice(0, len) + '...' : text
}

function ratingTag(rating: string): string {
  const m: Record<string, string> = { A: 'success', B: 'warning', C: 'danger', D: 'info' }
  return m[rating] || 'info'
}

function ratingLabel(rating: string): string {
  const m: Record<string, string> = { A: 'A级', B: 'B级', C: 'C级', D: 'D级' }
  return m[rating] || rating
}

function priorityType(p: string): string {
  const m: Record<string, string> = { high: 'danger', medium: 'warning', low: 'primary' }
  return m[p] || 'info'
}

function priorityLabel(p: string): string {
  const m: Record<string, string> = { high: '高', medium: '中', low: '低' }
  return m[p] || p
}

// --- API ---
async function fetchReviews() {
  reviewLoading.value = true
  try {
    const res = await api.get('/reviews')
    reviews.value = res.data?.items || res.data || []
  } catch {
    ElMessage.error('获取复盘列表失败')
  } finally {
    reviewLoading.value = false
  }
}

async function selectReview(r: Review) {
  selectedReviewId.value = r.id
  selectedReviewName.value = r.plan_name
  await fetchTasks(r.id)
}

async function fetchTasks(reviewId: number) {
  taskLoading.value = true
  try {
    const res = await api.get(`/reviews/${reviewId}/tasks`)
    tasks.value = res.data || []
  } catch {
    ElMessage.error('获取改善任务失败')
    tasks.value = []
  } finally {
    taskLoading.value = false
  }
}

function openCreateDialog() {
  editingTaskId.value = null
  form.value = {
    description: '',
    assigned_to: '',
    priority: 'medium',
    status: 'open',
    due_date: null,
  }
  dialogVisible.value = true
}

function openEditDialog(task: TaskItem) {
  editingTaskId.value = task.id
  form.value = {
    description: task.description,
    assigned_to: task.assigned_to,
    priority: task.priority,
    status: task.status,
    due_date: task.due_date,
  }
  dialogVisible.value = true
}

async function saveTask() {
  if (!form.value.description) {
    ElMessage.warning('请输入任务描述')
    return
  }
  saving.value = true
  try {
    const payload = { ...form.value }
    if (editingTaskId.value) {
      await api.put(`/tasks/${editingTaskId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      await api.post(`/reviews/${selectedReviewId.value}/tasks`, payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    if (selectedReviewId.value) {
      await fetchTasks(selectedReviewId.value)
    }
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// --- 初始化 ---
onMounted(fetchReviews)
</script>

<style scoped>
.page {
  padding: 0;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}
.main-card {
  min-height: 600px;
}

/* 左侧复盘面板 */
.review-panel {
  border-right: 1px solid #ebeef5;
  padding-right: 12px;
  height: 100%;
}
.panel-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 8px;
  color: #303133;
}
.review-list {
  max-height: 540px;
  overflow-y: auto;
}
.review-item {
  padding: 10px 8px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 6px;
  border: 1px solid transparent;
  transition: all 0.2s;
}
.review-item:hover {
  background: #f5f7fa;
  border-color: #e4e7ed;
}
.review-item.active {
  background: #fef0ef;
  border-color: #d97757;
}
.review-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
  line-height: 1.4;
}
.review-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

/* 右侧看板 */
.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
}
.board-row {
  height: 100%;
}
.kanban-column {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px;
  min-height: 480px;
  display: flex;
  flex-direction: column;
}
.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid #e4e7ed;
}
.column-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.column-body {
  flex: 1;
  min-height: 200px;
}
.task-card {
  background: #fff;
  border-radius: 6px;
  padding: 10px;
  margin-bottom: 8px;
  cursor: pointer;
  border: 1px solid #ebeef5;
  transition: all 0.2s;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.task-card:hover {
  border-color: #d97757;
  box-shadow: 0 2px 8px rgba(217, 119, 87, 0.12);
}
.task-desc {
  font-size: 13px;
  color: #303133;
  line-height: 1.5;
  margin-bottom: 8px;
}
.task-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.task-assignee {
  font-size: 12px;
  color: #909399;
}
.task-due {
  font-size: 12px;
  color: #909399;
}
</style>
