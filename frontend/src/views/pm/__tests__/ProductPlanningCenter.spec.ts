import { describe, it, expect, vi, beforeEach } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import { createPinia } from 'pinia'

// jsdom polyfill: matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false, media: query, onchange: null,
    addListener: vi.fn(), removeListener: vi.fn(),
    addEventListener: vi.fn(), removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  ElMessageBox: { confirm: vi.fn(() => Promise.resolve('confirm')) },
}))

// Mock API
vi.mock('../../../api', () => {
  const mockGet = vi.fn().mockResolvedValue({ data: { items: [], total: 0 } })
  return { default: { get: mockGet, post: vi.fn().mockResolvedValue({ data: {} }), delete: vi.fn().mockResolvedValue({}) } }
})

// Mock child components
vi.mock('../AnnualPlanList.vue', () => ({ default: { name: 'AnnualPlanList', template: '<div class="mock-annual-plan-list" />' } }))
vi.mock('../RoadmapPanel.vue', () => ({ default: { name: 'RoadmapPanel', template: '<div class="mock-roadmap-panel" />' } }))
vi.mock('../StatsCards.vue', () => ({ default: { name: 'StatsCards', template: '<div class="mock-stats-cards" />' } }))
vi.mock('../../../components/GlobalActionCard.vue', () => ({ default: { name: 'GlobalActionCard', template: '<div class="mock-global-action" />' } }))

import ProductPlanningCenter from '../ProductPlanningCenter.vue'
import api from '../../../api'

function createWrapper() {
  const pinia = createPinia()
  return shallowMount(ProductPlanningCenter, {
    global: {
      plugins: [pinia],
      stubs: {
        'el-tabs': { template: '<div class="el-tabs"><slot /></div>', props: ['modelValue'] },
        'el-tab-pane': { template: '<div><slot /></div>', props: ['label', 'name'] },
        'el-row': { template: '<div><slot /></div>' },
        'el-col': { template: '<div><slot /></div>' },
        'el-button': { template: '<button><slot /></button>' },
        'el-table': { template: '<div><slot /></div>' },
        'el-table-column': { template: '<div class="mock-column" />' },
        'el-select': { template: '<div><slot /></div>' },
        'el-option': { template: '<div />' },
        'el-input': { template: '<div><slot /></div>' },
        'el-dialog': { template: '<div v-if="modelValue"><slot /></div>', props: ['modelValue'] },
        'el-tag': { template: '<span><slot /></span>' },
        'el-card': { template: '<div><slot /></div>' },
        'el-pagination': { template: '<div />' },
        'el-steps': { template: '<div><slot /></div>' },
        'el-step': { template: '<div />' },
        'el-form': { template: '<div><slot /></div>' },
        'el-form-item': { template: '<div><slot /></div>' },
        'el-progress': { template: '<div />' },
        'el-alert': { template: '<div><slot /></div>' },
      },
    },
  })
}

describe('ProductPlanningCenter — Workspace Merge', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('组件可正常挂载', () => {
    const wrapper = createWrapper()
    expect(wrapper.exists()).toBe(true)
  })

  it('存在 activeTab 状态变量', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.activeTab).toBeDefined()
  })

  it('默认 activeTab 为 plans', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.activeTab).toBe('plans')
  })

  it('保留 filterStatus 原有状态变量', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.filterStatus).toBeDefined()
  })

  it('存在 fetchStatistics 和 fetchRoadmap 方法', () => {
    const wrapper = createWrapper()
    expect(typeof wrapper.vm.fetchStatistics).toBe('function')
    expect(typeof wrapper.vm.fetchRoadmap).toBe('function')
  })

  it('挂载时调用 GET /product-plans', async () => {
    createWrapper()
    await new Promise(r => setTimeout(r, 100))
    expect(api.get).toHaveBeenCalledWith(
      expect.stringContaining('/product-plans'),
      expect.anything(),
    )
  })
})
