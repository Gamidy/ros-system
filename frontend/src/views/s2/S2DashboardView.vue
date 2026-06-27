<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>认证中心仪表盘</span>
        </div>
      </template>
      <el-row :gutter="20" style="margin-bottom: 20px">
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-value">{{ stats.total }}</div>
            <div class="stat-label">认证项目总数</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-value" style="color: #409eff">{{ stats.in_progress }}</div>
            <div class="stat-label">进行中</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-value" style="color: #67c23a">{{ stats.completed }}</div>
            <div class="stat-label">已完成</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-value" style="color: #e6a23c">{{ stats.expiring_soon }}</div>
            <div class="stat-label">证书到期预警（30天内）</div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" style="margin-top: 16px">
      <template #header>
        <div class="card-header">
          <span>认证门禁状态</span>
        </div>
      </template>
      <el-table :data="gateRules" stripe border v-loading="loadingGate" max-height="350">
        <el-table-column prop="gate_code" label="门禁编号" width="100" />
        <el-table-column prop="name" label="规则名称" min-width="150" />
        <el-table-column prop="cert_type" label="认证类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.cert_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="是否强制" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_required ? 'danger' : 'info'" size="small">{{ row.is_required ? '强制' : '可选' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="自动阻塞" width="100">
          <template #default="{ row }">
            <el-tag :type="row.auto_block ? 'warning' : 'info'" size="small">{{ row.auto_block ? '开启' : '关闭' }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'

const stats = ref({ total: 0, in_progress: 0, completed: 0, expiring_soon: 0 })
const gateRules = ref<Record<string, unknown>[]>([])
const loadingGate = ref(false)

async function fetchStats() {
  try {
    const res = await api.get('/s2/certification-projects')
    const items = res.data || []
    const total = items.length
    const in_progress = items.filter((i: Record<string, unknown>) => i.status === 'in_progress').length
    const completed = items.filter((i: Record<string, unknown>) => i.status === 'completed').length
    stats.value = { total, in_progress, completed, expiring_soon: 0 }
  } catch { /* ignore */ }
}

async function fetchExpiring() {
  try {
    const res = await api.get('/s2/certificates/expiring?days=30')
    stats.value.expiring_soon = (res.data || []).length
  } catch { /* ignore */ }
}

async function fetchGateRules() {
  loadingGate.value = true
  try {
    const res = await api.get('/s2/gate-rules')
    gateRules.value = res.data || []
  } finally { loadingGate.value = false }
}

onMounted(() => {
  fetchStats()
  fetchExpiring()
  fetchGateRules()
})
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
.stat-card { text-align: center; padding: 10px; }
.stat-value { font-size: 36px; font-weight: bold; color: #303133; }
.stat-label { font-size: 14px; color: #909399; margin-top: 8px; }
</style>
