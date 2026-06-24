<template>
  <div class="s2-requirements">
    <div class="page-header">
      <h2>认证需求清单</h2>
      <div class="header-actions">
        <el-button type="primary" @click="triggerGenerate" :loading="genLoading">
          触发自动生成
        </el-button>
      </div>
    </div>

    <el-card class="info-card" style="margin-bottom:16px">
      <el-alert title="认证需求从 TargetMarket 自动生成，不可手动创建" type="info" :closable="false" show-icon />
    </el-card>

    <el-table :data="requirements" v-loading="loading" stripe style="width:100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="cert_type" label="认证类型" width="100">
        <template #default="{row}">
          <el-tag :type="certTypeTag(row.cert_type)" size="small">{{ row.cert_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="target_market_name" label="目标市场" min-width="120" />
      <el-table-column prop="cert_body" label="认证机构" min-width="150" />
      <el-table-column prop="is_mandatory" label="强制" width="70">
        <template #default="{row}">
          <el-tag :type="row.is_mandatory ? 'danger' : 'info'" size="small">
            {{ row.is_mandatory ? '是' : '否' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="120">
        <template #default="{row}">
          <el-tag :type="statusTag(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="source_type" label="来源" width="120" />
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{row}">
          <el-button type="primary" link size="small" @click="viewDetail(row)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="detailVisible" title="认证需求详情" width="500px">
      <el-descriptions v-if="currentDetail" :column="2" border>
        <el-descriptions-item label="ID">{{ currentDetail.id }}</el-descriptions-item>
        <el-descriptions-item label="认证类型">{{ currentDetail.cert_type }}</el-descriptions-item>
        <el-descriptions-item label="目标市场">{{ currentDetail.target_market_name }}</el-descriptions-item>
        <el-descriptions-item label="认证机构">{{ currentDetail.cert_body || '-' }}</el-descriptions-item>
        <el-descriptions-item label="强制">{{ currentDetail.is_mandatory ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTag(currentDetail.status)" size="small">
            {{ statusLabel(currentDetail.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="来源" :span="2">{{ currentDetail.source_type }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const genLoading = ref(false)
const requirements = ref<any[]>([])
const detailVisible = ref(false)
const currentDetail = ref<any>(null)

const certTypeTag = (type: string) => {
  const map: Record<string, string> = { CE: 'success', CB: 'primary', UL: 'warning', SAA: 'info', RoHS: 'danger', REACH: '' }
  return map[type] || 'info'
}
const statusTag = (s: string) => {
  const map: Record<string, string> = { pending: 'info', in_progress: 'warning', completed: 'success', failed: 'danger' }
  return map[s] || 'info'
}
const statusLabel = (s: string) => {
  const map: Record<string, string> = { pending: '待处理', in_progress: '进行中', completed: '已完成', failed: '失败' }
  return map[s] || s
}

const fetchData = async () => {
  loading.value = true
  try {
    const { data } = await api.get('/api/s2/certification-requirements')
    requirements.value = data || []
  } finally {
    loading.value = false
  }
}

const triggerGenerate = async () => {
  genLoading.value = true
  try {
    await api.post('/api/s2/certification-requirements/generate')
    ElMessage.success('认证需求生成完成')
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '生成失败')
  } finally {
    genLoading.value = false
  }
}

const viewDetail = async (row: any) => {
  try {
    const { data } = await api.get(`/api/s2/certification-requirements/${row.id}`)
    currentDetail.value = data
    detailVisible.value = true
  } catch {
    ElMessage.error('获取详情失败')
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; }
</style>
