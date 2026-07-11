<template>
  <div class="material-detail">
    <div class="page-header">
      <div class="header-left">
        <el-button @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>返回
        </el-button>
        <h2>{{ material.part_number }} - {{ material.part_name }}</h2>
      </div>
      <div class="header-right">
        <el-tag :type="getStatusType(material.status)">{{ getStatusLabel(material.status) }}</el-tag>
        <el-button type="primary" @click="handleEdit">编辑</el-button>
        <el-button type="success" v-if="material.status === 'draft'" @click="handleRelease">发布</el-button>
        <el-button type="warning" v-if="material.status === 'released'" @click="handleRevise">升版</el-button>
      </div>
    </div>
    
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card>
          <template #header>
            <span>基本信息</span>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="物料编码">{{ material.part_number }}</el-descriptions-item>
            <el-descriptions-item label="物料名称">{{ material.part_name }}</el-descriptions-item>
            <el-descriptions-item label="版本">{{ material.version }}</el-descriptions-item>
            <el-descriptions-item label="类型">{{ getPartTypeLabel(material.part_type) }}</el-descriptions-item>
            <el-descriptions-item label="单位">{{ material.unit }}</el-descriptions-item>
            <el-descriptions-item label="生命周期">{{ getLifecycleLabel(material.lifecycle_phase) }}</el-descriptions-item>
            <el-descriptions-item label="制造商">{{ material.manufacturer || '-' }}</el-descriptions-item>
            <el-descriptions-item label="制造商料号">{{ material.manufacturer_part_number || '-' }}</el-descriptions-item>
            <el-descriptions-item label="成本">{{ material.cost }}</el-descriptions-item>
            <el-descriptions-item label="重量">{{ material.weight ? material.weight + ' ' + material.weight_unit : '-' }}</el-descriptions-item>
            <el-descriptions-item label="创建人">{{ material.creator_name }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDate(material.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="规格描述" :span="2">{{ material.specification || '-' }}</el-descriptions-item>
            <el-descriptions-item label="详细描述" :span="2">{{ material.description || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
        
        <el-card class="mt-20">
          <template #header>
            <span>BOM列表</span>
            <el-button text type="primary" @click="handleCreateBOM">新建BOM</el-button>
          </template>
          <el-table :data="bomList" stripe>
            <el-table-column prop="version" label="版本" width="100" />
            <el-table-column prop="description" label="描述" />
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
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button link type="primary" @click="handleViewBOM(row)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>版本历史</span>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="version in versionHistory"
              :key="version.id"
              :type="version.version === material.version ? 'primary' : ''"
            >
              <div>版本 {{ version.version }}</div>
              <div class="text-secondary">{{ version.change_description || '创建' }}</div>
              <div class="text-secondary">{{ formatDate(version.created_at) }}</div>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'

const route = useRoute()
const router = useRouter()
const material = ref({})
const bomList = ref([])
const versionHistory = ref([])

const statusMap = {
  draft: { label: '草稿', type: 'info' },
  review: { label: '审核中', type: 'warning' },
  released: { label: '已发布', type: 'success' },
  obsolete: { label: '已停用', type: 'danger' }
}

const partTypeMap = {
  raw: '原材料',
  component: '元器件',
  assembly: '组件',
  finished: '成品',
  'semi-finished': '半成品',
  tool: '工装工具'
}

const lifecycleMap = {
  concept: '概念阶段',
  development: '开发阶段',
  production: '生产阶段',
  mature: '成熟阶段',
  obsolete: '淘汰阶段'
}

const getStatusLabel = (status) => statusMap[status]?.label || status
const getStatusType = (status) => statusMap[status]?.type || ''
const getPartTypeLabel = (type) => partTypeMap[type] || type
const getLifecycleLabel = (phase) => lifecycleMap[phase] || phase
const formatDate = (date) => date ? new Date(date).toLocaleString('zh-CN') : '-'

const fetchMaterial = async () => {
  try {
    const res = await request.get(`/api/v1/materials/${route.params.id}`)
    material.value = res
  } catch (error) {
    ElMessage.error('获取物料信息失败')
  }
}

const fetchBOMs = async () => {
  try {
    const res = await request.get('/api/v1/boms', {
      params: {
        tenant_id: 'default',
        material_id: route.params.id
      }
    })
    bomList.value = res.items || []
  } catch (error) {
    console.error('获取BOM列表失败', error)
  }
}

const handleEdit = () => {
  // 编辑逻辑
}

const handleRelease = async () => {
  try {
    await request.post(`/api/v1/materials/${route.params.id}/release`)
    ElMessage.success('发布成功')
    fetchMaterial()
  } catch (error) {
    ElMessage.error(error.detail || '发布失败')
  }
}

const handleRevise = async () => {
  try {
    const res = await request.post(`/api/v1/materials/${route.params.id}/revise`)
    ElMessage.success(`升版成功，新版本: ${res.new_version}`)
    router.push(`/materials/${res.material_id}`)
  } catch (error) {
    ElMessage.error(error.detail || '升版失败')
  }
}

const handleCreateBOM = () => {
  router.push('/boms')
}

const handleViewBOM = (row) => {
  router.push(`/boms/${row.id}`)
}

onMounted(() => {
  fetchMaterial()
  fetchBOMs()
})
</script>

<style scoped>
.material-detail {
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

.text-secondary {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
</style>
