<template>
  <div class="alerts-tab">
    <el-skeleton :loading="loading" animated :count="3">
      <template #default>
        <div v-if="alerts.length === 0 && !loading" class="empty-state">
          <el-empty description="暂无提醒 — 所有任务/风险状态正常" />
        </div>

        <div v-for="(group, sev) in groupedAlerts" :key="sev" class="alert-group">
          <div class="group-title">{{ sevLabel(sev) }} ({{ group.length }})</div>
          <div v-for="a in group" :key="a.type + a.title" class="alert-item">
            <el-card shadow="hover">
              <div class="alert-content">
                <el-tag :type="sevTag(a.severity)" size="small" class="alert-type-tag">{{ sevLabel(a.severity) }}</el-tag>
                <div class="alert-body">
                  <div class="alert-title">{{ a.title }}</div>
                  <div class="alert-detail">{{ a.detail }}</div>
                </div>
                <span class="alert-date" v-if="a.date">{{ a.date }}</span>
              </div>
            </el-card>
          </div>
        </div>
      </template>
    </el-skeleton>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const props = defineProps<{ pid: number }>()
const loading = ref(false)
const alerts = ref<any[]>([])

const groupedAlerts = computed(() => {
  const groups: Record<string, any[]> = { critical: [], high: [], medium: [], low: [] }
  for (const a of alerts.value) {
    if (!groups[a.severity]) groups[a.severity] = []
    groups[a.severity].push(a)
  }
  return groups
})

function sevTag(s: string) {
  return { critical: 'danger', high: 'warning', medium: 'info', low: 'info' }[s] || 'info'
}
function sevLabel(s: string) {
  return { critical: '🔴 紧急', high: '🟡 严重', medium: '🔵 提醒', low: '⚪ 普通' }[s] || s
}

async function fetchAlerts() {
  loading.value = true
  try {
    const r = await api.get(`/projects/${props.pid}/alerts`)
    alerts.value = r.data || []
  } catch (e: unknown) {
    ElMessage.error('加载提醒失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchAlerts)
</script>

<style scoped>
.alerts-tab { padding: 4px 0; }
.alert-group { margin-bottom: 12px; }
.group-title { font-weight: 600; margin-bottom: 8px; color: #606266; font-size: 14px; }
.alert-item { margin-bottom: 8px; }
.alert-content { display: flex; align-items: flex-start; gap: 12px; }
.alert-type-tag { flex-shrink: 0; margin-top: 2px; }
.alert-body { flex: 1; min-width: 0; }
.alert-title { font-weight: 600; color: #303133; font-size: 14px; }
.alert-detail { color: #909399; font-size: 12px; margin-top: 4px; }
.alert-date { flex-shrink: 0; color: #c0c4cc; font-size: 12px; }
.empty-state { min-height: 200px; display: flex; align-items: center; justify-content: center; }
</style>
