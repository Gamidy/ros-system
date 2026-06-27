<template>
  <div class="standards-view">
    <el-page-header title="标准知识库" @back="$router.push('/dashboard')" />

    <!-- 概览统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-num">{{ stats.total_active }}</div>
          <div class="stat-label">活跃标准</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-num warning">{{ stats.new_last_7d }}</div>
          <div class="stat-label">本周新增</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-num success">{{ stats.new_last_30d }}</div>
          <div class="stat-label">本月新增</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-num danger">{{ stats.upcoming_effective }}</div>
          <div class="stat-label">即将生效</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选栏 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="query" size="small">
        <el-form-item label="地区">
          <el-select v-model="query.region" clearable placeholder="全部" style="width:120px">
            <el-option v-for="r in regions" :key="r.code" :label="r.name" :value="r.code">
              <span>{{ r.name }}</span>
              <span class="region-tag">({{ r.code }})</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="query.category" clearable placeholder="全部" style="width:120px">
            <el-option v-for="c in categories" :key="c.code" :label="c.name" :value="c.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="全部" style="width:100px">
            <el-option label="已生效" value="active" />
            <el-option label="已废止" value="superseded" />
            <el-option label="草案中" value="draft" />
            <el-option label="已撤销" value="repealed" />
          </el-select>
        </el-form-item>
        <el-form-item label="影响等级">
          <el-select v-model="query.impact" clearable placeholder="全部" style="width:100px">
            <el-option label="🔴 严重" value="critical" />
            <el-option label="🟠 高" value="high" />
            <el-option label="🟡 中" value="medium" />
            <el-option label="🟢 低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="query.search"
            placeholder="搜索标准编号/标题..."
            clearable
            style="width:240px"
            @keyup.enter="search"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格 -->
    <el-card class="table-card">
      <el-table :data="page.items" v-loading="loading" stripe highlight-current-row>
        <el-table-column prop="std_number" label="标准编号" width="180" sortable />
        <el-table-column label="地区" width="100">
          <template #default="{ row }">
            <el-tag :type="row.region_code === 'EU' ? 'primary' :
              row.region_code === 'US' ? 'success' :
              row.region_code === 'SA' ? 'warning' : 'info'" size="small">
              {{ row.region_name || row.region_code }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category_name" label="分类" width="120" />
        <el-table-column prop="title" label="标题" min-width="300" show-overflow-tooltip />
        <el-table-column prop="version" label="版本" width="80" />
        <el-table-column prop="effective_date" label="生效日期" width="120" />
        <el-table-column label="影响" width="80" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.impact_level === 'critical' ? 'danger' :
                row.impact_level === 'high' ? 'warning' :
                row.impact_level === 'medium' ? 'info' : 'success'"
              size="small"
              effect="plain"
            >
              {{ row.impact_level === 'critical' ? '严重' :
                 row.impact_level === 'high' ? '高' :
                 row.impact_level === 'medium' ? '中' : '低' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewDetail(row.id)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page.page"
          v-model:page-size="page.page_size"
          :total="page.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @change="loadData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import type { StandardPage, RegionItem, CategoryItem, RecentStats } from '@/api/standards'
import { listStandards, listRegions, listCategories, getStandardStats } from '@/api/standards'

const router = useRouter()
const loading = ref(false)

// 筛选条件
const query = reactive({
  region: '',
  category: '',
  status: '',
  impact: '',
  search: '',
  page: 1,
  page_size: 20,
})

// 数据
const page = reactive<StandardPage>({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 })
const regions = ref<RegionItem[]>([])
const categories = ref<CategoryItem[]>([])
const stats = reactive<RecentStats>({
  total_active: 0, new_last_7d: 0, new_last_30d: 0, upcoming_effective: 0, by_region: [],
})

async function loadData() {
  loading.value = true
  try {
    const res = await listStandards({
      region: query.region || undefined,
      category: query.category || undefined,
      status: query.status || undefined,
      impact: query.impact || undefined,
      search: query.search || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    Object.assign(page, res)
  } finally {
    loading.value = false
  }
}

async function loadMeta() {
  try {
    regions.value = await listRegions()
    categories.value = await listCategories()
    const s = await getStandardStats()
    Object.assign(stats, s)
  } catch { /* ignore */ }
}

function search() {
  query.page = 1
  loadData()
}

function reset() {
  query.region = ''
  query.category = ''
  query.status = ''
  query.impact = ''
  query.search = ''
  query.page = 1
  loadData()
}

function viewDetail(id: number) {
  router.push(`/standards/${id}`)
}

onMounted(() => {
  loadMeta()
  loadData()
})
</script>

<style scoped>
.standards-view { padding: 16px; }
.stats-row { margin-top: 16px; margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-num { font-size: 32px; font-weight: bold; color: #409eff; }
.stat-num.warning { color: #e6a23c; }
.stat-num.success { color: #67c23a; }
.stat-num.danger { color: #f56c6c; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }
.filter-card { margin-bottom: 16px; }
.table-card { margin-bottom: 16px; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: flex-end; }
.region-tag { color: #909399; margin-left: 4px; font-size: 12px; }
</style>
