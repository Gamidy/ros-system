<template>
  <div class="page">
    <!-- ═══════ 统计卡片 ═══════ -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="4">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" style="color:#409eff">{{ stats.this_month_new }}</div>
          <div class="stat-label">本月新增</div>
        </el-card>
      </el-col>
      <el-col :span="5">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" style="color:#e6a23c">{{ stats.pending_verification }}</div>
          <div class="stat-label">待验证</div>
        </el-card>
      </el-col>
      <el-col :span="5">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" style="color:#409eff">{{ inProgressCount }}</div>
          <div class="stat-label">进行中</div>
        </el-card>
      </el-col>
      <el-col :span="5">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" style="color:#67c23a">{{ effectiveCount }}</div>
          <div class="stat-label">已生效</div>
        </el-card>
      </el-col>
      <el-col :span="5">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" style="color:#909399">{{ closedThisMonth }}</div>
          <div class="stat-label">本月关闭</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ═══════ 图表行 ═══════ -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <!-- 状态分布 -->
      <el-col :span="12">
        <el-card shadow="never">
          <template #header><span>状态分布</span></template>
          <div style="padding: 8px 0">
            <div v-for="(count, status) in processStatusDistribution" :key="status" class="dist-row">
              <span class="dist-label">{{ statusLabel(status) }}</span>
              <el-progress
                :percentage="statusPercent(count)"
                :color="statusColor(status)"
                :stroke-width="18"
                :text-inside="true"
                :format="() => `${count}`"
              />
            </div>
            <div v-if="Object.keys(processStatusDistribution).length === 0" style="text-align:center;color:#999;padding:20px">
              暂无数据
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 变更类型分布 -->
      <el-col :span="12">
        <el-card shadow="never">
          <template #header><span>变更类型分布</span></template>
          <div style="padding: 8px 0">
            <div v-for="(count, type) in typeDistribution" :key="type" class="dist-row">
              <span class="dist-label">{{ changeTypeLabel(type) }}</span>
              <el-progress
                :percentage="typePercent(count)"
                :stroke-width="18"
                :text-inside="true"
                :format="() => `${count}`"
              />
            </div>
            <div v-if="Object.keys(typeDistribution).length === 0" style="text-align:center;color:#999;padding:20px">
              暂无数据
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ═══════ 最近变更列表 ═══════ -->
    <el-card shadow="never">
      <template #header><span>最近变更（最近10条）</span></template>
      <el-table :data="recentChanges" stripe border v-loading="loading" style="width:100%">
        <el-table-column prop="code" label="ECO编号" width="140" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="item_count" label="明细项数" width="90" align="center" />
        <el-table-column prop="effective_date" label="生效日期" width="110" />
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="$router.push(`/eco/${row.id}`)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { fetchChangeDashboard, type ECOChDashboard, type ECOOut } from '../../api/eco'

// ── 状态映射 ──
const statusMap: Record<string, string> = {
  draft: '草稿',
  implementing: '实施中',
  verified: '已验证',
  effective: '已生效',
  closed: '已关闭',
  cancelled: '已取消',
}
const statusTypeMap: Record<string, string> = {
  draft: 'info',
  implementing: 'warning',
  verified: 'primary',
  effective: 'success',
  closed: 'info',
  cancelled: 'danger',
}
const changeTypeMap: Record<string, string> = {
  add: '新增',
  modify: '修改',
  replace: '替换',
  delete: '删除',
  disable: '禁用',
}
function statusLabel(s: string) { return statusMap[s] || s }
function statusType(s: string) { return statusTypeMap[s] || 'info' }
function changeTypeLabel(s: string) { return changeTypeMap[s] || s }
function statusColor(s: string) { return statusTypeMap[s] || '#909399' }

// ── 数据 ──
const loading = ref(false)
const dashboard = ref<ECOChDashboard>({
  status_summary: {},
  type_distribution: {},
  this_month_new: 0,
  pending_verification: 0,
  changes: [],
})

const stats = computed(() => ({
  this_month_new: dashboard.value.this_month_new,
  pending_verification: dashboard.value.pending_verification,
}))

const processStatusDistribution = computed(() => dashboard.value.status_summary || {})
const typeDistribution = computed(() => dashboard.value.type_distribution || {})
const recentChanges = computed<ECOOut[]>(() => (dashboard.value.changes || []).slice(0, 10))

const inProgressCount = computed(() => {
  const s = dashboard.value.status_summary || {}
  return (s.implementing || 0) + (s.verified || 0)
})

const effectiveCount = computed(() => {
  const s = dashboard.value.status_summary || {}
  return s.effective || 0
})

const closedThisMonth = computed(() => {
  const s = dashboard.value.status_summary || {}
  return s.closed || 0
})

// ── 分布百分比 ──
function statusPercent(count: number) {
  const total = Object.values(processStatusDistribution.value).reduce((a: number, b: number) => a + (Number(b) || 0), 0)
  return total > 0 ? Math.round((count / total) * 100) : 0
}
function typePercent(count: number) {
  const total = Object.values(typeDistribution.value).reduce((a: number, b: number) => a + (Number(b) || 0), 0)
  return total > 0 ? Math.round((count / total) * 100) : 0
}

async function fetchData() {
  loading.value = true
  try {
    const res = await fetchChangeDashboard()
    dashboard.value = res
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.stat-card { text-align: center; padding: 8px 0; }
.stat-value { font-size: 32px; font-weight: 700; line-height: 1.2; }
.stat-label { font-size: 13px; color: #909399; margin-top: 6px; }
.dist-row { display: flex; align-items: center; margin-bottom: 12px; }
.dist-label { width: 80px; font-size: 13px; flex-shrink: 0; color: #606266; }
.dist-row .el-progress { flex: 1; }
</style>
