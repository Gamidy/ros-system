// 实验与测试 API
import api from './index'

// ── 类型 ──
export interface TestCreate {
  name: string
  test_type: string
  product_id?: number
  plan_date?: string
  description?: string
  [key: string]: any
}

export interface TestUpdate {
  name?: string
  test_type?: string
  product_id?: number
  plan_date?: string
  description?: string
  status?: string
  [key: string]: any
}

export interface TestOut {
  id: number
  name: string
  test_type: string
  product_id?: number
  product_name?: string
  plan_date?: string
  actual_date?: string
  description?: string
  status: string
  result?: string
  created_at: string
  updated_at: string
  [key: string]: any
}

// ── 实验/测试 CRUD ──
export function listTests(params?: Record<string, any>) {
  return api.get('/tests', { params })
}

export function getTest(id: number) {
  return api.get(`/tests/${id}`)
}

export function createTest(data: TestCreate) {
  return api.post('/tests', data)
}

export function updateTest(id: number, data: TestUpdate) {
  return api.patch(`/tests/${id}`, data)
}

export function deleteTest(id: number) {
  return api.delete(`/tests/${id}`)
}

// ── 验证需求 ──
export function listVerificationRequirements(params?: Record<string, any>) {
  return api.get('/tests/verification-requirements', { params })
}

export function createVerificationRequirement(data: Record<string, any>) {
  return api.post('/tests/verification-requirements', data)
}

// ── Gate规则 ──
export function listGateRules(params?: Record<string, any>) {
  return api.get('/tests/gate-rules', { params })
}

export function createGateRule(data: Record<string, any>) {
  return api.post('/tests/gate-rules', data)
}
