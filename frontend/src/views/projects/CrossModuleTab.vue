<template>
  <div class="cross-module-tab">
    <el-skeleton :loading="loading" animated :count="3">
      <template #default>
        <!-- 关联产品 -->
        <el-card shadow="never" class="section-card" v-if="data.product">
          <template #header><span>📦 关联产品</span></template>
          <div class="info-grid">
            <div class="info-item"><span class="label">产品编码</span><span>{{ data.product.code }}</span></div>
            <div class="info-item"><span class="label">产品名称</span><span>{{ data.product.name }}</span></div>
            <div class="info-item"><span class="label">状态</span><el-tag size="small">{{ data.product.status }}</el-tag></div>
            <div class="info-item"><span class="label">分类</span><span>{{ data.product.category || '-' }}</span></div>
          </div>
        </el-card>

        <!-- BOM清单 -->
        <el-card shadow="never" class="section-card" v-if="data.boms && data.boms.length > 0">
          <template #header><span>📋 BOM清单 ({{ data.boms.length }})</span></template>
          <el-table :data="data.boms" stripe border size="small">
            <el-table-column prop="name" label="BOM名称" min-width="150" />
            <el-table-column prop="bom_type" label="类型" width="80" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{row}"><el-tag size="small">{{ row.status }}</el-tag></template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 认证记录 -->
        <el-card shadow="never" class="section-card" v-if="data.certifications && data.certifications.length > 0">
          <template #header><span>🔒 认证记录 ({{ data.certifications.length }})</span></template>
          <el-table :data="data.certifications" stripe border size="small">
            <el-table-column prop="name" label="认证名称" min-width="150" />
            <el-table-column prop="type" label="类型" width="80" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{row}"><el-tag size="small">{{ row.status }}</el-tag></template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- ECR/ECO -->
        <el-card shadow="never" class="section-card" v-if="data.ecrs && data.ecrs.length > 0">
          <template #header><span>🔄 工程变更 ECR/ECO ({{ data.ecrs.length }})</span></template>
          <el-table :data="data.ecrs" stripe border size="small">
            <el-table-column prop="title" label="标题" min-width="150" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{row}"><el-tag size="small">{{ row.status }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建日期" width="100" />
          </el-table>
        </el-card>

        <!-- 统计信息 -->
        <el-card shadow="never" class="section-card">
          <template #header><span>📊 统计信息</span></template>
          <div class="kpi-row">
            <el-statistic title="总工时" :value="data.total_hours || 0" />
            <el-statistic title="工时记录" :value="data.time_entries_count || 0" />
            <el-statistic title="任务评论" :value="data.comments_count || 0" />
          </div>
        </el-card>

        <el-empty v-if="!data.product && (!data.certifications || data.certifications.length === 0) && (!data.ecrs || data.ecrs.length === 0) && (!data.boms || data.boms.length === 0)" description="暂无跨模块关联数据" />
      </template>
    </el-skeleton>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const props = defineProps<{ pid: number }>()
const loading = ref(true)
const data = ref<any>({})

async function fetchData() {
  loading.value = true
  try {
    const r = await api.get(`/projects/${props.pid}/cross-module`)
    data.value = r.data || {}
  } catch (e: unknown) {
    ElMessage.error('加载跨模块数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.cross-module-tab { padding: 4px 0; }
.section-card { margin-bottom: 12px; }
.info-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.info-item { display: flex; flex-direction: column; gap: 4px; }
.info-item .label { font-size: 12px; color: #909399; }
.kpi-row { display: flex; gap: 32px; flex-wrap: wrap; }
</style>
