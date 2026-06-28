<template>
  <div class="wbs-tab">
    <div class="toolbar">
      <el-button type="primary" size="small" @click="$emit('new-task')">新建任务</el-button>
      <el-button size="small" @click="fetchTree">刷新</el-button>
      <span class="tree-info" v-if="stats">共 {{ stats.total_tasks }} 个任务，{{ stats.root_count }} 个根节点</span>
    </div>

    <div v-if="loading" class="loading-center"><el-spinner :size="32" /></div>

    <el-tree
      v-else
      :data="treeData"
      :props="{ children: 'children', label: 'title' }"
      node-key="id"
      default-expand-all
      :expand-on-click-node="false"
      class="wbs-tree"
    >
      <template #default="{ node, data }">
        <div class="tree-node">
          <span class="node-indent" v-if="node.level > 1">
            <span v-for="i in node.level - 1" :key="i" class="indent-space" />
            <span class="indent-line" />
          </span>
          <span class="node-toggle" @click="handleToggle(node)">
            <el-icon v-if="node.isLeaf" size="12" style="visibility:hidden"><Minus /></el-icon>
            <el-icon v-else size="12" :class="{ 'is-expanded': node.expanded }">
              <CaretRight />
            </el-icon>
          </span>

          <span class="node-title" :class="{ 'is-parent': !node.isLeaf }">{{ data.title }}</span>

          <el-tag :type="priorityTag(data.priority)" size="small" class="node-tag">{{ priorityLabel(data.priority) }}</el-tag>
          <el-tag :type="statusTag(data.status)" size="small" class="node-tag">{{ statusLabel(data.status) }}</el-tag>

          <span v-if="data.assignee" class="node-assignee">
            <el-icon size="11"><User /></el-icon>{{ data.assignee }}
          </span>
          <span v-if="data.due_date" class="node-date" :class="{ overdue: isOverdue(data.due_date) && data.status !== 'done' }">
            <el-icon size="11"><Calendar /></el-icon>{{ data.due_date }}
          </span>

          <!-- Child progress bar for parent nodes -->
          <span v-if="!node.isLeaf" class="node-progress">
            <el-progress
              :percentage="calcPercent(data)"
              :stroke-width="6"
              :width="60"
              :color="progressColor(calcPercent(data))"
            />
          </span>

          <span class="node-actions">
            <el-button text size="small" @click.stop="addChild(data)">+子任务</el-button>
            <el-button text size="small" type="danger" @click.stop="removeTask(data)">删除</el-button>
          </span>
        </div>
      </template>
    </el-tree>

    <el-empty v-if="!loading && treeData.length === 0" description="暂无任务，点击上方新建" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CaretRight, Minus, User, Calendar } from '@element-plus/icons-vue'
import api from '../../api'

const props = defineProps<{
  pid: number
}>()

const emit = defineEmits<{
  (e: 'new-task'): void
}>()

interface TreeNode {
  id: number
  title: string
  status: string
  priority: string
  assignee?: string | null
  due_date?: string | null
  children: TreeNode[]
  [key: string]: any
}

const loading = ref(true)
const treeData = ref<TreeNode[]>([])
const stats = ref<{ total_tasks: number; root_count: number } | null>(null)

async function fetchTree() {
  loading.value = true
  try {
    const res = await api.get(`/projects/${props.pid}/tasks/tree`)
    treeData.value = res.data.tree || []
    stats.value = res.data.stats || null
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载WBS树失败')
  } finally {
    loading.value = false
  }
}

function handleToggle(node: any) {
  node.expanded = !node.expanded
}

async function addChild(parent: TreeNode) {
  const title = prompt('请输入子任务名称：')
  if (!title?.trim()) return
  try {
    await api.post(`/projects/${props.pid}/tasks`, { title, parent_task_id: parent.id })
    ElMessage.success('子任务已创建')
    await fetchTree()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '创建失败')
  }
}

async function removeTask(data: TreeNode) {
  try {
    await ElMessageBox.confirm(`确定删除「${data.title}」？${data.children?.length ? '子任务也将被删除。' : ''}`, '确认删除')
    await api.delete(`/projects/${props.pid}/tasks/${data.id}`)
    ElMessage.success('已删除')
    await fetchTree()
  } catch { /* cancelled */ }
}

function calcPercent(data: TreeNode): number {
  const count = (n: TreeNode): { t: number; d: number } => {
    let t = 1, d = n.status === 'done' ? 1 : 0
    for (const c of (n.children || [])) {
      const r = count(c)
      t += r.t; d += r.d
    }
    return { t, d }
  }
  const r = count(data)
  return r.t > 0 ? Math.round(r.d / r.t * 100) : 0
}

function progressColor(pct: number): string {
  return pct >= 80 ? '#67c23a' : pct >= 50 ? '#e6a23c' : '#409eff'
}

function priorityTag(p: string): string { return { low: 'info', medium: '', high: 'warning', urgent: 'danger' }[p] || 'info' }
function priorityLabel(p: string): string { return { low: '低', medium: '中', high: '高', urgent: '紧急' }[p] || p }
function statusTag(s: string): string { return { todo: 'info', in_progress: 'primary', done: 'success', blocked: 'danger' }[s] || 'info' }
function statusLabel(s: string): string { return { todo: '待办', in_progress: '进行中', done: '已完成', blocked: '阻塞' }[s] || s }
function isOverdue(d: string | null | undefined): boolean {
  if (!d) return false; return new Date(d) < new Date(new Date().toDateString())
}

onMounted(fetchTree)
</script>

<style scoped>
.wbs-tab { width: 100%; }
.toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; }
.tree-info { font-size: 12px; color: #909399; margin-left: auto; }
.loading-center { display: flex; justify-content: center; padding: 60px 0; }

.wbs-tree { font-size: 13px; }
.wbs-tree :deep(.el-tree-node__content) { height: auto; padding: 4px 0; }

.tree-node {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 8px; width: 100%;
  border-radius: 4px; transition: background 0.1s;
}
.tree-node:hover { background: #f5f7fa; }

.node-indent { display: inline-flex; align-items: center; gap: 0; }
.indent-space { display: inline-block; width: 18px; }
.indent-line { display: inline-block; width: 14px; border-left: 1px solid #dcdfe6; height: 1px; margin-bottom: 8px; }

.node-toggle { cursor: pointer; width: 14px; display: inline-flex; align-items: center; }
.node-toggle .is-expanded { transform: rotate(90deg); transition: transform 0.15s; }

.node-title { font-weight: 600; color: #303133; }
.node-title.is-parent { color: #409eff; }
.node-tag { margin-left: 4px; }
.node-assignee { font-size: 11px; color: #909399; display: inline-flex; align-items: center; gap: 2px; margin-left: 8px; }
.node-date { font-size: 11px; color: #909399; display: inline-flex; align-items: center; gap: 2px; margin-left: 8px; }
.node-date.overdue { color: #f56c6c; font-weight: 600; }
.node-progress { margin-left: 8px; }
.node-actions { margin-left: auto; flex-shrink: 0; opacity: 0.4; transition: opacity 0.15s; }
.tree-node:hover .node-actions { opacity: 1; }
</style>
