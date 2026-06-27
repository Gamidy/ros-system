/** 通用表格行类型 — 用于无法确定具体类型的 el-table row 参数 */
export interface TableRow {
  id?: number | string
  [key: string]: unknown
}

/** 通用图表数据点 — 用于 ECharts 回调 */
export interface ChartDataPoint {
  name?: string
  value?: number
  score?: number
  count?: number
  date?: string
  day?: string
  [key: string]: unknown
}

/** 用于 JSON.parse 后未确定结构的数组元素 */
export type JsonRow = Record<string, unknown>
