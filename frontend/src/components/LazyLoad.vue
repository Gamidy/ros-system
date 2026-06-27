<template>
  <div ref="elRef">
    <slot v-if="!enabled || isVisible" />
    <div v-else class="lazy-placeholder" :style="{ height: placeholderHeight + 'px' }" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

withDefaults(defineProps<{
  /** Enable lazy loading — disabled on desktop for instant render */
  enabled?: boolean
  /** Placeholder height in px while content is not yet visible */
  placeholderHeight?: number
}>(), {
  enabled: true,
  placeholderHeight: 200,
})

const elRef = ref<HTMLElement | null>(null)
const isVisible = ref(false)
let observer: IntersectionObserver | null = null

onMounted(() => {
  if (!elRef.value) return
  observer = new IntersectionObserver(
    ([entry]) => {
      if (entry.isIntersecting) {
        isVisible.value = true
        observer?.disconnect()
        observer = null
      }
    },
    { rootMargin: '100px', threshold: 0 },
  )
  observer.observe(elRef.value)
})

onUnmounted(() => {
  observer?.disconnect()
  observer = null
})
</script>

<style scoped>
.lazy-placeholder {
  width: 100%;
  background: var(--c-bg-hover, #f5f5f7);
  border-radius: var(--c-radius-md, 8px);
}
</style>
