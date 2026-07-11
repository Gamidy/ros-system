<template>
  <div class="material-list">
    <div class="page-header">
      <h2>物料管理</h2>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>新建物料
      </el-button>
    </div>
    
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="关键字">
          <el-input v-model="searchForm.keyword" placeholder="物料编码/名称" clearable />
        </el-form-item>
        <el-form-item label="物料类型">
          <el-select v-model="searchForm.part_type" placeholder="全部类型" clearable>
            <el-option label="原材料" value="raw" />
            <el-option label="元器件" value="component" />
            <el-option label="组件" value="assembly" />
            <el-option label="成品" value="finished" />
            <el-option label="半成品" value="semi-finished" />
            <el-option label="工装工具" value="tool" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="全部状态" clearable>
            <el-option label="草稿" value="draft" />
            <el-option label="审核中" value="review" />
            <el-option label="已发布" value="released" />
            <el-option label="已停用" value="obsolete" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>查询
          </el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card>
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="part_number" label="物料编码" width="180">
          <template #default="{ row }">
            <el-link type="primary" @click="handleView(row)">{{ row.part_number }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="part_name" label="物料名称" min-width="200" />
        <el-table-column prop="part_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getPartTypeType(row.part_type)">{{ getPartTypeLabel(row.part_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="80" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lifecycle_phase" label="生命周期" width="100">
          <template #default="{ row }">
            {{ getLifecycleLabel(row.lifecycle_phase) }}
          </template>
        </el-table-column>
        <el-table-column prop="creator_name" label="创建人" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">查看</el-button>
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
    
    <!-- 新建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="700px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="120px"
      >
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="物料编码" prop="part_number">
              <el-input v-model="form.part_number" placeholder="请输入物料编码" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="物料名称" prop="part_name">
              <el-input v-model="form.part_name" placeholder="请输入物料名称" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="物料类型" prop="part_type">
              <el-select v-model="form.part_type" placeholder="请选择类型" style="width: 100%">
                <el-option label="原材料" value="raw" />
                <el-option label="元器件" value="component" />
                <el-option label="组件" value="assembly" />
                <el-option label="成品" value="finished" />
                <el-option label="半成品" value="semi-finished" />
                <el-option label="工装工具" value="tool" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="单位" prop="unit">
              <el-input v-model="form.unit" placeholder="PCS" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="规格描述" prop="specification">
          <el-input v-model="form.specification" type="textarea" :rows="3" />
        </el-form-item>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="制造商" prop="manufacturer">
              <el-input v-model="form.manufacturer" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="制造商料号" prop="manufacturer_part_number">
              <el-input v-model="form.manufacturer_part_number" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="成本" prop="cost">
              <el-input-number v-model="form.cost" :precision="4" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="重量" prop="weight">
              <el-input-number v-model="form.weight" :precision="4" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="详细描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="4" />
        </el-form-item>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'

const router = useRouter()
const loading = ref(false)
const tableData = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('')
const submitLoading = ref(false)
const formRef = ref()
const isEdit = ref(false)
const currentId = ref(null)

const searchForm = reactive({
  keyword: '',
  part_type: '',
  status: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const form = reactive({
  part_number: '',
  part_name: '',
  part_type: '',
  unit: 'PCS',
  specification: '',
  manufacturer: '',
  manufacturer_part_number: '',
  cost: 0,
  weight: null,
  description: ''
})

const formRules = {
  part_number: [{ required: true, message: '请输入物料编码', trigger: 'blur' }],
  part_name: [{ required: true, message: '请输入物料名称', trigger: 'blur' }],
  part_type: [{ required: true, message: '请选择物料类型', trigger: 'change' }]
}

const partTypeMap = {
  raw: { label: '原材料', type: 'info' },
  component: { label: '元器件', type: 'warning' },
  assembly: { label: '组件', type: 'success' },
  finished: { label: '成品', type: 'primary' },
  'semi-finished': { label: '半成品', type: '' },
  tool: { label: '工装工具', type: 'danger' }
}

const statusMap = {
  draft: { label: '草稿', type: 'info' },
  review: { label: '审核中', type: 'warning' },
  released: { label: '已发布', type: 'success' },
  obsolete: { label: '已停用', type: 'danger' },
  pending: { label: '待处理', type: 'primary' }
}

const lifecycleMap = {
  concept: '概念阶段',
  development: '开发阶段',
  production: '生产阶段',
  mature: '成熟阶段',
  obsolete: '淘汰阶段'
}

const getPartTypeLabel = (type) => partTypeMap[type]?.label || type
const getPartTypeType = (type) => partTypeMap[type]?.type || ''
const getStatusLabel = (status) => statusMap[status]?.label || status
const getStatusType = (status) => statusMap[status]?.type || ''
const getLifecycleLabel = (phase) => lifecycleMap[phase] || phase

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/v1/materials', {
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
  searchForm.part_type = ''
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
  isEdit.value = false
  dialogTitle.value = '新建物料'
  Object.assign(form, {
    part_number: '',
    part_name: '',
    part_type: '',
    unit: 'PCS',
    specification: '',
    manufacturer: '',
    manufacturer_part_number: '',
    cost: 0,
    weight: null,
    description: ''
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  currentId.value = row.id
  dialogTitle.value = '编辑物料'
  Object.assign(form, row)
  dialogVisible.value = true
}

const handleView = (row) => {
  router.push(`/materials/${row.id}`)
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确认删除物料 ${row.part_number}？`, '提示', {
    confirmButtonText: '确认',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await request.delete(`/api/v1/materials/${row.id}`)
      ElMessage.success('删除成功')
      fetchData()
    } catch (error) {
      ElMessage.error(error.detail || '删除失败')
    }
  })
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  submitLoading.value = true
  try {
    if (isEdit.value) {
      await request.put(`/api/v1/materials/${currentId.value}`, form)
      ElMessage.success('更新成功')
    } else {
      await request.post('/api/v1/materials', {
        ...form,
        tenant_id: 'default'
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (error) {
    ElMessage.error(error.detail || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.material-list {
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
  color: #303133;
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
