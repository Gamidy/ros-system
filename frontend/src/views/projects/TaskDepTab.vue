<template>
  <div class="dep-tab">
    <div class="toolbar">
      <el-button type="primary" size="small" @click="showAddDialog = true">新建依赖</el-button>
      <span class="dep-count">共 {{ deps.length }} 条依赖关系</span>
    </div>

    <el-table :data="deps" stripe border size="small" style="width: 100%" v-if="deps.length > 0">
      <el-table-column prop="task_title" label="当前任务" min-width="180" />
      <el-table-column label="依赖类型" width="140">
        <template #default="{ row }">
          <el-tag size="small">{{ depTypeLabel(row.dep_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="depends_on_title" label="前置任务" min-width="180" />
      <el-table-column prop="lag_days" label="滞后(天)" width="80" />
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" type="danger" @click="removeDep(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else description="暂无依赖关系" />

    <el-dialog v-model="showAddDialog" title="新建依赖" width="400" destroy-on-close>
      <el-form label-width="80" size="small">
        <el-form-item label="当前任务">
          <el-select v-model="form.task_id" filterable placeholder="选择任务" style="width:100%">
            <el-option v-for="t in allTasks" :key="t.id" :label="t.title" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="依赖类型">
          <el-select v-model="form.dep_type">
            <el-option label="完成→开始" value="finish_to_start" />
            <el-option label="开始→开始" value="start_to_start" />
            <el-option label="完成→完成" value="finish_to_finish" />
          </el-select>
        </el-form-item>
        <el-form-item label="前置任务">
          <el-select v-model="form.depends_on_task_id" filterable placeholder="选择前置任务" style="width:100%">
            <el-option v-for="t in allTasks" :key="t.id" :disabled="t.id === form.task_id" :label="t.title" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="滞后(天)">
          <el-input-number v-model="form.lag_days" :min="0" :max="365" size="small" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveDep">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const props = defineProps<{ pid: number }>()

interface Dependency {
  id: number; task_id: number; task_title: string
  depends_on_task_id: number; depends_on_title: string
  dep_type: string; lag_days: number
}

const deps = ref<Dependency[]>([])
const allTasks = ref<any[]>([])
const showAddDialog = ref(false)
const form = ref({ task_id: null, depends_on_task_id: null, dep_type: 'finish_to_start', lag_days: 0 })

function depTypeLabel(t: string): string {
  return { finish_to_start: '完成→开始', start_to_start: '开始→开始', finish_to_finish: '完成→完成' }[t] || t
}

async function fetchAll() {
  const [depRes, taskRes] = await Promise.all([
    api.get(`/projects/${props.pid}/tasks/dependencies`).catch(() => ({ data: [] })),
    api.get(`/projects/${props.pid}/tasks`).catch(() => ({ data: [] })),
  ])
  deps.value = depRes.data || []
  allTasks.value = taskRes.data || []
}

async function saveDep() {
  if (!form.value.task_id || !form.value.depends_on_task_id) {
    ElMessage.warning('请选择任务')
    return
  }
  try {
    await api.post(`/projects/${props.pid}/tasks/dependencies`, null, {
      params: { task_id: form.value.task_id, depends_on_task_id: form.value.depends_on_task_id, dep_type: form.value.dep_type, lag_days: form.value.lag_days },
    })
    ElMessage.success('依赖已创建')
    showAddDialog.value = false
    form.value = { task_id: null, depends_on_task_id: null, dep_type: 'finish_to_start', lag_days: 0 }
    await fetchAll()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '创建失败')
  }
}

async function removeDep(dep: Dependency) {
  try {
    await api.delete(`/projects/${props.pid}/tasks/dependencies/${dep.id}`)
    ElMessage.success('已删除')
    await fetchAll()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

onMounted(fetchAll)
</script>

<style scoped>
.dep-tab { width: 100%; }
.toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; }
.dep-count { font-size: 12px; color: #909399; margin-left: auto; }
</style>
