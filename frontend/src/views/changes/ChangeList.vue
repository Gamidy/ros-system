<template>
  <div class="change-list">
    <div class="page-header">
      <h2>变更管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="handleCreateECR">
          <el-icon><Plus /></el-icon>新建ECR
        </el-button>
        <el-button type="success" @click="handleCreateECO">
          <el-icon><Plus /></el-icon>新建ECO
        </el-button>
      </div>
    </div>
    
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="变更请求 (ECR)" name="requests">
        <el-card class="search-card">
          <el-form :inline="true" :model="ecrSearchForm">
            <el-form-item label="编号">
              <el-input v-model="ecrSearchForm.request_number" placeholder="ECR编号" clearable />
            </el-form-item>
            <el-form-item label="类型">
              <el-select v-model="ecrSearchForm.change_type" placeholder="全部类型" clearable>
                <el-option label="设计变更" value="design" />
                <el-option label="工艺变更" value="process" />
                <el-option label="物料变更" value="material" />
                <el-option label="规格变更" value="specification" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="ecrSearchForm.status" placeholder="全部状态" clearable>
                <el-option label="草稿" value="draft" />
                <el-option label="已提交" value="submitted" />
                <el-option label="审核中" value="reviewing" />
                <el-option label="已批准" value="approved" />
                <el-option label="已拒绝" value="rejected" />
                <el-option label="已取消" value="cancelled" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSearchECR">查询</el-button>
              <el-button @click="handleResetECR">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
        
        <el-card>
          <el-table :data="ecrList" v-loading="ecrLoading" stripe>
            <el-table-column prop="request_number" label="ECR编号" width="160">
              <template #default="{ row }">
                <el-link type="primary" @click="handleViewECR(row)">{{ row.request_number }}</el-link>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="标题" min-width="250" />
            <el-table-column prop="change_type" label="变更类型" width="120">
              <template #default="{ row }">
                <el-tag>{{ getChangeTypeLabel(row.change_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="priority" label="优先级" width="100">
              <template #default="{ row }">
                <el-tag :type="getPriorityType(row.priority)">{{ getPriorityLabel(row.priority) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">{{ getStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="requester_name" label="申请人" width="120" />
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.status === 'draft'" link type="primary" @click="handleSubmitECR(row)">提交</el-button>
                <el-button v-if="row.status === 'submitted' || row.status === 'reviewing'" link type="success" @click="handleApproveECR(row)">批准</el-button>
                <el-button v-if="row.status === 'submitted' || row.status === 'reviewing'" link type="danger" @click="handleRejectECR(row)">拒绝</el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <div class="pagination">
            <el-pagination
              v-model:current-page="ecrPagination.page"
              v-model:page-size="ecrPagination.page_size"
              :total="ecrPagination.total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              @size-change="handleECRSizeChange"
              @current-change="handleECRPageChange"
            />
          </div>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="变更单 (ECO)" name="orders">
        <el-card class="search-card">
          <el-form :inline="true" :model="ecoSearchForm">
            <el-form-item label="编号">
              <el-input v-model="ecoSearchForm.order_number" placeholder="ECO编号" clearable />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="ecoSearchForm.status" placeholder="全部状态" clearable>
                <el-option label="草稿" value="draft" />
                <el-option label="已提交" value="submitted" />
                <el-option label="审核中" value="reviewing" />
                <el-option label="已批准" value="approved" />
                <el-option label="已实施" value="implemented" />
                <el-option label="已拒绝" value="rejected" />
                <el-option label="已取消" value="cancelled" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSearchECO">查询</el-button>
              <el-button @click="handleResetECO">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
        
        <el-card>
          <el-table :data="ecoList" v-loading="ecoLoading" stripe>
            <el-table-column prop="order_number" label="ECO编号" width="160">
              <template #default="{ row }">
                <el-link type="primary" @click="handleViewECO(row)">{{ row.order_number }}</el-link>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="标题" min-width="250" />
            <el-table-column prop="change_type" label="变更类型" width="120">
              <template #default="{ row }">
                <el-tag>{{ getChangeTypeLabel(row.change_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">{{ getECOStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="planner_name" label="计划人" width="120" />
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.status === 'draft'" link type="primary" @click="handleSubmitECO(row)">提交</el-button>
                <el-button v-if="row.status === 'submitted' || row.status === 'reviewing'" link type="success" @click="handleApproveECO(row)">批准</el-button>
                <el-button v-if="row.status === 'approved'" link type="warning" @click="handleImplementECO(row)">实施</el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <div class="pagination">
            <el-pagination
              v-model:current-page="ecoPagination.page"
              v-model:page-size="ecoPagination.page_size"
              :total="ecoPagination.total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              @size-change="handleECOSizeChange"
              @current-change="handleECOPageChange"
            />
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>
    
    <!-- ECR对话框 -->
    <el-dialog v-model="ecrDialogVisible" title="新建变更请求 (ECR)" width="700px">
      <el-form :model="ecrForm" :rules="ecrRules" ref="ecrFormRef" label-width="120px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="ecrForm.title" placeholder="请输入变更请求标题" />
        </el-form-item>
        <el-form-item label="变更类型" prop="change_type">
          <el-select v-model="ecrForm.change_type" placeholder="请选择类型" style="width: 100%">
            <el-option label="设计变更" value="design" />
            <el-option label="工艺变更" value="process" />
            <el-option label="物料变更" value="material" />
            <el-option label="规格变更" value="specification" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="ecrForm.priority" style="width: 100%">
            <el-option label="低" value="low" />
            <el-option label="普通" value="normal" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标日期">
          <el-date-picker v-model="ecrForm.target_date" type="date" placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="变更描述">
          <el-input v-model="ecrForm.description" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="影响分析">
          <el-input v-model="ecrForm.impact_analysis" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="ecrDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitECRForm" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'

const activeTab = ref('requests')
const ecrLoading = ref(false)
const ecoLoading = ref(false)
const ecrDialogVisible = ref(false)
const submitLoading = ref(false)
const ecrFormRef = ref()

const ecrSearchForm = reactive({
  request_number: '',
  change_type: '',
  status: ''
})

const ecoSearchForm = reactive({
  order_number: '',
  status: ''
})

const ecrPagination = reactive({ page: 1, page_size: 20, total: 0 })
const ecoPagination = reactive({ page: 1, page_size: 20, total: 0 })

const ecrList = ref([])
const ecoList = ref([])

const ecrForm = reactive({
  title: '',
  change_type: '',
  priority: 'normal',
  target_date: '',
  description: '',
  impact_analysis: ''
})

const ecrRules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  change_type: [{ required: true, message: '请选择变更类型', trigger: 'change' }]
}

const changeTypeMap = {
  design: '设计变更',
  process: '工艺变更',
  material: '物料变更',
  specification: '规格变更',
  other: '其他'
}

const priorityMap = {
  low: { label: '低', type: 'info' },
  normal: { label: '普通', type: '' },
  high: { label: '高', type: 'warning' },
  urgent: { label: '紧急', type: 'danger' }
}

const statusMap = {
  draft: { label: '草稿', type: 'info' },
  submitted: { label: '已提交', type: 'primary' },
  reviewing: { label: '审核中', type: 'warning' },
  approved: { label: '已批准', type: 'success' },
  rejected: { label: '已拒绝', type: 'danger' },
  cancelled: { label: '已取消', type: 'info' }
}

const ecoStatusMap = {
  draft: { label: '草稿', type: 'info' },
  submitted: { label: '已提交', type: 'primary' },
  reviewing: { label: '审核中', type: 'warning' },
  approved: { label: '已批准', type: 'success' },
  implemented: { label: '已实施', type: 'success' },
  rejected: { label: '已拒绝', type: 'danger' },
  cancelled: { label: '已取消', type: 'info' }
}

const getChangeTypeLabel = (type) => changeTypeMap[type] || type
const getPriorityLabel = (priority) => priorityMap[priority]?.label || priority
const getPriorityType = (priority) => priorityMap[priority]?.type || ''
const getStatusLabel = (status) => statusMap[status]?.label || status
const getStatusType = (status) => statusMap[status]?.type || ''
const getECOStatusLabel = (status) => ecoStatusMap[status]?.label || status
const formatDate = (date) => date ? new Date(date).toLocaleString('zh-CN') : '-'

const fetchECRList = async () => {
  ecrLoading.value = true
  try {
    const res = await request.get('/api/v1/changes/requests', {
      params: {
        tenant_id: 'default',
        ...ecrSearchForm,
        page: ecrPagination.page,
        page_size: ecrPagination.page_size
      }
    })
    ecrList.value = res.items || []
    ecrPagination.total = res.total || 0
  } catch (error) {
    ElMessage.error('获取ECR列表失败')
  } finally {
    ecrLoading.value = false
  }
}

const fetchECOList = async () => {
  ecoLoading.value = true
  try {
    const res = await request.get('/api/v1/changes/orders', {
      params: {
        tenant_id: 'default',
        ...ecoSearchForm,
        page: ecoPagination.page,
        page_size: ecoPagination.page_size
      }
    })
    ecoList.value = res.items || []
    ecoPagination.total = res.total || 0
  } catch (error) {
    ElMessage.error('获取ECO列表失败')
  } finally {
    ecoLoading.value = false
  }
}

const handleTabChange = () => {
  if (activeTab.value === 'requests') {
    fetchECRList()
  } else {
    fetchECOList()
  }
}

const handleSearchECR = () => {
  ecrPagination.page = 1
  fetchECRList()
}

const handleResetECR = () => {
  ecrSearchForm.request_number = ''
  ecrSearchForm.change_type = ''
  ecrSearchForm.status = ''
  handleSearchECR()
}

const handleSearchECO = () => {
  ecoPagination.page = 1
  fetchECOList()
}

const handleResetECO = () => {
  ecoSearchForm.order_number = ''
  ecoSearchForm.status = ''
  handleSearchECO()
}

const handleCreateECR = () => {
  Object.assign(ecrForm, {
    title: '',
    change_type: '',
    priority: 'normal',
    target_date: '',
    description: '',
    impact_analysis: ''
  })
  ecrDialogVisible.value = true
}

const handleCreateECO = () => {
  ElMessage.info('ECO创建功能开发中')
}

const handleSubmitECRForm = async () => {
  const valid = await ecrFormRef.value.validate().catch(() => false)
  if (!valid) return
  
  submitLoading.value = true
  try {
    await request.post('/api/v1/changes/requests', {
      ...ecrForm,
      tenant_id: 'default',
      target_date: ecrForm.target_date ? new Date(ecrForm.target_date).toISOString().split('T')[0] : null
    })
    ElMessage.success('创建成功')
    ecrDialogVisible.value = false
    fetchECRList()
  } catch (error) {
    ElMessage.error(error.detail || '创建失败')
  } finally {
    submitLoading.value = false
  }
}

const handleSubmitECR = async (row) => {
  try {
    await request.post(`/api/v1/changes/requests/${row.id}/submit`)
    ElMessage.success('提交成功')
    fetchECRList()
  } catch (error) {
    ElMessage.error(error.detail || '提交失败')
  }
}

const handleApproveECR = async (row) => {
  try {
    await ElMessageBox.confirm('确认批准此变更请求？', '审批确认', {
      confirmButtonText: '批准',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.post(`/api/v1/changes/requests/${row.id}/approve`)
    ElMessage.success('审批成功')
    fetchECRList()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.detail || '审批失败')
    }
  }
}

const handleRejectECR = async (row) => {
  try {
    await ElMessageBox.prompt('请输入拒绝原因', '拒绝确认', {
      confirmButtonText: '拒绝',
      cancelButtonText: '取消',
      type: 'warning',
      inputType: 'textarea'
    })
    await request.post(`/api/v1/changes/requests/${row.id}/reject`)
    ElMessage.success('已拒绝')
    fetchECRList()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.detail || '操作失败')
    }
  }
}

const handleSubmitECO = async (row) => {
  try {
    await request.post(`/api/v1/changes/orders/${row.id}/submit`)
    ElMessage.success('提交成功')
    fetchECOList()
  } catch (error) {
    ElMessage.error(error.detail || '提交失败')
  }
}

const handleApproveECO = async (row) => {
  try {
    await request.post(`/api/v1/changes/orders/${row.id}/approve`)
    ElMessage.success('审批成功')
    fetchECOList()
  } catch (error) {
    ElMessage.error(error.detail || '审批失败')
  }
}

const handleImplementECO = async (row) => {
  try {
    await ElMessageBox.confirm('确认实施此变更单？', '实施确认', {
      confirmButtonText: '确认实施',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.post(`/api/v1/changes/orders/${row.id}/implement`)
    ElMessage.success('实施成功')
    fetchECOList()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.detail || '实施失败')
    }
  }
}

const handleViewECR = (row) => {
  ElMessage.info('查看详情功能开发中')
}

const handleViewECO = (row) => {
  ElMessage.info('查看详情功能开发中')
}

onMounted(() => {
  fetchECRList()
})
</script>

<style scoped>
.change-list {
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

.header-actions {
  display: flex;
  gap: 12px;
}

.search-card {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
