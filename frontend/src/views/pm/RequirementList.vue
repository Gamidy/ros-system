<template>
  <div class="requirement-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>需求管理</span>
        </div>
      </template>

      <!-- 状态过滤 Tabs -->
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane label="待处理" name="pending" />
        <el-tab-pane label="已采纳" name="accepted" />
        <el-tab-pane label="已转化" name="converted" />
        <el-tab-pane label="已拒绝" name="rejected" />
      </el-tabs>

      <!-- 数据表格 -->
      <el-table :data="list" v-loading="loading" stripe border style="width:100%">
        <el-table-column prop="market_name" label="市场" min-width="100" />
        <el-table-column prop="product_type" label="产品类型" width="100" />
        <el-table-column prop="target_capacity" label="冷量" width="90" />
        <el-table-column prop="target_price" label="目标价格" width="110">
          <template #default="{ row }">
            ¥{{ row.target_price ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="energy_standard" label="能效标准" width="90" />
        <el-table-column prop="submitted_by_name" label="提交人" min-width="90" />
        <el-table-column prop="created_at" label="提交时间" width="170">
          <template #default="{ row }">
            {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <!-- 待处理：可采纳/拒绝，可一键生成策划 -->
            <template v-if="row.status === 'pending'">
              <el-button size="small" type="success" @click="handleAccept(row)">采纳</el-button>
              <el-button size="small" type="danger" @click="handleReject(row)">拒绝</el-button>
              <el-button
                size="small" type="primary"
                :loading="convertingId === row.id"
                @click="handleConvert(row)"
              >📋 生成策划</el-button>
            </template>
            <!-- 已采纳：可生成策划 -->
            <template v-else-if="row.status === 'accepted'">
              <el-button
                size="small" type="primary"
                :loading="convertingId === row.id"
                @click="handleConvert(row)"
              >📋 生成策划</el-button>
              <span v-if="row.converted_plan_id" style="color:#909399;font-size:12px;margin-left:8px">已转化</span>
            </template>
            <!-- 已转化：显示跳转链接 -->
            <template v-else-if="row.status === 'converted' && row.converted_plan_id">
              <el-button size="small" link type="primary" @click="goPlan(row.converted_plan_id)">
                查看策划
              </el-button>
            </template>
            <!-- 其他状态 -->
            <span v-else style="color:#909399;font-size:12px">—</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrap" v-if="total > 0">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchList"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listRequirements,
  updateRequirementStatus,
  convertToPlan,
  convertRequirementToPlan,
} from '../../api/productPlan'
import type { RequirementItem } from '../../api/productPlan'

const router = useRouter()

const loading = ref(false)
const convertingId = ref<string | null>(null)
const list = ref<RequirementItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const activeTab = ref('all')

// ── 状态映射 ──

const STATUS_MAP: Record<string, string> = {
  pending: '待处理',
  accepted: '已采纳',
  converted: '已转化',
  rejected: '已拒绝',
}

function statusLabel(status: string): string {
  return STATUS_MAP[status] || status
}

function statusTagType(status: string): string {
  const map: Record<string, string> = {
    pending: 'warning',
    accepted: 'success',
    converted: 'primary',
    rejected: 'danger',
  }
  return map[status] || 'info'
}

// ── 数据获取 ──

async function fetchList() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (activeTab.value !== 'all') {
      params.status = activeTab.value
    }
    const res = await listRequirements(params)
    const data = res.data
    list.value = data.items || data.data || []
    total.value = data.total || 0
  } catch {
    // 错误由拦截器处理
  } finally {
    loading.value = false
  }
}

function handleTabChange() {
  page.value = 1
  fetchList()
}

// ── 操作 ──

/** 采纳需求 */
async function handleAccept(row: RequirementItem) {
  try {
    await ElMessageBox.confirm('确认采纳该需求？', '采纳确认', { type: 'info' })
    await updateRequirementStatus(row.id, 'accepted')
    ElMessage.success('已采纳')
    fetchList()
  } catch {
    // 取消或错误
  }
}

/** 拒绝需求（需填写原因） */
async function handleReject(row: RequirementItem) {
  try {
    const { value } = await ElMessageBox.prompt('请填写拒绝原因', '拒绝', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputPlaceholder: '拒绝原因',
      inputValidator: (v: string) => (v ? true : '请填写拒绝原因'),
    })
    await updateRequirementStatus(row.id, 'rejected', value)
    ElMessage.success('已拒绝')
    fetchList()
  } catch {
    // 取消或错误
  }
}

/** 「📋 生成策划」一键转换 — 调用后端创建草稿并跳转到详情页 */
async function handleConvert(row: RequirementItem) {
  try {
    await ElMessageBox.confirm('确认将该需求转为产品策划草稿？', '生成策划确认', { type: 'info' })
    convertingId.value = row.id
    const res = await convertRequirementToPlan(row.id)
    const planId: string | undefined = res.data?.plan_id
    if (planId) {
      ElMessage.success('策划草稿已生成，正在跳转...')
      router.push(`/product-plans/${planId}`)
    } else {
      ElMessage.success('策划草稿已生成')
      fetchList()
    }
  } catch {
    // 取消或错误
  } finally {
    convertingId.value = null
  }
}

function goPlan(planId: number) {
  router.push(`/product-plans/${planId}`)
}

// ── 初始化 ──

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.requirement-list {
  padding: 16px;
}
.card-header {
  font-size: 16px;
  font-weight: 600;
}
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
