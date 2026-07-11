<template>
  <div class="bom-list">
    <div class="page-header">
      <h2>BOM管理</h2>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>新建BOM
      </el-button>
    </div>
    
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="物料编码">
          <el-input v-model="searchForm.keyword" placeholder="物料编码/名称" clearable />
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
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card>
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="material_part_number" label="父件编码" width="180" />
        <el-table-column prop="material_part_name" label="父件名称" min-width="200" />
        <el-table-column prop="version" label="版本" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_default" label="默认" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="success">是</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="item_count" label="子项数" width="100" />
        <el-table-column prop="creator_name" label="创建人" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">查看</el-button>
            <el-button link type="primary" @click="handleCompare(row)">比较</el-button>
            <el-button link type="success" v-if="row.status === 'draft'" @click="handleRelease(row)">发布</el-button>
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
    
    <!-- 新建BOM对话框 -->
    <el-dialog v-model="dialogVisible" title="新建BOM" width="900px" destroy-on-close>
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="父件物料" prop="material_id">
              <el-select
                v-model="form.material_id"
                filterable
                remote
                placeholder="搜索物料编码/名称"
                :remote-method="searchMaterials"
                :loading="materialLoading"
                style="width: 100%"
              >
                <el-option
                  v-for="item in materialOptions"
                  :key="item.id"
                  :label="`${item.part_number} - ${item.part_name}`"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="版本" prop="version">
              <el-input v-model="form.version" placeholder="A.1" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="默认BOM">
          <el-switch v-model="form.is_default" />
        </el-form-item>
        
        <el-divider>BOM行项目</el-divider>
        
        <div class="bom-items">
          <div v-for="(item, index) in form.items" :key="index" class="bom-item-row">
            <el-row :gutter="10">
              <el-col :span="7">
                <el-select
                  v-model="item.material_id"
                  filterable
                  remote
                  placeholder="子件物料"
                  :remote-method="searchMaterials"
                  :loading="materialLoading"
                >
                  <el-option
                    v-for="m in materialOptions"
                    :key="m.id"
                    :label="`${m.part_number} - ${m.part_name}`"
                    :value="m.id"
                  />
                </el-select>
              </el-col>
              <el-col :span="3">
                <el-input-number v-model="item.quantity" :min="0.0001" :precision="4" style="width: 100%" />
              </el-col>
              <el-col :span="3">
                <el-input v-model="item.unit" placeholder="单位" />
              </el-col>
              <el-col :span="4">
                <el-input v-model="item.reference_designator" placeholder="位号" />
              </el-col>
              <el-col :span="4">
                <el-input v-model="item.notes" placeholder="备注" />
              </el-col>
              <el-col :span="3">
                <el-button type="danger" @click="removeItem(index)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-col>
            </el-row>
          </div>
          <el-button type="primary" plain @click="addItem">
            <el-icon><Plus /></el-icon>添加行项目
          </el-button>
        </div>
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
const submitLoading = ref(false)
const formRef = ref()
const materialLoading = ref(false)
const materialOptions = ref([])

const searchForm = reactive({
  keyword: '',
  status: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const form = reactive({
  material_id: '',
  version: 'A.1',
  description: '',
  is_default: false,
  items: []
})

const formRules = {
  material_id: [{ required: true, message: '请选择父件物料', trigger: 'change' }],
  version: [{ required: true, message: '请输入版本', trigger: 'blur' }]
}

const statusMap = {
  draft: { label: '草稿', type: 'info' },
  review: { label: '审核中', type: 'warning' },
  released: { label: '已发布', type: 'success' },
  obsolete: { label: '已停用', type: 'danger' }
}

const getStatusLabel = (status) => statusMap[status]?.label || status
const getStatusType = (status) => statusMap[status]?.type || ''
const formatDate = (date) => date ? new Date(date).toLocaleString('zh-CN') : '-'

const fetchData = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/v1/boms', {
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

const searchMaterials = async (query) => {
  if (!query) return
  materialLoading.value = true
  try {
    const res = await request.get('/api/v1/materials', {
      params: {
        tenant_id: 'default',
        keyword: query,
        page: 1,
        page_size: 20
      }
    })
    materialOptions.value = res.items || []
  } catch (error) {
    console.error('搜索物料失败', error)
  } finally {
    materialLoading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

const handleReset = () => {
  searchForm.keyword = ''
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
  form.material_id = ''
  form.version = 'A.1'
  form.description = ''
  form.is_default = false
  form.items = []
  dialogVisible.value = true
}

const addItem = () => {
  form.items.push({
    material_id: '',
    quantity: 1,
    unit: '',
    reference_designator: '',
    position: '',
    notes: '',
    is_optional: false,
    is_substitute_allowed: false
  })
}

const removeItem = (index) => {
  form.items.splice(index, 1)
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  if (form.items.length === 0) {
    ElMessage.warning('请至少添加一个行项目')
    return
  }
  
  submitLoading.value = true
  try {
    await request.post('/api/v1/boms', {
      ...form,
      tenant_id: 'default'
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
  router.push(`/boms/${row.id}`)
}

const handleCompare = (row) => {
  // BOM比较逻辑
  ElMessage.info('BOM比较功能开发中')
}

const handleRelease = async (row) => {
  try {
    await request.post(`/api/v1/boms/${row.id}/release`)
    ElMessage.success('发布成功')
    fetchData()
  } catch (error) {
    ElMessage.error(error.detail || '发布失败')
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确认删除BOM ${row.material_part_number} V${row.version}？`, '提示', {
    confirmButtonText: '确认',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await request.delete(`/api/v1/boms/${row.id}`)
      ElMessage.success('删除成功')
      fetchData()
    } catch (error) {
      ElMessage.error(error.detail || '删除失败')
    }
  })
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.bom-list {
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

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.bom-items {
  margin-top: 16px;
}

.bom-item-row {
  margin-bottom: 12px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
}
</style>
