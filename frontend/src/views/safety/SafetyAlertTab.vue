<template>
  <div>
    <div class="toolbar" style="margin-bottom:12px;display:flex;gap:8px;align-items:center;">
      <span style="font-size:14px;color:#666;">预警提前天数:</span>
      <el-select v-model="days" style="width:100px" @change="fetchAlerts">
        <el-option label="30天" :value="30" />
        <el-option label="60天" :value="60" />
        <el-option label="90天" :value="90" />
      </el-select>
      <el-select v-model="severity" placeholder="严重等级" clearable style="width:130px" @change="fetchAlerts">
        <el-option label="紧急 Critical" value="critical" />
        <el-option label="警告 Warning" value="warning" />
        <el-option label="提示 Info" value="info" />
      </el-select>
      <el-button type="primary" @click="fetchAlerts">刷新</el-button>
    </div>

    <el-table :data="alerts" v-loading="loading" style="width:100%">
      <el-table-column label="严重等级" width="100">
        <template #default="{row}">
          <el-tag :type="row.severity === 'critical' ? 'danger' : row.severity === 'warning' ? 'warning' : 'info'" size="small">
            {{ row.severity === 'critical' ? '紧急' : row.severity === 'warning' ? '警告' : '提示' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="alert_type" label="类型" width="120">
        <template #default="{row}">
          {{ row.alert_type === 'qual_expiry' ? '资质到期' : row.alert_type === 'standard_change' ? '标准变更' : row.alert_type === 'cert_expiry' ? '证书到期' : row.alert_type }}
        </template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="260" show-overflow-tooltip />
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column label="到期日" width="100">
        <template #default="{row}">
          <span v-if="row.expiry_date" :style="{ color: (row.days_remaining ?? 99) <= 7 ? '#f56c6c' : '#e6a23c' }">{{ row.expiry_date }}</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="剩余天数" width="80" align="center">
        <template #default="{row}">
          <el-tag v-if="row.days_remaining != null" :type="row.days_remaining <= 0 ? 'danger' : row.days_remaining <= 7 ? 'warning' : 'info'" size="small">
            {{ row.days_remaining <= 0 ? '已过期' : row.days_remaining + '天' }}
          </el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
    </el-table>

    <div style="margin-top:16px;text-align:center;" v-if="alerts.length === 0 && !loading">
      <el-empty description="暂无安规预警" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getSafetyAlerts } from '../../api/safety'

const alerts = ref<any[]>([])
const loading = ref(false)
const days = ref(30)
const severity = ref('')

async function fetchAlerts() {
  loading.value = true
  try {
    const { data } = await getSafetyAlerts({
      days: days.value,
      severity: severity.value || undefined,
    })
    alerts.value = data.items || []
  } catch { /* */ } finally { loading.value = false }
}

onMounted(fetchAlerts)
</script>
