import * as echarts from 'echarts'
import type { EChartsType, EChartsOption } from 'echarts'

/** ECharts 实例扩展类型（带 ResizeObserver） */
type EChartsWithObserver = EChartsType & { __resizeObserver?: ResizeObserver }

const chartInstances = new Map<HTMLElement, EChartsType>()

/**
 * 初始化 ECharts 实例并缓存
 */
export function initChart(el: HTMLElement, option: EChartsOption): EChartsType | null {
  if (!el) return null

  // 销毁已存在的实例
  disposeChart(el)

  const instance = echarts.init(el, undefined, { renderer: 'canvas' })
  instance.setOption(option)
  chartInstances.set(el, instance)

  // 响应式
  const resizeObserver = new ResizeObserver(() => {
    instance.resize()
  })
  resizeObserver.observe(el)

  // 存储 observer 以便销毁
  ;(instance as EChartsWithObserver).__resizeObserver = resizeObserver

  return instance
}

/**
 * 销毁指定元素的 ECharts 实例
 */
export function disposeChart(el: HTMLElement) {
  const instance = chartInstances.get(el)
  if (instance) {
    const observer = (instance as EChartsWithObserver).__resizeObserver
    if (observer) observer.disconnect()
    instance.dispose()
    chartInstances.delete(el)
  }
}

/**
 * 更新图表数据
 */
export function updateChart(el: HTMLElement, option: EChartsOption) {
  const instance = chartInstances.get(el)
  if (instance) {
    instance.setOption(option, true)
  }
}

/**
 * 获取 ECharts 通用 tooltip 样式（Glassmorphism）
 */
export function getGlassTooltip(): EChartsOption['tooltip'] {
  return {
    backgroundColor: 'rgba(255, 255, 255, 0.85)',
    borderColor: 'rgba(255, 255, 255, 0.3)',
    borderWidth: 1,
    textStyle: {
      color: '#1d1d1f',
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro", sans-serif',
    },
    extraCssText: 'backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.08);',
  }
}

/**
 * 获取通用图表颜色（Apple 低饱和色板）
 */
export function getChartColors(): string[] {
  return [
    '#007AFF',
    '#34C759',
    '#FF9500',
    '#AF52DE',
    '#5AC8FA',
    '#FF3B30',
    '#FFCC00',
    '#8E8E93',
  ]
}

/**
 * 通用图表字体
 */
export function getChartFont(): string {
  return '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", sans-serif'
}

export { echarts }
export type { EChartsType, EChartsOption }
