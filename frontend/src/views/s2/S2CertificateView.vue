<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>证书管理</span>
        </div>
      </template>

      <el-row :gutter="12" style="margin-bottom: 16px">
        <el-col :span="6">
          <el-select v-model="filterType" placeholder="认证类型" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="CE" value="CE" />
            <el-option label="CB" value="CB" />
            <el-option label="UL" value="UL" />
            <el-option label="SAA" value="SAA" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filterStatus" placeholder="状态筛选" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="有效" value="active" />
            <el-option label="过期" value="expired" />
            <el-option label="暂停" value="suspended" />
            <el-option label="注销" value="revoked" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-input v-model="searchNo" placeholder="搜索证书编号" clearable @change="fetchData" />
        </el-col>
      </el-row>

      <el-table :data="items" stripe border v-loading="loading" max-height="550">
        <el-table-column prop="cert_no" label="证书编号" width="200" />
        <el-table-column label="认证类型" width="100">
          <template #default="{ row }">
            <el-tag :type="certTagType(row.cert_type)" size="small">{{ row.cert_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="issuing_body" label="发证机构" width="150" />
        <el-table-column label="签发日期" width="120">
          <template #default="{ row }">{{ row.issue_date?.slice(0, 10) }}</template>
        </el-table-column>
        <el-table-column label="到期日期" width="120">
          <template #default="{ row }">
            <span :style="isExpiringSoon(row.expiry_date) ? 'color: #e6a23c; font-weight: bold' : ''">
              {{ row.expiry_date?.slice(0, 10) }}
            </span>
            <el-tag v-if="isExpiringSoon(row.expiry_date)" size="small" type="warning" style="margin-left: 4px">即将到期</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="$router.push(`/s2/certificates/${row.id}`)">详情</el-button>
            <el-button link type="success" size="small" @click="renew(row)">续证</el-button>
            <el-button link type="warning" size="small" @click="suspend(row)" v-if="row.status==='active'">暂停</el-button>
            <el-button link type="danger" size="small" @click="revoke(row)" v-if="row.status!=='revoked'">撤销</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

const items = ref<any[]>([])
const loading = ref(false)
const filterType = ref('')
const filterStatus = ref('')
const searchNo = ref('')

const statusMap: Record<string, string> = { active: '有效', expired: '过期', suspended: '暂停', revoked: '注销' }
const statusTypeMap: Record<string, string> = { active: 'success', expired: 'info', suspended: 'warning', revoked: 'danger' }
function statusLabel(s: string) { return statusMap[s] || s }
function statusType(s: string) { return (statusTypeMap[s] || 'info') as any }

function certTagType(t: string) { const map: Record<string, string> = { CE: 'danger', CB: 'warning', UL: 'primary', SAA: 'success' }; return map[t] || 'info' }

function isExpiringSoon(d: string | null) {
  if (!d) return false
  const expiry = new Date(d)
  const now = new Date()
  const diff = (expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
  return diff >= 0 && diff <= 30
}

async function fetchData() {
  loading.value = true
  try {
    const params: string[] = []
    if (filterType.value) params.push(`cert_type=${filterType.value}`)
    if (filterStatus.value) params.push(`status=${filterStatus.value}`)
    if (searchNo.value) params.push(`cert_no=${encodeURIComponent(searchNo.value)}`)
    const url = '/s2/certificates' + (params.length ? '?' + params.join('&') : '')
    const res = await api.get(url)
    items.value = res.data || []
  } finally { loading.value = false }
}

async function renew(row: any) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新的到期日期 (YYYY-MM-DD)', '续证', {
      inputPattern: /^\d{4}-\d{2}-\d{2}$/,
      inputErrorMessage: '日期格式不正确',
    })
    await api.post(`/s2/certificates/${row.id}/renew`, { expiry_date: value, change_reason: '续证' })
    ElMessage.success('续证成功')
    await fetchData()
  } catch { /* cancelled */ }
}

async function suspend(row: any) {
  try {
    await ElMessageBox.confirm(`确定暂停证书 ${row.cert_no}？`, '确认', { type: 'warning' })
    await api.post(`/s2/certificates/${row.id}/suspend`)
    ElMessage.success('已暂停')
    await fetchData()
  } catch { /* cancelled */ }
}

async function revoke(row: any) {
  try {
    await ElMessageBox.confirm(`确定撤销证书 ${row.cert_no}？此操作不可逆！`, '确认', { type: 'warning', confirmButtonText: '确认撤销', confirmButtonClass: 'el-button--danger' })
    await api.post(`/s2/certificates/${row.id}/revoke`)
    ElMessage.success('已撤销')
    await fetchData()
  } catch { /* cancelled */ }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
