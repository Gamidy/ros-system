<template>
  <div class="time-tab">
    <div class="toolbar">
      <el-button type="primary" size="small" @click="showAdd = true">记录工时</el-button>
    </div>

    <el-table :data="entries" stripe border size="small" style="width:100%">
      <el-table-column prop="entry_date" label="日期" width="100" />
      <el-table-column prop="task_title" label="任务" min-width="160" />
      <el-table-column prop="user_name" label="人员" width="80" />
      <el-table-column prop="hours" label="工时(h)" width="70" />
      <el-table-column prop="description" label="说明" min-width="120" show-overflow-tooltip />
      <el-table-column label="操作" width="60" fixed="right">
        <template #default="{ row }"><el-button text size="small" type="danger" @click="del(row)">删</el-button></template>
      </el-table-column>
    </el-table>
    <el-empty v-if="entries.length===0" description="暂无工时记录" />

    <!-- 资源负载 -->
    <el-divider />
    <div class="section-title">👤 团队资源负载</div>
    <div class="workload-grid">
      <el-card v-for="w in workload" :key="w.assignee" shadow="never" class="wl-card">
        <div class="wl-name">{{ w.assignee }}</div>
        <div class="wl-stats">
          <span>任务 <b>{{ w.task_count }}</b> 个</span>
          <span>工时 <b>{{ w.total_hours }}</b>h</span>
        </div>
        <el-progress :percentage="Math.min(100, w.task_count * 20)" :stroke-width="8" :color="w.task_count > 4 ? '#f56c6c' : '#67c23a'" />
      </el-card>
      <el-empty v-if="workload.length===0" description="暂无数据" />
    </div>

    <el-dialog v-model="showAdd" title="记录工时" width="380" destroy-on-close>
      <el-form label-width="80" size="small">
        <el-form-item label="任务">
          <el-select v-model="form.task_id" filterable style="width:100%">
            <el-option v-for="t in allTasks" :key="t.id" :label="t.title" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="人员"><el-input v-model="form.user_name" /></el-form-item>
        <el-form-item label="工时(h)"><el-input-number v-model="form.hours" :min="0.5" :max="24" :step="0.5" /></el-form-item>
        <el-form-item label="日期"><el-date-picker v-model="form.entry_date" type="date" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd=false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const props = defineProps<{ pid: number }>()
const entries = ref<any[]>([])
const workload = ref<any[]>([])
const allTasks = ref<any[]>([])
const showAdd = ref(false)
const form = ref({ task_id: null, user_name: '', hours: 1, entry_date: null, description: '' })

async function fetchAll() {
  const [eRes, wRes, tRes] = await Promise.all([
    api.get(`/projects/${props.pid}/time`).catch(() => ({ data: [] })),
    api.get(`/projects/${props.pid}/time/workload`).catch(() => ({ data: [] })),
    api.get(`/projects/${props.pid}/tasks`).catch(() => ({ data: [] })),
  ])
  entries.value = eRes.data || []
  workload.value = wRes.data || []
  allTasks.value = tRes.data || []
}

async function save() {
  if (!form.value.task_id || !form.value.entry_date) { ElMessage.warning('请填写完整'); return }
  try {
    await api.post(`/projects/${props.pid}/time`, null, { params: form.value })
    ElMessage.success('已记录')
    showAdd.value = false
    form.value = { task_id: null, user_name: '', hours: 1, entry_date: null, description: '' }
    await fetchAll()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '失败') }
}
async function del(e: any) {
  try { await api.delete(`/projects/${props.pid}/time/${e.id}`); ElMessage.success('已删除'); await fetchAll() }
  catch (ex: any) { ElMessage.error(ex?.response?.data?.detail || '失败') }
}

onMounted(fetchAll)
</script>

<style scoped>
.time-tab { width: 100%; }
.toolbar { margin-bottom: 12px; }
.section-title { font-size: 15px; font-weight: 600; color: #303133; margin-bottom: 8px; }
.workload-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; }
.wl-card :deep(.el-card__body) { padding: 12px; }
.wl-name { font-weight: 600; font-size: 14px; }
.wl-stats { display: flex; gap: 12px; font-size: 12px; color: #909399; margin: 4px 0 8px; }
</style>
