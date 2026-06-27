<template>
  <div class="page">
    <el-card shadow="never" style="margin-bottom: 16px">
      <template #header>
        <div class="card-header">
          <span>证书详情</span>
          <el-button @click="$router.push('/s2/certificates')">返回列表</el-button>
        </div>
      </template>

      <el-descriptions :column="3" border v-loading="loading">
        <el-descriptions-item label="证书编号">{{ cert.cert_no }}</el-descriptions-item>
        <el-descriptions-item label="认证类型">
          <el-tag :type="certTagType(cert.cert_type)" size="small">{{ cert.cert_type }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusType(cert.status)" size="small">{{ statusLabel(cert.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="发证机构">{{ cert.issuing_body }}</el-descriptions-item>
        <el-descriptions-item label="签发日期">{{ cert.issue_date?.slice(0, 10) }}</el-descriptions-item>
        <el-descriptions-item label="到期日期">{{ cert.expiry_date?.slice(0, 10) }}</el-descriptions-item>
        <el-descriptions-item label="备注">{{ cert.remark }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>版本历史时间线</span>
        </div>
      </template>

      <el-timeline v-loading="loadingVersions">
        <el-timeline-item
          v-for="v in versions"
          :key="v.id"
          :timestamp="v.issue_date?.slice(0, 10) || ''"
          :type="v.status === 'active' ? 'primary' : 'info'"
          placement="top"
        >
          <div style="display: flex; justify-content: space-between; align-items: center">
            <div>
              <strong>{{ v.version_no }}</strong> — {{ v.cert_no }}
              <el-tag :type="v.status === 'active' ? 'success' : 'info'" size="small" style="margin-left: 8px">
                {{ v.status === 'active' ? '有效' : v.status === 'superseded' ? '已取代' : '过期' }}
              </el-tag>
            </div>
          </div>
          <div style="font-size: 13px; color: #909399; margin-top: 4px">
            发证机构: {{ v.issuing_body }} | 到期: {{ v.expiry_date?.slice(0, 10) || '永久' }}
          </div>
          <div v-if="v.change_reason" style="font-size: 13px; color: #e6a23c; margin-top: 2px">
            变更原因: {{ v.change_reason }}
          </div>
        </el-timeline-item>
        <el-empty v-if="!versions.length" description="暂无版本历史" />
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../api'

const route = useRoute()
const cert = ref<Record<string, unknown>>({})
const versions = ref<Record<string, unknown>[]>([])
const loading = ref(false)
const loadingVersions = ref(false)

const statusMap: Record<string, string> = { active: '有效', expired: '过期', suspended: '暂停', revoked: '注销' }
const statusTypeMap: Record<string, string> = { active: 'success', expired: 'info', suspended: 'warning', revoked: 'danger' }
function statusLabel(s: string) { return statusMap[s] || s }
function statusType(s: string) { return (statusTypeMap[s] || 'info') as string }

function certTagType(t: string) { const map: Record<string, string> = { CE: 'danger', CB: 'warning', UL: 'primary', SAA: 'success' }; return map[t] || 'info' }

async function fetchCert() {
  loading.value = true
  try {
    const res = await api.get(`/s2/certificates/${route.params.id}`)
    cert.value = res.data || {}
  } finally { loading.value = false }
}

async function fetchVersions() {
  loadingVersions.value = true
  try {
    // Versions are embedded in certificate detail or use a separate endpoint
    // The API doesn't have a dedicated versions endpoint, so we try fetching all
    const res = await api.get(`/s2/certificates/${route.params.id}`)
    // If the response includes versions directly (from the model relationship)
    versions.value = res.data?.versions || []
  } finally { loadingVersions.value = false }
}

onMounted(async () => {
  await fetchCert()
  await fetchVersions()
})
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
