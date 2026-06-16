<template>
  <div class="page">
    <el-card shadow="never">
      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <!-- ═══ 我的审批 ═══ -->
        <el-tab-pane label="我的审批" name="pending">
          <el-table :data="items" stripe border max-height="420" v-loading="loading">
            <el-table-column prop="id" label="审批编号" width="140" />
            <el-table-column prop="type" label="类型" width="110">
              <template #default="{ row }">
                <el-tag size="small">{{ typeLabel(row.type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
            <el-table-column prop="applicant" label="申请人" width="100" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">
                  {{ statusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="submitted_at" label="提交时间" width="170" />
            <el-table-column label="操作" width="170" fixed="right">
              <template #default="{ row }">
                <el-button type="success" size="small" @click="handleApprove(row)">通过</el-button>
                <el-button type="danger" size="small" @click="openRejectDialog(row)">驳回</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div style="margin-top: 16px; display: flex; justify-content: flex-end">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :total="total"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="fetchData"
              @current-change="fetchData"
            />
          </div>
        </el-tab-pane>

        <!-- ═══ 审批历史 ═══ -->
        <el-tab-pane label="审批历史" name="history">
          <div style="margin-bottom: 16px; display: flex; justify-content: space-between">
            <el-select
              v-model="filterStatus"
              placeholder="状态筛选"
              clearable
              @change="fetchData"
              style="width: 160px"
            >
              <el-option label="全部" value="" />
              <el-option label="已通过" value="approved" />
              <el-option label="已驳回" value="rejected" />
            </el-select>
            <div />
          </div>
          <el-table :data="items" stripe border max-height="420" v-loading="loading">
            <el-table-column prop="id" label="审批编号" width="140" />
            <el-table-column prop="type" label="类型" width="110">
              <template #default="{ row }">
                <el-tag size="small">{{ typeLabel(row.type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
            <el-table-column prop="applicant" label="申请人" width="100" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">
                  {{ statusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="submitted_at" label="提交时间" width="170" />
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="viewDetail(row)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div style="margin-top: 16px; display: flex; justify-content: flex-end">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :total="total"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="fetchData"
              @current-change="fetchData"
            />
          </div>
        </el-tab-pane>

        <!-- ═══ 审批链配置 ═══ -->
        <el-tab-pane label="审批链配置" name="chains">
          <el-table :data="chains" stripe border v-loading="loadingChains">
            <el-table-column prop="code" label="编号" width="140" />
            <el-table-column prop="name" label="名称" min-width="180" />
            <el-table-column label="步骤" min-width="300">
              <template #default="{ row }">
                <el-tag
                  size="small"
                  v-for="(step, i) in row.steps"
                  :key="i"
                >{{ step.name }}<span v-if="i < row.steps.length-1" style="margin:0 4px">→</span></el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="editChain(row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div style="margin-top: 16px; display: flex; justify-content: flex-end">
            <el-button type="primary" @click="createChain">新建审批链</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 驳回对话框 -->
    <el-dialog v-model="rejectDialogVisible" title="驳回意见" width="450">
      <el-form :model="rejectForm" label-width="80">
        <el-form-item label="意见" required>
          <el-input
            v-model="rejectForm.opinion"
            type="textarea"
            :rows="3"
            placeholder="请输入驳回原因"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="rejecting" @click="handleReject">确认驳回</el-button>
      </template>
    </el-dialog>

    <!-- 审批链编辑对话框 -->
    <el-dialog v-model="showChainDialog" :title="editingChain ? '编辑审批链' : '新建审批链'" width="600">
      <el-form :model="selectedChain" label-width="80">
        <el-form-item label="名称" required>
          <el-input v-model="selectedChain.name" placeholder="请输入审批链名称" />
        </el-form-item>
        <el-form-item label="步骤">
          <div v-for="(step, idx) in selectedChain.steps" :key="idx" style="display:flex; gap:8px; margin-bottom:8px; align-items:center">
            <el-input v-model="step.name" placeholder="步骤名称" style="width:160px" />
            <el-select v-model="step.role" placeholder="审批角色" style="width:180px">
              <el-option label="工程师" value="engineer" />
              <el-option label="模块经理" value="module_manager" />
              <el-option label="研发总监" value="rd_director" />
              <el-option label="总经理" value="general_manager" />
              <el-option label="管理员" value="admin" />
            </el-select>
            <el-button type="danger" size="small" @click="removeStep(idx)" :disabled="selectedChain.steps.length <= 1">删除</el-button>
          </div>
          <el-button type="primary" size="small" @click="addStep" style="margin-top:4px">+ 添加步骤</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showChainDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingChain" @click="saveChain">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

/* ── 基础状态 ── */
const activeTab = ref('pending')
const loading = ref(false)
const rejecting = ref(false)

/* ── 列表 & 分页 ── */
const items = ref<any[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const filterStatus = ref('')

/* ── 驳回对话框 ── */
const rejectDialogVisible = ref(false)
const rejectForm = ref({ opinion: '' })
const rejectTargetId = ref<number | null>(null)

/* ── 审批链配置 ── */
const chains = ref<any[]>([])
const loadingChains = ref(false)
const showChainDialog = ref(false)
const savingChain = ref(false)
const editingChain = ref<any>(null)
const selectedChain = ref<any>({
  name: '',
  steps: [{ name: '', role: '' }],
})

/* ── 状态 / 类型 映射 ── */
const statusMap: Record<string, string> = {
  pending: '待审批',
  approved: '已通过',
  rejected: '已驳回',
}
const statusTypeMap: Record<string, string> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
}
const typeMap: Record<string, string> = {
  ecr: 'ECR变更',
  ecn: 'ECN变更',
  bom: 'BOM变更',
  certification: '认证',
}

function statusLabel(s: string) {
  return statusMap[s] || s
}
function statusType(s: string) {
  return statusTypeMap[s] || 'info'
}
function typeLabel(s: string) {
  return typeMap[s] || s
}

/* ── 切换 Tab 时重置分页 ── */
function onTabChange() {
  currentPage.value = 1
  fetchData()
}

/* ── 获取数据 ── */
async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: currentPage.value,
      page_size: pageSize.value,
    }

    if (activeTab.value === 'pending') {
      const r = await api.get('/approval/requests/pending', { params })
      const data = r.data
      items.value = data.items ?? data ?? []
      total.value = data.total ?? items.value.length
    } else {
      if (filterStatus.value) params.status = filterStatus.value
      const r = await api.get('/approval/requests', { params })
      const data = r.data
      items.value = data.items ?? data ?? []
      total.value = data.total ?? items.value.length
    }
  } catch {
    // API 拦截器已处理错误提示
  } finally {
    loading.value = false
  }
}

/* ── 通过 ── */
async function handleApprove(row: any) {
  try {
    await api.post(`/approval/requests/${row.id}/approve`)
    ElMessage.success('审批通过')
    await fetchData()
  } catch {
    // API 拦截器已处理
  }
}

/* ── 打开驳回对话框 ── */
function openRejectDialog(row: any) {
  rejectTargetId.value = row.id
  rejectForm.value = { opinion: '' }
  rejectDialogVisible.value = true
}

/* ── 提交驳回 ── */
async function handleReject() {
  if (!rejectForm.value.opinion.trim()) {
    ElMessage.warning('请输入驳回意见')
    return
  }
  rejecting.value = true
  try {
    await api.post(`/approval/requests/${rejectTargetId.value}/reject`, {
      opinion: rejectForm.value.opinion,
    })
    ElMessage.success('已驳回')
    rejectDialogVisible.value = false
    await fetchData()
  } catch {
    // API 拦截器已处理
  } finally {
    rejecting.value = false
  }
}

/* ── 查看历史详情（占位） ── */
function viewDetail(row: any) {
  ElMessage.info(`审批 #${row.id} 详情`)
}

/* ── 获取审批链 ── */
async function fetchChains() {
  loadingChains.value = true
  try {
    const r = await api.get('/approval/chains')
    chains.value = r.data ?? []
  } catch {
    // API 拦截器已处理
  } finally {
    loadingChains.value = false
  }
}

/* ── 编辑审批链 ── */
function editChain(row: any) {
  editingChain.value = row
  selectedChain.value = {
    id: row.id,
    code: row.code,
    name: row.name,
    steps: (row.steps || []).map((s: any) => ({ ...s })),
  }
  showChainDialog.value = true
}

/* ── 新建审批链 ── */
function createChain() {
  editingChain.value = null
  selectedChain.value = {
    name: '',
    steps: [{ name: '', role: '' }],
  }
  showChainDialog.value = true
}

/* ── 添加步骤 ── */
function addStep() {
  selectedChain.value.steps.push({ name: '', role: '' })
}

/* ── 删除步骤 ── */
function removeStep(index: number) {
  selectedChain.value.steps.splice(index, 1)
}

/* ── 保存审批链 ── */
async function saveChain() {
  if (!selectedChain.value.name.trim()) {
    ElMessage.warning('请输入审批链名称')
    return
  }
  savingChain.value = true
  try {
    await api.post('/approval/chains', selectedChain.value)
    ElMessage.success('保存成功')
    showChainDialog.value = false
    await fetchChains()
  } catch {
    // API 拦截器已处理
  } finally {
    savingChain.value = false
  }
}

onMounted(() => {
  fetchData()
  fetchChains()
})
</script>

<style scoped>
.page {
  padding: 0;
}
</style>
