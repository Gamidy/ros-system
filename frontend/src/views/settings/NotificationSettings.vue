<template>
  <div class="notification-settings">
    <h2>🔔 通知配置</h2>

    <!-- ═══════════════ 渠道开关卡片 ═══════════════ -->
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="never" class="channel-card">
          <template #header>
            <div class="card-header">
              <span>📱 企业微信</span>
              <el-switch
                v-model="channels.wecom.enabled"
                @change="saveChannel('wecom')"
              />
            </div>
          </template>
          <div class="channel-body">
            <div class="status-row">
              <span class="label">配置状态：</span>
              <el-tag v-if="channels.wecom.configured" type="success" size="small">已配置</el-tag>
              <el-tag v-else type="info" size="small">未配置</el-tag>
            </div>
            <div class="status-row" v-if="channels.wecom.configured">
              <span class="label">Webhook URL：</span>
              <code class="webhook-hint">{{ maskUrl(channels.wecom.webhook_url) }}</code>
            </div>
            <el-button
              size="small"
              type="primary"
              plain
              :loading="testingChannel === 'wecom'"
              :disabled="!channels.wecom.configured"
              @click="testChannel('wecom')"
            >
              测试发送
            </el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="never" class="channel-card">
          <template #header>
            <div class="card-header">
              <span>🐦 钉钉</span>
              <el-switch
                v-model="channels.dingtalk.enabled"
                @change="saveChannel('dingtalk')"
              />
            </div>
          </template>
          <div class="channel-body">
            <div class="status-row">
              <span class="label">配置状态：</span>
              <el-tag v-if="channels.dingtalk.configured" type="success" size="small">已配置</el-tag>
              <el-tag v-else type="info" size="small">未配置</el-tag>
            </div>
            <div class="status-row" v-if="channels.dingtalk.configured">
              <span class="label">Webhook URL：</span>
              <code class="webhook-hint">{{ maskUrl(channels.dingtalk.webhook_url) }}</code>
            </div>
            <el-button
              size="small"
              type="primary"
              plain
              :loading="testingChannel === 'dingtalk'"
              :disabled="!channels.dingtalk.configured"
              @click="testChannel('dingtalk')"
            >
              测试发送
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ═══════════════ 事件订阅 ═══════════════ -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <span>📋 事件订阅</span>
      </template>
      <el-checkbox-group v-model="subscribedEvents" @change="saveEventSubscriptions">
        <el-checkbox value="approval">审批类 — 通知审批人/申请人流转状态</el-checkbox>
        <el-checkbox value="planning">策划推进类 — 产品策划节点变更/里程碑提醒</el-checkbox>
        <el-checkbox value="cost_alert">成本告警类 — 成本超阈值预警</el-checkbox>
      </el-checkbox-group>
    </el-card>

    <!-- ═══════════════ 发送历史 ═══════════════ -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span>📤 发送历史（最近50条）</span>
          <el-button size="small" text @click="refreshHistory">刷新</el-button>
        </div>
      </template>
      <el-table
        :data="historyList"
        border
        size="small"
        style="width: 100%"
        max-height="420"
        v-loading="historyLoading"
      >
        <el-table-column prop="channel" label="渠道" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.channel === 'wecom'" size="small">企微</el-tag>
            <el-tag v-else-if="row.channel === 'dingtalk'" size="small">钉钉</el-tag>
            <span v-else>{{ row.channel }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'"
              size="small"
            >
              {{ row.status === 'success' ? '成功' : row.status === 'failed' ? '失败' : row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="event_type" label="事件类型" width="100">
          <template #default="{ row }">
            {{ eventTypeLabel(row.event_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="summary" label="摘要" min-width="180" show-overflow-tooltip />
        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!historyLoading && historyList.length === 0" class="empty-hint">
        暂无发送记录
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/index'

/* ── 类型定义 ── */
interface ChannelConfig {
  enabled: boolean
  configured: boolean
  webhook_url: string
}

interface Channels {
  wecom: ChannelConfig
  dingtalk: ChannelConfig
}

interface HistoryRecord {
  id: number
  channel: string
  status: string
  event_type: string
  summary: string
  created_at: string
}

/* ── 状态 ── */
const channels = reactive<Channels>({
  wecom: { enabled: false, configured: false, webhook_url: '' },
  dingtalk: { enabled: false, configured: false, webhook_url: '' },
})

const subscribedEvents = ref<string[]>([])
const historyList = ref<HistoryRecord[]>([])
const historyLoading = ref(false)
const testingChannel = ref<string | null>(null)

/* ── API ── */

/** 获取通知偏好配置 */
async function fetchPrefs() {
  try {
    const res = await api.get('/user/notification-prefs')
    const data = res.data
    channels.wecom.enabled = data.wecom_enabled ?? false
    channels.wecom.configured = data.wecom_configured ?? false
    channels.wecom.webhook_url = data.wecom_webhook_url ?? ''
    channels.dingtalk.enabled = data.dingtalk_enabled ?? false
    channels.dingtalk.configured = data.dingtalk_configured ?? false
    channels.dingtalk.webhook_url = data.dingtalk_webhook_url ?? ''
    subscribedEvents.value = data.subscribed_events ?? []
    if (data.history) {
      historyList.value = data.history
    }
  } catch {
    ElMessage.error('加载通知配置失败')
  }
}

/** 保存渠道开关 */
async function saveChannel(channel: string) {
  try {
    const payload: Record<string, boolean> = {}
    if (channel === 'wecom') {
      payload.wecom_enabled = channels.wecom.enabled
    } else {
      payload.dingtalk_enabled = channels.dingtalk.enabled
    }
    await api.put('/user/notification-prefs', payload)
    ElMessage.success(`${channel === 'wecom' ? '企微' : '钉钉'}开关已更新`)
  } catch {
    ElMessage.error('保存失败')
  }
}

/** 测试发送 */
async function testChannel(channel: string) {
  testingChannel.value = channel
  try {
    await api.post('/user/notification-prefs/test', { channel })
    ElMessage.success(`测试消息已发送至${channel === 'wecom' ? '企微' : '钉钉'}`)
  } catch {
    ElMessage.error('测试发送失败，请检查通道配置')
  } finally {
    testingChannel.value = null
  }
}

/** 保存事件订阅 */
async function saveEventSubscriptions(events: string[]) {
  try {
    await api.put('/user/notification-prefs', { subscribed_events: events })
    ElMessage.success('事件订阅已更新')
  } catch {
    ElMessage.error('保存事件订阅失败')
  }
}

/** 刷新历史 */
async function refreshHistory() {
  historyLoading.value = true
  try {
    const res = await api.get('/user/notification-prefs/history', { params: { limit: 50 } })
    historyList.value = res.data ?? []
  } catch {
    ElMessage.error('加载发送历史失败')
  } finally {
    historyLoading.value = false
  }
}

/* ── 工具 ── */

function maskUrl(url: string): string {
  if (!url) return '-'
  if (url.length <= 20) return url
  return url.slice(0, 12) + '****' + url.slice(-8)
}

function formatTime(iso: string): string {
  if (!iso) return '-'
  try {
    const d = new Date(iso)
    const pad = (n: number) => n.toString().padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch {
    return iso
  }
}

function eventTypeLabel(t: string): string {
  const labels: Record<string, string> = {
    approval: '审批类',
    planning: '策划推进',
    cost_alert: '成本告警',
  }
  return labels[t] ?? t
}

/* ── 生命周期 ── */
onMounted(fetchPrefs)
</script>

<style scoped>
.notification-settings {
  padding: 16px;
}

.notification-settings h2 {
  margin: 0 0 16px;
  font-size: 18px;
}

.channel-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.channel-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.status-row .label {
  color: #666;
  white-space: nowrap;
}

.webhook-hint {
  font-size: 12px;
  color: #999;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
}

.section-card {
  margin-top: 16px;
}

.section-card .el-checkbox {
  display: flex;
  margin-bottom: 8px;
}

.section-card .el-checkbox:last-child {
  margin-bottom: 0;
}

.empty-hint {
  text-align: center;
  color: #999;
  font-size: 13px;
  padding: 24px 0;
}
</style>
