import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock localStorage for jsdom
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value }),
    removeItem: vi.fn((key: string) => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
  }
})()

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock })

describe('Auth Store', () => {
  beforeEach(() => {
    localStorageMock.clear()
    setActivePinia(createPinia())
  })

  it('initial state has no token', async () => {
    const { useAuthStore } = await import('../stores/auth')
    const store = useAuthStore()
    expect(store.token).toBe('')
  })

  it('sets and reads token', async () => {
    const { useAuthStore } = await import('../stores/auth')
    const store = useAuthStore()
    store.token = 'test-token-123'
    expect(store.token).toBe('test-token-123')
  })

  it('logout clears state', async () => {
    const { useAuthStore } = await import('../stores/auth')
    const store = useAuthStore()
    store.token = 'test-token'
    store.user = { username: 'test' }
    store.logout()
    expect(store.token).toBe('')
    expect(store.user).toBeNull()
  })
})
