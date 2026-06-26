<template>
  <div class="event-timeline-detail">
    <!-- ═══════ 顶部：返回 + Plan 信息 ═══════ -->
    <div class="etd-header">
      <el-button text @click="$router.push('/event-timeline')">← 返回时间线</el-button>
      <div class="etd-plan-info" v-if="plan">
        <h2>📋 {{ plan.name }}</h2>
        <div class="etd-plan-meta">
          <el-tag size="small" :type="plan.status === 'approved' ? 'success' : 'warning'">
            {{ plan.status || '—' }}
          </el-tag>
          <span class="etd-plan-id">ID: {{ planId }}</span>
        </div>
      </div>
      <div class="etd-header-actions">
        <el-button
          type="warning"
          size="small"
          :loading="replaying"
          @click="handleReplay"
        >
          ⏪ 执行重放
        </el-button>
      </div>
    </div>

    <!-- ═══════ 重放结果提示 ═══════ -->
    <el-alert
      v-if="replayResult"
      :title="replayResult.success ? '✅ 重放成功' : '❌ 重放失败'"
      :type="replayResult.success ? 'success' : 'error'"
      show-icon
      :closable="false"
      style="margin-bottom:16px"
    >
      <template #default>
        <pre class="replay-json">{{ JSON.stringify(replayResult, null, 2) }}</pre>
      </template>
    </el-alert>

    <!-- ═══════ 加载态 ═══════ -->
    <div v-loading="loading" element-loading-text="加载事件详情...">
      <el-empty v-if="!loading && events.length === 0" description="暂无事件数据" :image-size="60" />

      <!-- ═══════ 时间线（展开） ═══════ -->
      <el-timeline v-else>
        <el-timeline-item
          v-for="evt in events"
          :key="evt.id"
          :timestamp="formatTime(evt.created_at)"
          placement="top"
          :color="timelineColor(evt.event_type)"
        >
          <el-card shadow="never" class="event-detail-card">
            <!-- 头部 -->
            <div class="edc-header">
              <el-tag :type="eventTagType(evt.event_type)" size="small" effect="dark">
                {{ evt.event_type }}
              </el-tag>
              <span class="edc-source" v-if="evt.source">来源: {{ evt.source }}</span>
            </div>

            <!-- Payload 详情 -->
            <div class="edc-section" v-if="evt.payload">
              <div class="edc-section-title">📦 Payload</div>
              <pre class="edc-json">{{ JSON.stringify(evt.payload, null, 2) }}</pre>
            </div>

            <!-- State Snapshot Diff (before / after) -->
            <div class="edc-section" v-if="evt.state_snapshot">
              <div class="edc-section-title">📸 State Snapshot</div>

              <!-- before & after 并列 -->
              <el-row :gutter="12" v-if="evt.state_snapshot.before || evt.state_snapshot.after">
                <el-col :span="12" v-if="evt.state_snapshot.before">
                  <div class="snapshot-block">
                    <div class="snapshot-label before-label">BEFORE</div>
                    <pre class="snapshot-json">{{ JSON.stringify(evt.state_snapshot.before, null, 2) }}</pre>
                  </div>
                </el-col>
                <el-col :span="12" v-if="evt.state_snapshot.after">
                  <div class="snapshot-block">
                    <div class="snapshot-label after-label">AFTER</div>
                    <pre class="snapshot-json">{{ JSON.stringify(evt.state_snapshot.after, null, 2) }}</pre>
                  </div>
                </el-col>
              </el-row>

              <!-- 无 diff 时显示原始 -->
              <pre v-else class="edc-json">{{ JSON.stringify(evt.state_snapshot, null, 2) }}</pre>
            </div>

            <!-- 无 payload & snapshot -->
            <el-empty
              v-if="!evt.payload && !evt.state_snapshot"
              description="无详细数据"
              :image-size="30"
            />
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../../api'

const route = useRoute()
const planId = route.params.planId as string

// ── Data ──
const plan = ref<any>(null)
const events = ref<any[]>([])
const loading = ref(true)
const replaying = ref(false)
const replayResult = ref<any>(null)

// ── Helpers ──
function formatTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function eventTagType(type: string): string {
  const map: Record<string, string> = {
    created: 'success',
    updated: 'primary',
    deleted: 'danger',
    submitted: 'warning',
    approved: 'success',
    rejected: 'danger',
    reverted: 'info',
  }
  return map[type] || 'info'
}

function timelineColor(type: string): string {
  const map: Record<string, string> = {
    created: '#67C23A',
    updated: '#409EFF',
    deleted: '#F56C6C',
    submitted: '#E6A23C',
    approved: '#67C23A',
    rejected: '#F56C6C',
  }
  return map[type] || '#909399'
}

// ── API: 获取 Plan 信息 ──
async function fetchPlan() {
  try {
    const res = await api.get(`/product-plans/${planId}`)
    plan.value = res.data
  } catch {
    plan.value = null
  }
}

// ── API: 获取事件详情（含 snapshot diff） ──
async function fetchDetail() {
  loading.value = true
  try {
    const res = await api.get(`/api/v2/events/timeline/${planId}/detail`)
    const data = res.data
    events.value = data?.items || data?.data || data?.records || []
  } catch {
    events.value = []
  } finally {
    loading.value = false
  }
}

// ── API: 执行重放 ──
async function handleReplay() {
  replaying.value = true
  replayResult.value = null
  try {
    const res = await api.post(`/api/v2/events/replay/${planId}`)
    replayResult.value = res.data
    ElMessage.success('重放执行完成')
  } catch (e: unknown) {
    const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : null
    replayResult.value = { success: false, error: _err || '重放请求失败' }
    ElMessage.error('重放执行失败')
  } finally {
    replaying.value = false
  }
}

// ── Lifecycle ──
onMounted(async () => {
  await Promise.all([fetchPlan(), fetchDetail()])
})
</script>

<style scoped>
.event-timeline-detail {
  padding: 0 4px;
}
.etd-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.etd-plan-info {
  flex: 1;
}
.etd-plan-info h2 {
  margin: 0 0 4px;
  font-size: 18px;
}
.etd-plan-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #909399;
}
.etd-header-actions {
  flex-shrink: 0;
}

/* 事件卡片 */
.event-detail-card {
  border-radius: 6px;
  margin-bottom: 4px;
}
.edc-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.edc-source {
  font-size: 12px;
  color: #909399;
}
.edc-section {
  margin-top: 10px;
}
.edc-section-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
  color: #303133;
}
.edc-json {
  background: #f5f7fa;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
  max-height: 200px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

/* Snapshot diff */
.snapshot-block {
  border-radius: 6px;
  overflow: hidden;
}
.snapshot-label {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  color: #fff;
}
.before-label {
  background: #E6A23C;
}
.after-label {
  background: #67C23A;
}
.snapshot-json {
  background: #f5f7fa;
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.5;
  max-height: 220px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

/* 重放结果 */
.replay-json {
  background: rgba(255,255,255,0.6);
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 12px;
  max-height: 300px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 8px 0 0;
}
</style>
