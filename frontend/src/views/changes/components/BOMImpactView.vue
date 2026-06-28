<template>
  <el-card shadow="never" style="margin-bottom: 16px">
    <template #header>
      <div class="card-header">
        <span>变更影响传播 (BOM Impact)</span>
        <el-tag v-if="total > 0" size="small">{{ total }} 条记录</el-tag>
      </div>
    </template>

    <div v-if="loading" style="text-align:center;padding:32px">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
    </div>

    <el-alert
      v-else-if="error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom:8px"
    />

    <el-empty
      v-else-if="!items.length"
      description="暂无变更影响记录（ECO生效后自动分析）"
      :image-size="60"
      style="padding:24px"
    />

    <el-table v-else :data="items" stripe border size="small" style="width:100%">
      <el-table-column label="影响等级" width="120">
        <template #default="{ row }">
          <el-tag :type="levelType(row.impact_level)" size="small" effect="dark">
            {{ levelLabel(row.impact_level) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="changed_part" label="变更内容" min-width="200" show-overflow-tooltip />
      <el-table-column label="匹配规则" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.matched_rule?.name || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="影响认证类型" width="160">
        <template #default="{ row }">
          <el-tag
            v-for="ct in parseCertTypes(row.affected_cert_types)"
            :key="ct"
            size="small"
            style="margin-right:4px;margin-bottom:2px"
          >{{ ct }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="分析时间" width="150">
        <template #default="{ row }">{{ row.created_at?.slice(0,16) }}</template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { fetchImpactRecords } from '@/api/ci_v2'
import type { ImpactRecordItem } from '@/api/ci_v2'

const props = defineProps<{
  ecrId: number | null
}>()

const items = ref<ImpactRecordItem[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

const levelMap: Record<string, string> = {
  critical: '严重',
  major: '较大',
  minor: '轻微',
  none: '无影响',
}
const levelTypeMap: Record<string, string> = {
  critical: 'danger',
  major: 'warning',
  minor: 'info',
  none: 'info',
}

function levelLabel(s: string): string { return levelMap[s] || s }
function levelType(s: string): string { return levelTypeMap[s] || 'info' }

function parseCertTypes(val: string): string[] {
  if (!val) return []
  try {
    const parsed = JSON.parse(val)
    return Array.isArray(parsed) ? parsed : [String(parsed)]
  } catch (e: unknown) {
    return val.split(',').map(s => s.trim()).filter(Boolean)
  }
}

async function loadRecords(): Promise<void> {
  if (!props.ecrId) return
  loading.value = true
  error.value = null
  try {
    const res = await fetchImpactRecords({ ecr_id: props.ecrId, page_size: 50 })
    items.value = res.items
    total.value = res.total
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '获取影响记录失败'
  } finally {
    loading.value = false
  }
}

function refresh(): void {
  loadRecords()
}

onMounted(loadRecords)

defineExpose({ refresh })
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
