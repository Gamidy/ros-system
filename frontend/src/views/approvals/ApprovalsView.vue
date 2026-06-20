<template>
  <div class="page">
    <el-card shadow="never">
      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <!-- 我的审批 -->
        <el-tab-pane label="我的审批" name="pending">
          <el-table :data="list" stripe border max-height="420" v-loading="loading">
            <el-table-column prop="id" label="审批编号" width="140" />
            <el-table-column prop="type" label="类型" width="110">
              <template #default="{ row }">
                <el-tag size="small">{{ typeMap[row.type] || row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
            <el-table-column prop="applicant" label="申请人" width="100" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusType[row.status] || 'info'" size="small">{{ statusMap[row.status] || row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="submitted_at" label="提交时间" width="170" />
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="showDetail(row)">详情</el-button>
                <el-button type="success" size="small" @click="handleApprove(row)">通过</el-button>
                <el-button type="danger" size="small" @click="handleReject(row)">驳回</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div style="margin-top: 16px; display: flex; justify-content: flex-end;">
            <el-pagination
              v-model:current-page="page"
              v-model:page-size="pageSize"
              :total="total"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="fetchList"
              @current-change="fetchList"
            />
          </div>
        </el-tab-pane>

        <!-- 审批历史 -->
        <el-tab-pane label="审批历史" name="history">
          <div style="margin-bottom: 16px; display: flex; justify-content: space-between;">
            <el-select v-model="statusFilter" placeholder="状态筛选" clearable @change="fetchList" style="width: 160px">
              <el-option label="全部" value="" />
              <el-option label="已通过" value="approved" />
              <el-option label="已驳回" value="rejected" />
            </el-select>
            <div></div>
          </div>
          <el-table :data="list" stripe border max-height="420" v-loading="loading">
            <el-table-column prop="id" label="审批编号" width="140" />
            <el-table-column prop="type" label="类型" width="110">
              <template #default="{ row }">
                <el-tag size="small">{{ typeMap[row.type] || row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
            <el-table-column prop="applicant" label="申请人" width="100" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusType[row.status] || 'info'" size="small">{{ statusMap[row.status] || row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="submitted_at" label="提交时间" width="170" />
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="showDetail(row)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div style="margin-top: 16px; display: flex; justify-content: flex-end;">
            <el-pagination
              v-model:current-page="page"
              v-model:page-size="pageSize"
              :total="total"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="fetchList"
              @current-change="fetchList"
            />
          </div>
        </el-tab-pane>

        <!-- 审批链配置 -->
        <el-tab-pane label="审批链配置" name="chains">
          <el-table :data="chains" stripe border v-loading="loadingChains">
            <el-table-column prop="code" label="编号" width="140" />
            <el-table-column prop="name" label="名称" min-width="180" />
            <el-table-column label="步骤" min-width="300">
              <template #default="{ row }">
                <el-tag v-for="(s, i) in row.steps" :key="i" size="small" style="margin: 0 4px">
                  {{ s.name }}<span v-if="i < row.steps.length - 1" style="margin: 0 4px">→</span>
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="editChain(row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div style="margin-top: 16px; display: flex; justify-content: flex-end;">
            <el-button type="primary" @click="createChain">新建审批链</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 申请详情弹窗 -->
    <el-dialog v-model="detailVisible" title="申请详情" width="520px">
      <template v-if="detailItem">
        <h3 style="margin: 0 0 12px 0; color: #409eff;">申请信息</h3>
        <div class="detail-grid">
          <span class="detail-label">审批编号:</span><span>{{ detailItem.id }}</span>
          <span class="detail-label">申请类型:</span><span>{{ detailItem.request_type === 'register' ? '账号申请' : detailItem.request_type }}</span>
          <span class="detail-label">标题:</span><span>{{ detailItem.title }}</span>
          <template v-if="detailItem.applicant_info">
            <span class="detail-label">申请人:</span><span>{{ detailItem.requester }}</span>
            <span class="detail-label">真实姓名:</span><span>{{ detailItem.applicant_info.full_name || '-' }}</span>
            <span class="detail-label">部门:</span><span>{{ detailItem.applicant_info.department || '-' }}</span>
            <span class="detail-label">职位:</span><span>{{ detailItem.applicant_info.position || '-' }}</span>
            <span class="detail-label">手机号:</span><span>{{ detailItem.applicant_info.phone || '-' }}</span>
            <span class="detail-label">申请理由:</span><span>{{ detailItem.applicant_info.reason || '-' }}</span>
          </template>
          <span class="detail-label">提交时间:</span><span>{{ detailItem.created_at || '-' }}</span>
        </div>
      </template>
      <template #footer>
        <el-button type="primary" size="small" @click="doApprove">✅ 通过</el-button>
        <el-button type="danger" size="small" @click="openRejectDialog">❌ 驳回</el-button>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 驳回意见弹窗 -->
    <el-dialog v-model="rejectVisible" title="驳回意见" width="450px">
      <el-form :model="rejectForm" label-width="80px">
        <el-form-item label="意见" required>
          <el-input v-model="rejectForm.opinion" type="textarea" rows="3" placeholder="请输入驳回原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="primary" :loading="rejecting" @click="doReject">确认驳回</el-button>
      </template>
    </el-dialog>

    <!-- 编辑审批链弹窗 -->
    <el-dialog v-model="chainEditVisible" :title="editingChain ? '编辑审批链' : '新建审批链'" width="600px">
      <el-form :model="chainForm" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="chainForm.name" placeholder="请输入审批链名称" />
        </el-form-item>
        <el-form-item label="步骤">
          <div v-for="(step, idx) in chainForm.steps" :key="idx" class="step-row">
            <el-input v-model="step.name" placeholder="步骤名称" style="width: 160px" />
            <el-select v-model="step.role" placeholder="审批角色" style="width: 180px">
              <el-option label="工程师" value="engineer" />
              <el-option label="模块经理" value="module_manager" />
              <el-option label="研发总监" value="rd_director" />
              <el-option label="总经理" value="general_manager" />
              <el-option label="管理员" value="admin" />
            </el-select>
            <el-button type="danger" size="small" @click="removeStep(idx)" :disabled="chainForm.steps.length <= 1">删除</el-button>
          </div>
          <el-button type="primary" size="small" @click="addStep" style="margin-top: 4px">+ 添加步骤</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="chainEditVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingChain" @click="saveChain">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const activeTab = ref('pending')
const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const statusFilter = ref('')

const statusMap: Record<string, string> = { pending: '待审批', approved: '已通过', rejected: '已驳回' }
const statusType: Record<string, string> = { pending: 'warning', approved: 'success', rejected: 'danger' }
const typeMap: Record<string, string> = { ecr: 'ECR变更', ecn: 'ECN变更', bom: 'BOM变更', certification: '认证' }

// Detail dialog
const detailVisible = ref(false)
const detailItem = ref<any>(null)

// Reject dialog
const rejectVisible = ref(false)
const rejectForm = ref({ opinion: '' })
const rejecting = ref(false)

// Chain management
const chains = ref<any[]>([])
const loadingChains = ref(false)
const chainEditVisible = ref(false)
const editingChain = ref<any>(null)
const savingChain = ref(false)
const chainForm = ref({ name: '', steps: [{ name: '', role: '' }] })

function resetPage() { page.value = 1; fetchList() }

async function fetchList() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (activeTab.value === 'pending') {
      const res = await api.get('/approval/requests/pending', { params })
      list.value = res.data.items ?? res.data ?? []
      total.value = res.data.total ?? list.value.length
    } else {
      if (statusFilter.value) params.status = statusFilter.value
      const res = await api.get('/approval/requests', { params })
      list.value = res.data.items ?? res.data ?? []
      total.value = res.data.total ?? list.value.length
    }
  } catch { /* ignore */ }
  finally { loading.value = false }
}

function onTabChange() { resetPage() }

// 详情弹窗
function showDetail(row: any) {
  detailItem.value = row
  detailVisible.value = true
}

// 通过
async function handleApprove(row: any) {
  detailItem.value = row
  detailVisible.value = true
}
function doApprove() {
  if (!detailItem.value) return
  const id = detailItem.value.id
  api.post(`/approval/requests/${id}/approve`)
    .then(() => {
      ElMessage.success('审批通过')
      detailVisible.value = false
      detailItem.value = null
      fetchList()
      // 刷新通知计数
      window.dispatchEvent(new CustomEvent('approval-updated'))
    })
    .catch(() => {})
}

// 驳回
function handleReject(row: any) {
  detailItem.value = row
  openRejectDialog()
}
function openRejectDialog() {
  rejectForm.value = { opinion: '' }
  rejectVisible.value = true
}
async function doReject() {
  if (!rejectForm.value.opinion.trim()) {
    ElMessage.warning('请输入驳回意见')
    return
  }
  if (!detailItem.value) return
  rejecting.value = true
  try {
    await api.post(`/approval/requests/${detailItem.value.id}/reject`, { opinion: rejectForm.value.opinion })
    ElMessage.success('已驳回')
    rejectVisible.value = false
    detailVisible.value = false
    detailItem.value = null
    fetchList()
    window.dispatchEvent(new CustomEvent('approval-updated'))
  } catch { /* ignore */ }
  finally { rejecting.value = false }
}

// 审批链管理
async function fetchChains() {
  loadingChains.value = true
  try {
    const res = await api.get('/approval/chains')
    chains.value = res.data ?? []
  } catch { /* ignore */ }
  finally { loadingChains.value = false }
}

function editChain(chain: any) {
  editingChain.value = chain
  chainForm.value = {
    id: chain.id,
    code: chain.code,
    name: chain.name,
    steps: (chain.steps || []).map((s: any) => ({ ...s })),
  }
  chainEditVisible.value = true
}

function createChain() {
  editingChain.value = null
  chainForm.value = { name: '', steps: [{ name: '', role: '' }] }
  chainEditVisible.value = true
}

function addStep() { chainForm.value.steps.push({ name: '', role: '' }) }
function removeStep(idx: number) { chainForm.value.steps.splice(idx, 1) }

async function saveChain() {
  if (!chainForm.value.name.trim()) {
    ElMessage.warning('请输入审批链名称')
    return
  }
  savingChain.value = true
  try {
    await api.post('/approval/chains', chainForm.value)
    ElMessage.success('保存成功')
    chainEditVisible.value = false
    await fetchChains()
  } catch { /* ignore */ }
  finally { savingChain.value = false }
}

onMounted(() => { fetchList(); fetchChains() })
</script>

<style scoped>
.detail-grid {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 8px;
  font-size: 14px;
  line-height: 28px;
}
.detail-label {
  color: #909399;
}
.step-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
}
.page {
  /* ensure consistent layout */
}
</style>
