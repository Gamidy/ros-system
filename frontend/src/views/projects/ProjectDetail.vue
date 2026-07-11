<template>
  <div class="project-detail">
    <div class="page-header">
      <div class="header-left">
        <el-button @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>返回
        </el-button>
        <h2>{{ project.project_name }}</h2>
      </div>
      <div class="header-right">
        <el-tag :type="getStatusType(project.status)">{{ getStatusLabel(project.status) }}</el-tag>
        <el-button type="primary" @click="handleEdit">编辑</el-button>
      </div>
    </div>
    
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>项目信息</span>
            </div>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="项目编号">{{ project.project_code }}</el-descriptions-item>
            <el-descriptions-item label="项目类型">{{ getTypeLabel(project.project_type) }}</el-descriptions-item>
            <el-descriptions-item label="优先级">
              <el-tag :type="getPriorityType(project.priority)">{{ getPriorityLabel(project.priority) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="项目经理">{{ project.manager_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="开始日期">{{ project.start_date || '-' }}</el-descriptions-item>
            <el-descriptions-item label="目标完成日期">{{ project.target_end_date || '-' }}</el-descriptions-item>
            <el-descriptions-item label="预算">{{ project.budget ? '¥' + project.budget.toLocaleString() : '-' }}</el-descriptions-item>
            <el-descriptions-item label="进度">{{ project.progress }}%</el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">{{ project.description || '-' }}</el-descriptions-item>
          </el-descriptions>
          
          <div class="progress-section">
            <div class="progress-label">项目进度</div>
            <el-progress :percentage="project.progress" :status="getProgressStatus(project.progress)" :stroke-width="20" />
          </div>
        </el-card>
        
        <el-card class="mt-20">
          <template #header>
            <div class="card-header">
              <span>任务分解 (WBS)</span>
              <el-button type="primary" @click="handleCreateTask">
                <el-icon><Plus /></el-icon>新建任务
              </el-button>
            </div>
          </template>
          <el-table
            :data="taskList"
            row-key="id"
            default-expand-all
            :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
            stripe
          >
            <el-table-column prop="task_name" label="任务名称" min-width="200" />
            <el-table-column prop="task_type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="getTaskTypeType(row.task_type)">{{ getTaskTypeLabel(row.task_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getTaskStatusType(row.status)">{{ getTaskStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="assignee_name" label="负责人" width="120" />
            <el-table-column prop="planned_start" label="计划开始" width="120" />
            <el-table-column prop="planned_end" label="计划结束" width="120" />
            <el-table-column prop="progress" label="进度" width="150">
              <template #default="{ row }">
                <el-progress :percentage="row.progress" :show-text="true" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button v-if="row.status === 'not_started'" link type="primary" @click="handleStartTask(row)">开始</el-button>
                <el-button v-if="row.status === 'in_progress'" link type="success" @click="handleCompleteTask(row)">完成</el-button>
                <el-button link type="primary" @click="handleEditTask(row)">编辑</el-button>
                <el-button link type="danger" @click="handleDeleteTask(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>项目统计</span>
          </template>
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-value">{{ taskStats.total }}</div>
              <div class="stat-label">总任务</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ taskStats.completed }}</div>
              <div class="stat-label">已完成</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ taskStats.in_progress }}</div>
              <div class="stat-label">进行中</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ taskStats.pending }}</div>
              <div class="stat-label">未开始</div>
            </div>
          </div>
        </el-card>
        
        <el-card class="mt-20">
          <template #header>
            <span>项目时间线</span>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="event in timelineEvents"
              :key="event.id"
              :type="event.type"
              :timestamp="event.time"
            >
              {{ event.content }}
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 任务对话框 -->
    <el-dialog v-model="taskDialogVisible" :title="taskDialogTitle" width="600px">
      <el-form :model="taskForm" :rules="taskRules" ref="taskFormRef" label-width="100px">
        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="taskForm.task_name" />
        </el-form-item>
        <el-form-item label="任务类型">
          <el-select v-model="taskForm.task_type" style="width: 100%">
            <el-option label="里程碑" value="milestone" />
            <el-option label="任务" value="task" />
            <el-option label="阶段" value="phase" />
            <el-option label="交付物" value="deliverable" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="taskForm.assigned_to" style="width: 100%">
            <el-option
              v-for="user in userOptions"
              :key="user.id"
              :label="user.full_name"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="计划开始">
              <el-date-picker v-model="taskForm.planned_start" type="date" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计划结束">
              <el-date-picker v-model="taskForm.planned_end" type="date" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="预计工时">
          <el-input-number v-model="taskForm.estimated_hours" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="任务描述">
          <el-input v-model="taskForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="taskDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitTask" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'

const route = useRoute()
const project = ref({})
const taskList = ref([])
const userOptions = ref([])
const taskDialogVisible = ref(false)
const taskDialogTitle = ref('')
const submitLoading = ref(false)
const taskFormRef = ref()
const currentTaskId = ref(null)

const taskForm = reactive({
  task_name: '',
  task_type: 'task',
  assigned_to: '',
  planned_start: '',
  planned_end: '',
  estimated_hours: 0,
  description: ''
})

const taskRules = {
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }]
}

const statusMap = {
  planning: { label: '规划中', type: 'info' },
  active: { label: '进行中', type: 'primary' },
  on_hold: { label: '暂停', type: 'warning' },
  completed: { label: '已完成', type: 'success' },
  cancelled: { label: '已取消', type: 'danger' }
}

const priorityMap = {
  low: { label: '低', type: 'info' },
  normal: { label: '普通', type: '' },
  high: { label: '高', type: 'warning' },
  critical: { label: '紧急', type: 'danger' }
}

const typeMap = {
  product: '产品研发',
  process: '工艺改进',
  research: '技术研究',
  improvement: '持续改进'
}

const taskTypeMap = {
  milestone: { label: '里程碑', type: 'warning' },
  task: { label: '任务', type: '' },
  phase: { label: '阶段', type: 'primary' },
  deliverable: { label: '交付物', type: 'success' }
}

const taskStatusMap = {
  not_started: { label: '未开始', type: 'info' },
  in_progress: { label: '进行中', type: 'primary' },
  completed: { label: '已完成', type: 'success' },
  blocked: { label: '阻塞', type: 'danger' },
  cancelled: { label: '已取消', type: 'warning' }
}

const getStatusLabel = (status) => statusMap[status]?.label || status
const getStatusType = (status) => statusMap[status]?.type || ''
const getPriorityLabel = (priority) => priorityMap[priority]?.label || priority
const getPriorityType = (priority) => priorityMap[priority]?.type || ''
const getTypeLabel = (type) => typeMap[type] || type
const getTaskTypeLabel = (type) => taskTypeMap[type]?.label || type
const getTaskTypeType = (type) => taskTypeMap[type]?.type || ''
const getTaskStatusLabel = (status) => taskStatusMap[status]?.label || status
const getTaskStatusType = (status) => taskStatusMap[status]?.type || ''

const getProgressStatus = (progress) => {
  if (progress >= 100) return 'success'
  if (progress >= 60) return ''
  if (progress >= 30) return 'warning'
  return 'exception'
}

const taskStats = computed(() => {
  const stats = { total: 0, completed: 0, in_progress: 0, pending: 0 }
  
  function countTasks(tasks) {
    tasks.forEach(task => {
      stats.total++
      if (task.status === 'completed') stats.completed++
      else if (task.status === 'in_progress') stats.in_progress++
      else if (task.status === 'not_started') stats.pending++
      
      if (task.children && task.children.length > 0) {
        countTasks(task.children)
      }
    })
  }
  
  countTasks(taskList.value)
  return stats
})

const timelineEvents = ref([
  { id: 1, content: '项目创建', time: '2024-01-01', type: 'primary' },
  { id: 2, content: '需求分析完成', time: '2024-01-15', type: 'success' },
  { id: 3, content: '设计评审通过', time: '2024-02-01', type: 'success' },
  { id: 4, content: '原型开发中', time: '2024-02-15', type: 'warning' }
])

const fetchProject = async () => {
  try {
    const res = await request.get(`/api/v1/projects/${route.params.id}`)
    project.value = res
  } catch (error) {
    ElMessage.error('获取项目信息失败')
  }
}

const fetchTasks = async () => {
  try {
    const res = await request.get(`/api/v1/projects/${route.params.id}/tasks`)
    taskList.value = res || []
  } catch (error) {
    console.error('获取任务列表失败', error)
  }
}

const handleEdit = () => {
  ElMessage.info('编辑功能开发中')
}

const handleCreateTask = () => {
  currentTaskId.value = null
  taskDialogTitle.value = '新建任务'
  Object.assign(taskForm, {
    task_name: '',
    task_type: 'task',
    assigned_to: '',
    planned_start: '',
    planned_end: '',
    estimated_hours: 0,
    description: ''
  })
  taskDialogVisible.value = true
}

const handleEditTask = (row) => {
  currentTaskId.value = row.id
  taskDialogTitle.value = '编辑任务'
  Object.assign(taskForm, row)
  taskDialogVisible.value = true
}

const handleSubmitTask = async () => {
  const valid = await taskFormRef.value.validate().catch(() => false)
  if (!valid) return
  
  submitLoading.value = true
  try {
    if (currentTaskId.value) {
      await request.put(`/api/v1/projects/${route.params.id}/tasks/${currentTaskId.value}`, {
        ...taskForm,
        planned_start: taskForm.planned_start ? new Date(taskForm.planned_start).toISOString().split('T')[0] : null,
        planned_end: taskForm.planned_end ? new Date(taskForm.planned_end).toISOString().split('T')[0] : null
      })
      ElMessage.success('更新成功')
    } else {
      await request.post(`/api/v1/projects/${route.params.id}/tasks`, {
        ...taskForm,
        project_id: route.params.id,
        planned_start: taskForm.planned_start ? new Date(taskForm.planned_start).toISOString().split('T')[0] : null,
        planned_end: taskForm.planned_end ? new Date(taskForm.planned_end).toISOString().split('T')[0] : null
      })
      ElMessage.success('创建成功')
    }
    taskDialogVisible.value = false
    fetchTasks()
    fetchProject()
  } catch (error) {
    ElMessage.error(error.detail || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

const handleStartTask = async (row) => {
  try {
    await request.put(`/api/v1/projects/${route.params.id}/tasks/${row.id}`, {
      status: 'in_progress'
    })
    ElMessage.success('任务已开始')
    fetchTasks()
    fetchProject()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const handleCompleteTask = async (row) => {
  try {
    await request.put(`/api/v1/projects/${route.params.id}/tasks/${row.id}`, {
      status: 'completed',
      progress: 100
    })
    ElMessage.success('任务已完成')
    fetchTasks()
    fetchProject()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const handleDeleteTask = (row) => {
  ElMessageBox.confirm(`确认删除任务 ${row.task_name}？`, '提示', {
    confirmButtonText: '确认',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await request.delete(`/api/v1/projects/${route.params.id}/tasks/${row.id}`)
      ElMessage.success('删除成功')
      fetchTasks()
      fetchProject()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

onMounted(() => {
  fetchProject()
  fetchTasks()
})
</script>

<style scoped>
.project-detail {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.mt-20 {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-section {
  margin-top: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
}

.progress-label {
  font-weight: bold;
  margin-bottom: 12px;
  color: #303133;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.stat-item {
  text-align: center;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409EFF;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}
</style>
