<template>
  <div class="my-org-info">
    <h2>🏢 我的组织</h2>

    <el-card shadow="never" v-loading="loading">
      <template #header>
        <span>{{ orgInfo?.name || '组织信息' }}</span>
        <el-tag v-if="orgInfo?.is_active" type="success" size="small" style="margin-left: 8px;">启用</el-tag>
        <el-tag v-else-if="orgInfo && !orgInfo.is_active" type="danger" size="small" style="margin-left: 8px;">禁用</el-tag>
      </template>

      <el-empty v-if="!orgInfo && !loading" description="暂未加入任何组织" />

      <template v-if="orgInfo">
        <div class="info-grid">
          <div class="info-item">
            <span class="label">组织代码</span>
            <span class="value">{{ orgInfo.code || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">联系人</span>
            <span class="value">{{ orgInfo.contact_person || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">邮箱</span>
            <span class="value">{{ orgInfo.email || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">电话</span>
            <span class="value">{{ orgInfo.phone || '-' }}</span>
          </div>
          <div class="info-item" style="grid-column: 1 / -1;">
            <span class="label">地址</span>
            <span class="value">{{ orgInfo.address || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">成员数</span>
            <span class="value">{{ orgInfo.user_count ?? '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">创建时间</span>
            <span class="value">{{ formatTime(orgInfo.created_at) }}</span>
          </div>
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'

interface OrgInfo {
  id: number
  name: string
  code: string
  contact_person: string
  email: string
  phone: string
  address: string
  is_active: boolean
  user_count: number
  created_at: string
}

const loading = ref(false)
const orgInfo = ref<OrgInfo | null>(null)

function formatTime(t: string) {
  if (!t) return '-'
  const d = new Date(t)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function fetchMyOrg() {
  loading.value = true
  try {
    const res = await api.get('/auth/my-org')
    orgInfo.value = (res.data?.data || res.data) as OrgInfo | null
  } catch {
    orgInfo.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchMyOrg()
})
</script>

<style scoped>
.my-org-info {
  padding: 16px;
  max-width: 600px;
}
.my-org-info h2 {
  margin: 0 0 16px;
  font-size: 18px;
}
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.info-item .label {
  font-size: 12px;
  color: #909399;
}
.info-item .value {
  font-size: 14px;
  color: #303133;
}
</style>
