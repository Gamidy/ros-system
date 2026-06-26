/**
 * Responsive layout composable
 * Listens to window.resize + matchMedia queries
 * Returns isMobile / isTablet / isDesktop / breakpoint / screenSize
 * and a responsiveClass string for easy :class binding.
 *
 * Breakpoints:
 *   mobile  < 768px
 *   tablet  >= 768px && < 1024px
 *   desktop >= 1024px
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'

export type Breakpoint = 'mobile' | 'tablet' | 'desktop'

export function useResponsive() {
  const windowWidth = ref(window.innerWidth)
  const isMobile = ref(windowWidth.value < 768)
  const isTablet = ref(windowWidth.value >= 768 && windowWidth.value < 1024)
  const isDesktop = ref(windowWidth.value >= 1024)
  const breakpoint = ref<Breakpoint>(
    windowWidth.value < 768 ? 'mobile' : windowWidth.value < 1024 ? 'tablet' : 'desktop',
  )

  /** Human-readable size category for data attributes / logging */
  const screenSize = ref<string>(
    windowWidth.value < 768 ? 'mobile' : windowWidth.value < 1024 ? 'tablet' : 'desktop',
  )

  /** Convenience: true when viewport is not desktop */
  const isMobileOrTablet = computed(() => isMobile.value || isTablet.value)

  /**
   * CSS class string for responsive visibility.
   * Usage:  :class="responsiveClass"
   * Adds 'is-mobile' / 'is-tablet' / 'is-desktop' on the host element.
   */
  const responsiveClass = computed(() => {
    const parts: string[] = []
    if (isMobile.value) parts.push('is-mobile')
    if (isTablet.value) parts.push('is-tablet')
    if (isDesktop.value) parts.push('is-desktop')
    if (isMobile.value || isTablet.value) parts.push('is-mobile-or-tablet')
    parts.push(`bp-${breakpoint.value}`)
    return parts.join(' ')
  })

  let mqMobile: MediaQueryList | null = null
  let mqTablet: MediaQueryList | null = null

  function update() {
    const w = window.innerWidth
    windowWidth.value = w
    isMobile.value = w < 768
    isTablet.value = w >= 768 && w < 1024
    isDesktop.value = w >= 1024
    screenSize.value = w < 768 ? 'mobile' : w < 1024 ? 'tablet' : 'desktop'
    if (w < 768) breakpoint.value = 'mobile'
    else if (w < 1024) breakpoint.value = 'tablet'
    else breakpoint.value = 'desktop'
  }

  onMounted(() => {
    update()
    window.addEventListener('resize', update)

    // Also listen to matchMedia for cross-tab / orientation changes
    mqMobile = window.matchMedia('(max-width: 767px)')
    mqTablet = window.matchMedia('(min-width: 768px) and (max-width: 1023px)')

    try {
      mqMobile.addEventListener('change', update)
      mqTablet.addEventListener('change', update)
    } catch {
      // Safari < 14 fallback
      mqMobile.addListener(update)
      mqTablet.addListener(update)
    }
  })

  onUnmounted(() => {
    window.removeEventListener('resize', update)
    if (mqMobile) {
      try {
        mqMobile.removeEventListener('change', update)
      } catch {
        mqMobile.removeListener(update)
      }
    }
    if (mqTablet) {
      try {
        mqTablet.removeEventListener('change', update)
      } catch {
        mqTablet.removeListener(update)
      }
    }
  })

  return {
    isMobile,
    isTablet,
    isDesktop,
    breakpoint,
    windowWidth,
    screenSize,
    isMobileOrTablet,
    responsiveClass,
  }
}
