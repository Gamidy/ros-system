/** 知识库 API 对接 */

import api from './index'

// ── 类型定义 ──────────────────────────────────────────────────────────

export interface KnowledgeItem {
  id: number
  category: string
  code: string
  name: string
  content: string | null
  content_type: string | null
  tags: string | null
  version: number | null
  status: string | null
  created_by: string | null
  updated_by: string | null
  sort_order: number | null
  remark: string | null
  created_at: string | null
  updated_at: string | null
}

export interface KnowledgeSearchResult {
  total: number
  page: number
  size: number
  items: KnowledgeItem[]
}

export interface KnowledgeCreate {
  category: string
  code: string
  name: string
  content?: string | null
  content_type?: string | null
  tags?: string | null
  sort_order?: number
  remark?: string | null
}

export interface KnowledgeUpdate {
  category?: string
  code?: string
  name?: string
  content?: string | null
  content_type?: string | null
  tags?: string | null
  sort_order?: number
  remark?: string | null
}

export interface CategoryTreeNode {
  id: string
  name: string
  parent_id: string | null
  children: CategoryTreeNode[]
}

// ── 知识库查询类接口 ─────────────────────────────────────────────

/** 分页搜索知识条目 */
export function searchKnowledge(params: {
  q?: string
  category?: string
  page?: number
  size?: number
}): Promise<KnowledgeSearchResult> {
  return api.get('/kb/items/search', { params }).then(r => r.data)
}

/** 获取所有条目（简单筛选，不分页） */
export function listKnowledge(params?: {
  category?: string
  keyword?: string
  status?: string
}): Promise<KnowledgeItem[]> {
  return api.get('/kb/items', { params }).then(r => r.data)
}

/** 获取单条详情 */
export function getKnowledgeItem(id: number): Promise<KnowledgeItem> {
  return api.get(`/kb/items/${id}`).then(r => r.data)
}

/** 获取分类树 */
export function getCategoryTree(): Promise<CategoryTreeNode[]> {
  return api.get('/kb/categories/tree').then(r => r.data)
}

// ── 知识库管理 CRUD ─────────────────────────────────────────────

/** 创建知识条目 */
export function createKnowledgeItem(data: KnowledgeCreate): Promise<KnowledgeItem> {
  return api.post('/kb/items', data).then(r => r.data)
}

/** 更新知识条目 */
export function updateKnowledgeItem(id: number, data: KnowledgeUpdate): Promise<KnowledgeItem> {
  return api.put(`/kb/items/${id}`, data).then(r => r.data)
}

/** 删除知识条目 */
export function deleteKnowledgeItem(id: number): Promise<{ ok: boolean; id: number }> {
  return api.delete(`/kb/items/${id}`).then(r => r.data)
}
