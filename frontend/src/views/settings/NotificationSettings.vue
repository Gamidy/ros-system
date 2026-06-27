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
              <span class="label">Webhook 地址：</span>
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
              <span class="label">Webhook 地址：</span>
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

    <!-- ═══════════════ 免打扰配置卡片 ═══════════════ -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span>🌙 免打扰时段</span>
          <el-switch v-model="dnd.enabled" />
        </div>
      </template>
      <el-form label-width="120px" label-position="left" size="small">
        <el-form-item label="开始时间">
          <el-time-picker
            v-model="dnd.startTime"
            placeholder="选择开始时间"
            format="HH:mm"
            value-format="HH:mm"
            style="width: 140px"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-time-picker
            v-model="dnd.endTime"
            placeholder="选择结束时间"
            format="HH:mm"
            value-format="HH:mm"
            style="width: 140px"
          />
        </el-form-item>
        <el-form-item label="最低推送优先级">
          <el-select v-model="dnd.minPriority" style="width: 260px">
            <el-option :value="0" label="不屏蔽（推送全部通知）" />
            <el-option :value="1" label="仅重要（屏蔽普通通知）" />
            <el-option :value="2" label="仅紧急（仅推送紧急通知）" />
          </el-select>
        </el-form-item>
        <el-form-item label=" ">
          <el-button
            type="primary"
            size="small"
            :loading="dndSaving"
            @click="saveDnd"
          >
            保存免打扰设置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- ═══════════════ 通知偏好矩阵 ═══════════════ -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span>📋 通知偏好设置</span>
          <el-button
            size="small"
            type="primary"
            :loading="prefSaving"
            @click="savePrefs"
          >
            保存偏好
          </el-button>
        </div>
      </template>
      <el-table
        :data="prefMatrix"
        border
        size="small"
        style="width: 100%"
        max-height="480"
      >
        <el-table-column label="事件类型" width="140" prop="eventLabel">
          <template #default="{ row }">
            <strong>{{ row.eventLabel }}</strong>
          </template>
        </el-table-column>
        <el-table-column
          v-for="ct in channelTypeList"
          :key="ct.key"
          :label="ct.label"
          :width="ct.width"
          align="center"
        >
          <template #default="{ row }">
            <el-checkbox
              v-model="row.channels[ct.key]"
              size="small"
            />
          </template>
        </el-table-column>
      </el-table>
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

interface PrefRecord {
  id: number
  user_id: number
  event_type: string
  channel_type: string
  enabled: boolean
}

/** 矩阵行 — 某个事件类型在各渠道的开关 */
interface PrefMatrixRow {
  eventType: string
  eventLabel: string
  channels: Record<string, boolean>
}

interface ChannelTypeOption {
  key: string
  label: string
  width: number
}

/** 免打扰配置 */
interface DoNotDisturbConfig {
  enabled: boolean
  startTime: string   // HH:MM
  endTime: string     // HH:MM
  timezone: string
  minPriority: number // 0=不屏蔽, 1=仅重要, 2=仅紧急
}

/* ── 常量 ── */
const EVENT_TYPE_LABELS: Record<string, string> = {
  approval_request: '审批请求',
  plan_submitted: '策划提交',
  review_due: '评审到期',
  alert: '系统预警',
}

const channelTypeList: ChannelTypeOption[] = [
  { key: 'wecom', label: '企业微信', width: 100 },
  { key: 'dingtalk', label: '钉钉', width: 80 },
  { key: 'email', label: '邮件', width: 80 },
  { key: 'websocket', label: '站内通知', width: 100 },
]

/* ── 状态 ── */
const channels = reactive<Channels>({
  wecom: { enabled: false, configured: false, webhook_url: '' },
  dingtalk: { enabled: false, configured: false, webhook_url: '' },
})

const historyList = ref<HistoryRecord[]>([])
const historyLoading = ref(false)
const testingChannel = ref<string | null>(null)

/** 通知偏好矩阵 */
const prefMatrix = ref<PrefMatrixRow[]>([])
const prefSaving = ref(false)

/** 免打扰配置 */
const dnd = reactive<DoNotDisturbConfig>({
  enabled: false,
  startTime: '22:00',
  endTime: '08:00',
  timezone: 'Asia/Shanghai',
  minPriority: 1,
})
const dndSaving = ref(false)

/* ── API ── */

/** 获取通知偏好配置 */
async function fetchPrefs() {
  try {
    const res = await api.get('/user/notification-prefs')
    const data = res.data

    // 兼容旧版 — 旧结构仍有数据时处理
    if (!Array.isArray(data)) {
      const d = data as Record<string, unknown>
      channels.wecom.enabled = (d.wecom_enabled as boolean) ?? false
      channels.wecom.configured = (d.wecom_configured as boolean) ?? false
      channels.wecom.webhook_url = (d.wecom_webhook_url as string) ?? ''
      channels.dingtalk.enabled = (d.dingtalk_enabled as boolean) ?? false
      channels.dingtalk.configured = (d.dingtalk_configured as boolean) ?? false
      channels.dingtalk.webhook_url = (d.dingtalk_webhook_url as string) ?? ''
      if (d.history) {
        historyList.value = d.history as HistoryRecord[]
      }
      return
    }

    // 新结构：数组形式 —
    // 构建偏好矩阵
    buildPrefMatrix(data as PrefRecord[])
  } catch {
    ElMessage.error('加载通知配置失败')
  }
}

/** 获取免打扰配置 */
async function fetchDnd() {
  try {
    const res = await api.get('/user/notification-dnd')
    const data = res.data as {
      enabled: boolean
      start_time: string
      end_time: string
      timezone: string
      min_priority: number
    }
    dnd.enabled = data.enabled
    dnd.startTime = data.start_time
    dnd.endTime = data.end_time
    dnd.timezone = data.timezone
    dnd.minPriority = data.min_priority
  } catch {
    // 首次调用失败时静默处理 — 用默认值
  }
}

/** 从 API 返回的 PrefRecord 列表构建矩阵 */
function buildPrefMatrix(records: PrefRecord[]): void {
  const matrixMap: Record<string, PrefMatrixRow> = {}

  // 为每个事件类型初始化一行
  for (const [eventType, eventLabel] of Object.entries(EVENT_TYPE_LABELS)) {
    const channelsMap: Record<string, boolean> = {}
    for (const ct of channelTypeList) {
      channelsMap[ct.key] = true // 默认开启
    }
    matrixMap[eventType] = { eventType, eventLabel, channels: channelsMap }
  }

  // 用实际记录覆盖
  for (const rec of records) {
    const row = matrixMap[rec.event_type]
    if (row) {
      row.channels[rec.channel_type] = rec.enabled
    }
  }

  prefMatrix.value = Object.values(matrixMap)
}

/** 保存渠道开关 — 切换某渠道在所有事件类型下的启用状态 */
async function saveChannel(channel: string) {
  try {
    const enabled = channel === 'wecom' ? channels.wecom.enabled : channels.dingtalk.enabled
    const prefs: { event_type: string; channel_type: string; enabled: boolean }[] = []
    for (const et of Object.keys(EVENT_TYPE_LABELS)) {
      prefs.push({ event_type: et, channel_type: channel, enabled })
    }
    await api.put('/user/notification-prefs', { prefs })
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

/** 保存通知偏好矩阵 */
async function savePrefs() {
  prefSaving.value = true
  try {
    const prefs: { event_type: string; channel_type: string; enabled: boolean }[] = []
    for (const row of prefMatrix.value) {
      for (const ct of channelTypeList) {
        prefs.push({
          event_type: row.eventType,
          channel_type: ct.key,
          enabled: row.channels[ct.key],
        })
      }
    }
    await api.put('/user/notification-prefs', { prefs })
    ElMessage.success('通知偏好已保存')
  } catch {
    ElMessage.error('保存通知偏好失败')
  } finally {
    prefSaving.value = false
  }
}

/** 保存免打扰配置 */
async function saveDnd() {
  dndSaving.value = true
  try {
    await api.put('/user/notification-dnd', {
      enabled: dnd.enabled,
      start_time: dnd.startTime,
      end_time: dnd.endTime,
      timezone: dnd.timezone,
      min_priority: dnd.minPriority,
    })
    ElMessage.success('免打扰配置已保存')
  } catch {
    ElMessage.error('保存免打扰配置失败')
  } finally {
    dndSaving.value = false
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
  return EVENT_TYPE_LABELS[t] ?? t
}

/* ── 生命周期 ── */
onMounted(() => {
  fetchPrefs()
  fetchDnd()
})
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
