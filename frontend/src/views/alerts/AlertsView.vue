<template>
  <div class="alerts-page">
    <el-row :gutter="16">
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>预警列表</span>
              <el-button type="warning" @click="checkOverdue">检查超期预警</el-button>
            </div>
          </template>

          <el-table :data="alerts" stripe border>
            <el-table-column prop="title" label="预警内容" min-width="250" />
            <el-table-column prop="level" label="级别" width="80">
              <template #default="{ row }"><el-tag :type="levelType(row.level)" size="small">{{ row.level }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="alert_type" label="类型" width="100" />
            <el-table-column prop="is_read" label="已读" width="60">
              <template #default="{ row }"><el-tag :type="row.is_read ? 'info' : 'danger'" size="small">{{ row.is_read ? '是' : '否' }}</el-tag></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never">
          <template #header><span>预警规则</span></template>
          <el-table :data="rules" stripe border>
            <el-table-column prop="name" label="规则名称" min-width="150" />
            <el-table-column prop="is_enabled" label="启用" width="60">
              <template #default="{ row }"><el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">{{ row.is_enabled ? '是' : '否' }}</el-tag></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const alerts = ref<any[]>([])
const rules = ref<any[]>([])

function levelType(l: string) {
  const map: Record<string, string> = { info: 'info', warning: 'warning', critical: 'danger' }
  return map[l] || 'info'
}

async function fetchAll() {
  try {
    const r1 = api.get('/alerts')
    const r2 = api.get('/alert-rules')
    alerts.value = (await r1).data
    rules.value = (await r2).data
  } catch {}
}

async function checkOverdue() {
  try {
    const res = await api.post('/alerts/check-overdue')
    ElMessage.success(`已创建 ${res.data.alerts_created} 条超期预警`)
    await fetchAll()
  } catch {}
}

onMounted(fetchAll)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
