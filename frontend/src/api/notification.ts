/**
 * 通知中心 API 类型与调用
 */
import api from './index'

// ── 类型定义 ──────────────────────────────────────────────────────────

export interface NotificationItem {
  id: number
  alert_id: number | null
  target_user: string
  channel: string
  title: string
  content: string
  is_sent: boolean
  is_read: boolean
  sent_at: string | null
  read_at: string | null
  created_at: string
  cross_channel_read: Record<string, string | null> | null
}

export interface NotificationPage {
  items: NotificationItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface NotificationQuery {
  target_user?: string
  is_read?: boolean | null
  channel?: string
  keyword?: string
  date_from?: string | null
  date_to?: string | null
  page?: number
  page_size?: number
}

export interface BatchDeleteResponse {
  ok: boolean
  deleted_count: number
}

export interface ReadAllResponse {
  ok: boolean
  updated_count: number
}

// ── 渠道类型常量（与后端对齐） ────────────────────────────────────────

export const CHANNEL_TYPES: string[] = ['wecom', 'dingtalk', 'email', 'websocket']

export const CHANNEL_LABELS: Record<string, string> = {
  wecom: '企业微信',
  dingtalk: '钉钉',
  email: '邮件',
  websocket: '站内通知',
}

export const EVENT_TYPES: string[] = [
  'approval_request',
  'plan_submitted',
  'review_due',
  'alert',
]

export const EVENT_TYPE_LABELS: Record<string, string> = {
  approval_request: '审批请求',
  plan_submitted: '策划提交',
  review_due: '评审到期',
  alert: '系统预警',
}

// ── API 调用 ──────────────────────────────────────────────────────────

/** 获取通知列表（分页） */
export async function fetchNotifications(
  params: NotificationQuery,
): Promise<NotificationPage> {
  const res = await api.get('/notifications', { params })
  return res.data as NotificationPage
}

/** 标记单条通知已读 */
export async function markNotificationRead(nid: number): Promise<void> {
  await api.patch(`/notifications/${nid}/read`)
}

/** 全部标记已读 */
export async function markAllNotificationsRead(): Promise<ReadAllResponse> {
  const res = await api.post('/notifications/read-all')
  return res.data as ReadAllResponse
}

/** 批量删除通知 */
export async function deleteNotificationsBatch(
  ids: number[],
): Promise<BatchDeleteResponse> {
  const res = await api.delete('/notifications/batch', { data: { ids } })
  return res.data as BatchDeleteResponse
}
