<template>
  <div class="proposals-view">
    <!-- 列表视图 or 子路由视图 -->
    <router-view v-if="$route.path !== '/proposals'" />
    <template v-else>
      <div class="page-header">
        <h2>📝 提案管理</h2>
        <el-button type="primary" @click="$router.push('/proposals/new')">+ 新建立项</el-button>
      </div>
      <el-card shadow="never">
        <el-table :data="proposals" v-loading="loading" stripe style="width:100%">
          <el-table-column prop="id" label="提案编号" width="100" />
          <el-table-column prop="name" label="名称" min-width="200" />
          <el-table-column prop="approval_status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="statusType(row.approval_status)" effect="plain">
                {{ statusLabel(row.approval_status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="viewDetail(row)">查看</el-button>
              <el-button type="warning" link size="small" @click="editDraft(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && proposals.length === 0" description="暂无提案数据" />
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../../api'

interface ProposalItem {
  id: number
  name: string
  approval_status: string | null
  is_draft?: boolean
  created_at: string
  [key: string]: unknown
}

const router = useRouter()
const loading = ref(false)
const proposals = ref<ProposalItem[]>([])

onMounted(() => {
  if (router.currentRoute.value.path === '/proposals') {
    fetchProposals()
  }
})

async function fetchProposals() {
  loading.value = true
  try {
    const res = await api.get('/pm/proposals')
    proposals.value = res.data || []
  } catch (e: unknown) {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

function statusType(status: string | null): string {
  if (!status || status === 'draft') return 'info'
  if (status === 'pending') return 'warning'
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'danger'
  return 'info'
}

function statusLabel(status: string | null): string {
  if (!status || status === 'draft') return '草稿'
  if (status === 'pending') return '审批中'
  if (status === 'approved') return '已通过'
  if (status === 'rejected') return '已驳回'
  return status
}

function viewDetail(_row: ProposalItem) {
  ElMessage.info('详情功能开发中')
}

function editDraft(row: ProposalItem) {
  router.push({ path: '/proposals/new', query: { draft: String(row.id) } })
}
</script>

<style scoped>
.proposals-view {
  padding: 0;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}
</style>
