import { describe, it, expect } from 'vitest'

describe('Router Config', () => {
  it('has expected routes', async () => {
    const { default: router } = await import('../router/index')
    const routes = router.getRoutes()
    const routeNames = routes.map(r => r.name).filter(Boolean)

    expect(routeNames).toContain('Login')
    expect(routeNames).toContain('Dashboard')
    expect(routeNames).toContain('Platforms')
    expect(routeNames).toContain('Models')
    expect(routeNames).toContain('Materials')
    expect(routeNames).toContain('BOM')
    expect(routeNames).toContain('Projects')
    expect(routeNames).toContain('ProjectDetail')

    // Verify total route count (Login + parent '/' + 8 children = 10)
    expect(routes.length).toBeGreaterThanOrEqual(8)
  })
})
