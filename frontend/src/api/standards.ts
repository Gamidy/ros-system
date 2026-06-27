/** 标准知识库 API 对接 */

import api from './index'

// ── 类型定义 ──────────────────────────────────────────────────────────

export interface StandardItem {
  id: number
  region_id: number
  category_id: number | null
  std_number: string
  title: string
  title_en: string | null
  version: string | null
  amendment: string | null
  status: string
  effective_date: string | null
  repeal_date: string | null
  source_url: string | null
  impact_level: string | null
  impact_scope: string | null
  region_name: string
  region_code: string
  category_name: string | null
  created_at: string | null
  updated_at: string | null
}

export interface StandardPage {
  items: StandardItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface StandardQuery {
  region?: string
  category?: string
  status?: string
  impact?: string
  search?: string
  date_from?: string | null
  date_to?: string | null
  page?: number
  page_size?: number
}

export interface RegionItem {
  id: number
  code: string
  name: string
  name_en: string | null
  base_url?: string | null
  scan_method?: string
  is_active?: boolean
  sort_order?: number
}

export interface CategoryItem {
  id: number
  code: string
  name: string
}

export interface RecentStats {
  total_active: number
  new_last_7d: number
  new_last_30d: number
  upcoming_effective: number
  by_region: { code: string; name: string; count: number }[]
}

export interface CrawlLogItem {
  id: number
  region_id: number
  region_name: string
  started_at: string
  finished_at: string | null
  status: string
  total_fetched: number
  new_added: number
  updated: number
  skipped: number
  error_message: string | null
  created_at: string
}

export interface CrawlLogPage {
  items: CrawlLogItem[]
  total: number
  page: number
  page_size: number
}

export interface StandardCreate {
  region_id: number
  category_id?: number | null
  std_number: string
  title: string
  title_en?: string | null
  version?: string | null
  amendment?: string | null
  status?: string
  effective_date?: string | null
  repeal_date?: string | null
  source_url?: string | null
  impact_level?: string | null
  impact_scope?: string | null
}

export interface StandardUpdate {
  category_id?: number | null
  title?: string
  title_en?: string | null
  version?: string | null
  amendment?: string | null
  status?: string
  effective_date?: string | null
  repeal_date?: string | null
  source_url?: string | null
  impact_level?: string | null
  impact_scope?: string | null
}

// ── PM 查询接口 ────────────────────────────────────────────────────────

/** 标准列表查询（多条件筛选 + 全文搜索 + 分页） */
export function listStandards(params: StandardQuery): Promise<StandardPage> {
  return api.get('/standards', { params }).then(r => r.data)
}

/** 标准详情 */
export function getStandard(id: number): Promise<StandardItem> {
  return api.get(`/standards/${id}`).then(r => r.data)
}

/** 最近 N 天新增/更新的标准 */
export function getRecentStandards(days = 7): Promise<{ items: StandardItem[]; days: number }> {
  return api.get('/standards/recent', { params: { days } }).then(r => r.data)
}

/** 标准库概览统计 */
export function getStandardStats(): Promise<RecentStats> {
  return api.get('/standards/stats').then(r => r.data)
}

/** 地区列表 */
export function listRegions(): Promise<RegionItem[]> {
  return api.get('/standards/regions').then(r => r.data)
}

/** 分类列表 */
export function listCategories(): Promise<CategoryItem[]> {
  return api.get('/standards/categories').then(r => r.data)
}

// ── 管理员 CRUD ──────────────────────────────────────────────────────

/** 地区配置列表（管理员） */
export function listAdminRegions(): Promise<RegionItem[]> {
  return api.get('/admin/standards/regions').then(r => r.data)
}

/** 新增地区 */
export function createRegion(data: Partial<RegionItem>): Promise<{ ok: boolean; id: number }> {
  return api.post('/admin/standards/regions', data).then(r => r.data)
}

/** 更新地区 */
export function updateRegion(id: number, data: Partial<RegionItem>): Promise<{ ok: boolean }> {
  return api.put(`/admin/standards/regions/${id}`, data).then(r => r.data)
}

/** 手动录入标准 */
export function createStandard(data: StandardCreate): Promise<{ ok: boolean; id: number }> {
  return api.post('/admin/standards', data).then(r => r.data)
}

/** 编辑标准条目 */
export function updateStandard(id: number, data: StandardUpdate): Promise<{ ok: boolean }> {
  return api.put(`/admin/standards/${id}`, data).then(r => r.data)
}

/** 删除标准（软删除） */
export function deleteStandard(id: number): Promise<{ ok: boolean }> {
  return api.delete(`/admin/standards/${id}`).then(r => r.data)
}

/** 手动触发爬取 */
export function triggerCrawl(region_id?: number): Promise<{ ok: boolean; crawl_ids: number[] }> {
  return api.post('/admin/standards/trigger-crawl', null, { params: { region_id } }).then(r => r.data)
}

/** 爬取日志列表 */
export function listCrawlLogs(params: {
  region_id?: number
  status?: string
  page?: number
  page_size?: number
}): Promise<CrawlLogPage> {
  return api.get('/admin/standards/crawl-logs', { params }).then(r => r.data)
}
