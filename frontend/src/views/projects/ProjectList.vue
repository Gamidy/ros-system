<template>
  <div class="project-list">
    <div class="page-header">
      <h2>项目管理</h2>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>新建项目
      </el-button>
    </div>
    
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="关键字">
          <el-input v-model="searchForm.keyword" placeholder="项目编码/名称" clearable />
        </el-form-item>
        <el-form-item label="项目类型">
          <el-select v-model="searchForm.project_type" placeholder="全部类型" clearable>
            <el-option label="产品研发" value="product" />
            <el-option label="工艺改进" value="process" />
            <el-option label="技术研究" value="research" />
            <el-option label="持续改进" value="improvement" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="全部状态" clearable>
            <el-option label="规划中" value="planning" />
            <el-option label="进行中" value="active" />
            <el-option label="暂停" value="on_hold" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-row :gutter="20">
      <el-col :span="8" v-for="project in tableData" :key="project.id">
        <el-card class="project-card" shadow="hover" @click="handleView(project)">
          <div class="project-header">
            <div class="project-title">{{ project.project_name }}</div>
            <el-tag :type="getStatusType(project.status)">{{ getStatusLabel(project.status) }}</el-tag>
          </div>
          <div class="project-code">{{ project.project_code }}</div>
          <div class="project-info">
            <div class="info-item">
              <el-icon><User /></el-icon>
              <span>{{ project.manager_name || '未分配' }}</span>
            </div>
            <div class="info-item">
              <el-icon><Calendar /></el-icon>
              <span>{{ project.start_date || '-' }} ~ {{ project.target_end_date || '-' }}</span>
            </div>
          </div>
          <div class="project-progress">
            <div class="progress-label">
              <span>进度</span>
              <span>{{ project.progress }}%</span>
            </div>
            <el-progress :percentage="project.progress" :status="getProgressStatus(project.progress)" />
          </div>
          <div class="project-footer">
            <el-tag size="small" :type="getPriorityType(project.priority)">{{ getPriorityLabel(project.priority) }}</el-tag>
            <span class="project-type">{{ getTypeLabel(project.project_type) }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <div class="pagination">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        :page-sizes="[12, 24, 48]"
        layout="total, sizes, prev, pager, next"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>
    
    <!-- 新建项目对话框 -->
    <el-dialog v-model="dialogVisible" title="新建项目" width="700px" destroy-on-close>
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="120px">
        <el-form-item label="项目名称" prop="project_name">
          <el-input v-model="form.project_name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="项目类型" prop="project_type">
              <el-select v-model="form.project_type" placeholder="请选择类型" style="width: 100%">
                <el-option label="产品研发" value="product" />
                <el-option label="工艺改进" value="process" />
                <el-option label="技术研究" value="research" />
                <el-option label="持续改进" value="improvement" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级">
              <el-select v-model="form.priority" style="width: 100%">
                <el-option label="低" value="low" />
                <el-option label="普通" value="normal" />
                <el-option label="高" value="high" />
                <el-option label="紧急" value="critical" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="项目经理">
              <el-select v-model="form.manager_id" placeholder="请选择项目经理" style="width: 100%">
                <el-option
                  v-for="user in userOptions"
                  :key="user.id"
                  :label="user.full_name"
                  :value="user.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="预算">
              <el-input-number v-model="form.budget" :precision="2" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="开始日期">
              <el-date-picker v-model="form.start_date" type="date" placeholder="选择日期" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标完成日期">
              <el-date-picker v-model="form.target_end_date" type="date" placeholder="选择日期" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const router = useRouter()
const loading = ref(false)
const tableData = ref([])
const dialogVisible = ref(false)
const submitLoading = ref(false)
const formRef = ref()
const userOptions = ref([])

const searchForm = reactive({
  keyword: '',
  project_type: '',
  status: ''
})

const pagination = reactive({
  page: 1,
  page_size: 12,
  total: 0
})

const form = reactive({
  project_name: '',
  description: '',
  project_type: 'product',
  priority: 'normal',
  manager_id: '',
  budget: 0,
  start_date: '',
  target_end_date: ''
})

const formRules = {
  project_name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  project_type: [{ required: true, message: '请选择项目类型', trigger: 'change' }]
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

const getStatusLabel = (status) => statusMap[status]?.label || status
const getStatusType = (status) => statusMap[status]?.type || ''
const getPriorityLabel = (priority) => priorityMap[priority]?.label || priority
const getPriorityType = (priority) => priorityMap[priority]?.type || ''
const getTypeLabel = (type) => typeMap[type] || type

const getProgressStatus = (progress) => {
  if (progress >= 100) return 'success'
  if (progress >= 60) return ''
  if (progress >= 30) return 'warning'
  return 'exception'
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/v1/projects', {
      params: {
        tenant_id: 'default',
        ...searchForm,
        page: pagination.page,
        page_size: pagination.page_size
      }
    })
    tableData.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

const handleReset = () => {
  searchForm.keyword = ''
  searchForm.project_type = ''
  searchForm.status = ''
  handleSearch()
}

const handleSizeChange = (size) => {
  pagination.page_size = size
  fetchData()
}

const handlePageChange = (page) => {
  pagination.page = page
  fetchData()
}

const handleCreate = () => {
  Object.assign(form, {
    project_name: '',
    description: '',
    project_type: 'product',
    priority: 'normal',
    manager_id: '',
    budget: 0,
    start_date: '',
    target_end_date: ''
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  submitLoading.value = true
  try {
    await request.post('/api/v1/projects', {
      ...form,
      tenant_id: 'default',
      start_date: form.start_date ? new Date(form.start_date).toISOString().split('T')[0] : null,
      target_end_date: form.target_end_date ? new Date(form.target_end_date).toISOString().split('T')[0] : null
    })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    fetchData()
  } catch (error) {
    ElMessage.error(error.detail || '创建失败')
  } finally {
    submitLoading.value = false
  }
}

const handleView = (row) => {
  router.push(`/projects/${row.id}`)
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.project-list {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
}

.search-card {
  margin-bottom: 20px;
}

.project-card {
  margin-bottom: 20px;
  cursor: pointer;
  transition: all 0.3s;
}

.project-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.project-title {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.project-code {
  font-size: 12px;
  color: #909399;
  margin-bottom: 12px;
}

.project-info {
  margin-bottom: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: #606266;
  font-size: 13px;
}

.project-progress {
  margin-bottom: 16px;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
  color: #606266;
}

.project-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}

.project-type {
  font-size: 12px;
  color: #909399;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
