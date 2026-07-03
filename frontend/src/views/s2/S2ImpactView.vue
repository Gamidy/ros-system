<template>
  <div class="s2-impact">
    <div class="page-header">
      <h2>变更影响分析</h2>
    </div>

    <el-table :data="records" v-loading="loading" stripe style="width:100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="changed_part" label="变更物料" min-width="150" />
      <el-table-column label="样机" width="150">
        <template #default="{row}">
          <span v-if="row.prototype_id">PR-{{ row.prototype_id }}</span>
        </template>
      </el-table-column>
      <el-table-column label="影响等级" width="120">
        <template #default="{row}">
          <el-tag :type="levelTag(row.impact_level)" size="small">
            {{ levelLabel(row.impact_level) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="影响的认证" min-width="200">
        <template #default="{row}">
          <template v-if="row.affected_cert_types">
            <el-tag v-for="ct in parseCertTypes(row.affected_cert_types)" :key="ct"
              style="margin-right:4px;margin-bottom:2px" size="small">
              {{ ct }}
            </el-tag>
          </template>
        </template>
      </el-table-column>
      <el-table-column prop="analysis_detail" label="分析详情" min-width="200" show-overflow-tooltip />
      <el-table-column prop="created_at" label="分析时间" width="170">
        <template #default="{row}">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'

const loading = ref(false)
const records = ref<Record<string, unknown>[]>([])

const levelTag = (l: string) => {
  const map: Record<string, string> = { critical: 'danger', major: 'warning', minor: 'info', none: 'success' }
  return map[l] || 'info'
}
const levelLabel = (l: string) => {
  const map: Record<string, string> = { critical: '严重', major: '较大', minor: '轻微', none: '无影响' }
  return map[l] || l
}
const parseCertTypes = (val: string) => { try { return JSON.parse(val) } catch { return [val] } }
const formatDate = (d: string) => d ? d.substring(0, 19).replace('T', ' ') : '-'

const fetchData = async () => {
  loading.value = true
  try {
    const { data } = await api.get('/s2/change-impact/records')
    records.value = data || []
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; }
</style>
