<template>
  <div class="cert-impact">
    <div class="page-header">
      <h2>变更影响链可视化</h2>
    </div>

    <!-- Filters -->
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6">
        <el-select v-model="filterImpactLevel" placeholder="影响级别" clearable @change="onFilterChange" style="width: 100%">
          <el-option label="全部级别" value="" />
          <el-option label="严重" value="critical" />
          <el-option label="较大" value="major" />
          <el-option label="轻微" value="minor" />
          <el-option label="无影响" value="none" />
        </el-select>
      </el-col>
      <el-col :span="6">
        <el-select v-model="filterSourceType" placeholder="来源类型" clearable @change="onFilterChange" style="width: 100%">
          <el-option label="全部来源" value="" />
          <el-option label="ECR" value="ecr" />
          <el-option label="ECO" value="eco" />
          <el-option label="样机(Prototype)" value="prototype" />
        </el-select>
      </el-col>
      <el-col :span="6">
        <el-button type="primary" @click="fetchData">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </el-col>
    </el-row>

    <!-- Table -->
    <el-table
      :data="records"
      v-loading="loading"
      stripe
      border
      style="width: 100%"
      @expand-change="onExpandChange"
      row-key="id"
    >
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="expand-detail" style="padding: 12px 24px">
            <el-descriptions title="变更影响详情" :column="2" border>
              <el-descriptions-item label="影响描述" :span="2">
                {{ row.analysis_detail || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="影响的证书类型">
                <template v-if="row.affected_cert_types">
                  <el-tag
                    v-for="ct in parseCertTypes(row.affected_cert_types)"
                    :key="ct"
                    style="margin-right: 4px; margin-bottom: 2px"
                    size="small"
                  >
                    {{ ct }}
                  </el-tag>
                </template>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="来源实体">
                {{ getSourceEntityLabel(row) }}
              </el-descriptions-item>
              <el-descriptions-item label="来源ID">
                {{ row.ecr_id || row.prototype_id || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="变更部件">
                {{ row.changed_part || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="匹配规则ID">
                {{ row.matched_rule_id || '-' }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="id" label="ID" width="60" sortable />
      <el-table-column label="关联类型" min-width="150">
        <template #default="{ row }">
          <el-tag size="small" type="info">
            {{ row.changed_part || '通用变更' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="影响级别" width="120" sortable>
        <template #default="{ row }">
          <el-tag :type="levelTag(row.impact_level)" size="small">
            {{ levelLabel(row.impact_level) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="来源" width="140">
        <template #default="{ row }">
          {{ getSourceLabel(row) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default>
          <el-tag type="success" size="small">已分析</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="分析时间" width="170" sortable>
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
    </el-table>

    <!-- Pagination -->
    <div style="margin-top: 16px; display: flex; justify-content: flex-end">
      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="onPageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

// ── Types ──
interface ImpactRecord {
  id: number
  ecr_id: number | null
  prototype_id: number
  changed_part: string | null
  matched_rule_id: number | null
  impact_level: string
  affected_cert_types: string
  analysis_detail: string | null
  org_id: number | null
  created_at: string
}

interface PaginatedResponse {
  total: number
  page: number
  page_size: number
  items: ImpactRecord[]
}

// ── State ──
const loading = ref(false)
const records = ref<ImpactRecord[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterImpactLevel = ref('')
const filterSourceType = ref('')

// ── Helpers ──
const levelTag = (level: string): string => {
  const map: Record<string, string> = {
    critical: 'danger',
    major: 'warning',
    minor: 'info',
    none: 'success',
  }
  return map[level] || 'info'
}

const levelLabel = (level: string): string => {
  const map: Record<string, string> = {
    critical: '严重',
    major: '较大',
    minor: '轻微',
    none: '无影响',
  }
  return map[level] || level
}

const parseCertTypes = (val: string): string[] => {
  try {
    const parsed = JSON.parse(val)
    return Array.isArray(parsed) ? parsed : [val]
  } catch {
    return [val]
  }
}

const formatDate = (d: string): string => {
  if (!d) return '-'
  return d.substring(0, 19).replace('T', ' ')
}

const getSourceLabel = (row: ImpactRecord): string => {
  if (row.ecr_id) return 'ECR'
  if (row.prototype_id) return '样机(Prototype)'
  return '-'
}

const getSourceEntityLabel = (row: ImpactRecord): string => {
  if (row.ecr_id) return `ECR #${row.ecr_id}`
  if (row.prototype_id) return `Prototype #${row.prototype_id}`
  return '-'
}

// ── Data Fetching ──
const buildParams = () => {
  const params: Record<string, string | number> = {
    page: page.value,
    page_size: pageSize.value,
  }
  if (filterImpactLevel.value) {
    params.impact_level = filterImpactLevel.value
  }
  if (filterSourceType.value) {
    params.source_type = filterSourceType.value
  }
  return params
}

const fetchData = async () => {
  loading.value = true
  try {
    const { data } = await api.get<PaginatedResponse>('/s2/change-impact/records', {
      params: buildParams(),
    })
    if (data.items) {
      records.value = data.items
      total.value = data.total
    } else if (Array.isArray(data)) {
      // Fallback for non-paginated response
      records.value = data as unknown as ImpactRecord[]
      total.value = data.length
    } else {
      records.value = []
      total.value = 0
    }
  } catch {
    ElMessage.error('加载影响分析数据失败')
    records.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const onFilterChange = () => {
  page.value = 1
  fetchData()
}

const resetFilters = () => {
  filterImpactLevel.value = ''
  filterSourceType.value = ''
  page.value = 1
  fetchData()
}

const onPageChange = (p: number) => {
  page.value = p
  fetchData()
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const onExpandChange = (_row: ImpactRecord, expandedRows: ImpactRecord[]) => {
  // Can be used to lazy-load detail data if needed
  void _row
  void expandedRows
}

// ── Lifecycle ──
onMounted(fetchData)
</script>

<style scoped>
.cert-impact {
  padding: 16px;
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
}
.expand-detail {
  background-color: #fafafa;
  border-radius: 4px;
}
</style>
