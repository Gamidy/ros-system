<template>
  <div class="kanban-tab">
    <!-- KPI row -->
    <div class="kpi-row">
      <el-statistic title="总任务" :value="stats.total" />
      <el-statistic title="待办" :value="stats.todo" />
      <el-statistic title="进行中" :value="stats.in_progress" />
      <el-statistic title="已完成" :value="stats.done" />
      <el-statistic title="阻塞" :value="stats.blocked" />
      <div class="toolbar-right">
        <el-button size="small" @click="switchView">切换表格视图</el-button>
        <el-button type="primary" size="small" @click="$emit('new-task')">新建任务</el-button>
      </div>
    </div>

    <!-- Kanban Board -->
    <div class="kanban-board">
      <div v-for="col in columns" :key="col.key" class="kanban-column"
        @dragover.prevent="onDragOver($event, col.key)"
        @dragleave="onDragLeave($event)"
        @drop="onDrop($event, col.key)">
        <div class="column-header" :style="{ borderTopColor: col.color }">
          <span class="column-title">{{ col.label }}</span>
          <el-tag size="small" :type="col.tagType">{{ col.tasks.length }}</el-tag>
        </div>

        <div class="column-body">
          <div v-for="t in col.tasks" :key="t.id" class="task-card"
            :class="{ 'is-dragging': draggingId === t.id }"
            draggable="true"
            @dragstart="onDragStart(t)"
            @dragend="onDragEnd">
            <div class="card-top">
              <span class="card-title">{{ t.title }}</span>
              <el-tag :type="priorityTag(t.priority)" size="small" class="priority-tag">{{ priorityLabel(t.priority) }}</el-tag>
            </div>
            <div class="card-meta" v-if="t.assignee || t.due_date">
              <span v-if="t.assignee" class="meta-assignee">
                <el-icon size="12"><User /></el-icon> {{ t.assignee }}
              </span>
              <span v-if="t.due_date" class="meta-due" :class="{ 'is-overdue': isOverdue(t.due_date) && t.status !== 'done' }">
                <el-icon size="12"><Calendar /></el-icon> {{ t.due_date }}
              </span>
            </div>
            <div v-if="t.description" class="card-desc">{{ t.description }}</div>
          </div>
          <div v-if="col.tasks.length === 0" class="empty-column">
            拖拽任务到此处
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { User, Calendar } from '@element-plus/icons-vue'

interface TaskItem {
  id: number
  title: string
  assignee?: string | null
  status: string
  priority: string
  due_date?: string | null
  description?: string | null
}

interface ColumnDef {
  key: string
  label: string
  color: string
  tagType: string
  tasks: TaskItem[]
}

const props = defineProps<{
  tasks: TaskItem[]
}>()

const emit = defineEmits<{
  (e: 'new-task'): void
  (e: 'edit-task', task: TaskItem): void
  (e: 'update-status', taskId: number, status: string): void
  (e: 'switch-view'): void
}>()

// ── Columns ──
const columns = computed<ColumnDef[]>(() => [
  { key: 'todo', label: '待办', color: '#909399', tagType: 'info', tasks: props.tasks.filter(t => t.status === 'todo') },
  { key: 'in_progress', label: '进行中', color: '#409eff', tagType: 'primary', tasks: props.tasks.filter(t => t.status === 'in_progress') },
  { key: 'done', label: '已完成', color: '#67c23a', tagType: 'success', tasks: props.tasks.filter(t => t.status === 'done') },
  { key: 'blocked', label: '阻塞', color: '#f56c6c', tagType: 'danger', tasks: props.tasks.filter(t => t.status === 'blocked') },
])

const stats = computed(() => ({
  total: props.tasks.length,
  todo: props.tasks.filter(t => t.status === 'todo').length,
  in_progress: props.tasks.filter(t => t.status === 'in_progress').length,
  done: props.tasks.filter(t => t.status === 'done').length,
  blocked: props.tasks.filter(t => t.status === 'blocked').length,
}))

// ── Drag & Drop ──
const draggingId = ref<number | null>(null)

function onDragStart(t: TaskItem) {
  draggingId.value = t.id
}

function onDragEnd() {
  draggingId.value = null
}

function onDragOver(e: DragEvent, _colKey: string) {
  const el = e.currentTarget as HTMLElement
  el.classList.add('drag-over')
}

function onDragLeave(e: DragEvent) {
  const el = e.currentTarget as HTMLElement
  el.classList.remove('drag-over')
}

async function onDrop(e: DragEvent, targetStatus: string) {
  const el = e.currentTarget as HTMLElement
  el.classList.remove('drag-over')

  if (draggingId.value === null) return
  const task = props.tasks.find(t => t.id === draggingId.value)
  if (!task || task.status === targetStatus) {
    draggingId.value = null
    return
  }
  emit('update-status', draggingId.value, targetStatus)
  draggingId.value = null
}

// ── Helpers ──
function priorityTag(p: string): string {
  return { low: 'info', medium: '', high: 'warning', urgent: 'danger' }[p] || 'info'
}
function priorityLabel(p: string): string {
  return { low: '低', medium: '中', high: '高', urgent: '紧急' }[p] || p
}
function isOverdue(d: string | null | undefined): boolean {
  if (!d) return false
  return new Date(d) < new Date(new Date().toDateString())
}

function switchView() {
  emit('switch-view')
}
</script>

<style scoped>
.kanban-tab { width: 100%; }
.kpi-row {
  display: flex; gap: 24px; align-items: center; margin-bottom: 16px; flex-wrap: wrap;
}
.kpi-row :deep(.el-statistic) { text-align: center; }
.kpi-row :deep(.el-statistic__head) { font-size: 12px; color: #909399; }
.kpi-row :deep(.el-statistic__content) { font-size: 20px; font-weight: 700; color: #303133; }
.toolbar-right { margin-left: auto; display: flex; gap: 8px; }

.kanban-board {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  min-height: 400px;
}

.kanban-column {
  background: #f5f7fa;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  min-height: 300px;
  transition: background 0.2s;
}
.kanban-column.drag-over {
  background: #e6f1ff;
  outline: 2px dashed #409eff;
  outline-offset: -2px;
}

.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px 8px;
  border-top: 3px solid #909399;
  border-radius: 8px 8px 0 0;
}
.column-title { font-weight: 600; font-size: 14px; color: #303133; }

.column-body {
  padding: 8px 10px 12px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 10px 12px;
  cursor: grab;
  transition: all 0.15s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.task-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  border-color: #c0c4cc;
}
.task-card:active { cursor: grabbing; }
.task-card.is-dragging {
  opacity: 0.5;
  transform: rotate(2deg);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 6px;
}
.card-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  line-height: 1.3;
  word-break: break-word;
}
.priority-tag { flex-shrink: 0; }

.card-meta {
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: #909399;
  margin-bottom: 4px;
}
.meta-assignee, .meta-due {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.meta-due.is-overdue {
  color: #f56c6c;
  font-weight: 600;
}

.card-desc {
  font-size: 11px;
  color: #909399;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.empty-column {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 80px;
  color: #c0c4cc;
  font-size: 12px;
  border: 1px dashed #dcdfe6;
  border-radius: 6px;
}

@media (max-width: 900px) {
  .kanban-board { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .kanban-board { grid-template-columns: 1fr; }
}
</style>
