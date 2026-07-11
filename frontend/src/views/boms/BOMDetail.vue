<template>
  <div class="bom-detail">
    <div class="page-header">
      <div class="header-left">
        <el-button @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>返回
        </el-button>
        <h2>BOM详情 - {{ bom.material_part_name }} (V{{ bom.version }})</h2>
      </div>
      <div class="header-right">
        <el-tag :type="getStatusType(bom.status)">{{ getStatusLabel(bom.status) }}</el-tag>
        <el-button type="primary" @click="handleExplode">多级展开</el-button>
        <el-button @click="handleCompare">版本比较</el-button>
      </div>
    </div>
    
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <span>BOM结构</span>
          </template>
          <el-table
            :data="flattenItems"
            row-key="id"
            default-expand-all
            :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
            stripe
          >
            <el-table-column prop="part_number" label="物料编码" width="180">
              <template #default="{ row }">
                <el-link type="primary" @click="handleViewMaterial(row)">{{ row.part_number }}</el-link>
              </template>
            </el-table-column>
            <el-table-column prop="part_name" label="物料名称" min-width="200" />
            <el-table-column prop="quantity" label="数量" width="120">
              <template #default="{ row }">
                {{ row.quantity }} {{ row.unit }}
              </template>
            </el-table-column>
            <el-table-column prop="reference_designator" label="位号" width="150" />
            <el-table-column prop="position" label="位置" width="120" />
            <el-table-column prop="notes" label="备注" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 多级展开对话框 -->
    <el-dialog v-model="explodeVisible" title="BOM多级展开" width="900px">
      <el-table :data="explodedItems" stripe>
        <el-table-column prop="level" label="层级" width="80">
          <template #default="{ row }">
            <el-tag>{{ row.level + 1 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="part_number" label="物料编码" width="180" />
        <el-table-column prop="part_name" label="物料名称" min-width="200" />
        <el-table-column prop="quantity" label="数量" width="120" />
        <el-table-column prop="reference_designator" label="位号" width="150" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const route = useRoute()
const router = useRouter()
const bom = ref({})
const explodeVisible = ref(false)
const explodedItems = ref([])

const statusMap = {
  draft: { label: '草稿', type: 'info' },
  review: { label: '审核中', type: 'warning' },
  released: { label: '已发布', type: 'success' },
  obsolete: { label: '已停用', type: 'danger' }
}

const getStatusLabel = (status) => statusMap[status]?.label || status
const getStatusType = (status) => statusMap[status]?.type || ''

const flattenItems = computed(() => {
  const result = []
  
  function flatten(items, parentIndex = '') {
    items.forEach((item, index) => {
      const currentIndex = parentIndex ? `${parentIndex}.${index + 1}` : `${index + 1}`
      const flatItem = {
        ...item,
        index: currentIndex,
        hasChildren: item.children && item.children.length > 0
      }
      result.push(flatItem)
      if (item.children && item.children.length > 0) {
        flatten(item.children, currentIndex)
      }
    })
  }
  
  if (bom.value.items) {
    flatten(bom.value.items)
  }
  
  return result
})

const fetchBOM = async () => {
  try {
    const res = await request.get(`/api/v1/boms/${route.params.id}`)
    bom.value = res
  } catch (error) {
    ElMessage.error('获取BOM详情失败')
  }
}

const handleExplode = async () => {
  try {
    const res = await request.get(`/api/v1/boms/${route.params.id}/explode`)
    
    // 扁平化展开结果
    function flattenExplode(items, level = 0) {
      const result = []
      items.forEach(item => {
        result.push({ ...item, level })
        if (item.children && item.children.length > 0) {
          result.push(...flattenExplode(item.children, level + 1))
        }
      })
      return result
    }
    
    explodedItems.value = flattenExplode(res.items || [])
    explodeVisible.value = true
  } catch (error) {
    ElMessage.error('展开失败')
  }
}

const handleCompare = () => {
  // BOM比较
  ElMessage.info('BOM比较功能开发中')
}

const handleViewMaterial = (row) => {
  router.push(`/materials/${row.material_id}`)
}

onMounted(() => {
  fetchBOM()
})
</script>

<style scoped>
.bom-detail {
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
</style>
