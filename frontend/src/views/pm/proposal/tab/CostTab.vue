<template>
  <div class="cost-tab">
    <CostPrototypeSection :data="data" @update="handleSectionUpdate" />
    <CostTestSection :data="data" @update="handleSectionUpdate" />
    <CostLaborSection :data="data" @update="handleSectionUpdate" />
    <CostSummarySection :data="data" @update="handleSectionUpdate" />
  </div>
</template>

<script setup lang="ts">
import CostPrototypeSection from './CostPrototypeSection.vue'
import CostTestSection from './CostTestSection.vue'
import CostLaborSection from './CostLaborSection.vue'
import CostSummarySection from './CostSummarySection.vue'

const props = defineProps({
  data: { type: Object, required: true },
})
const emit = defineEmits<{ update: [patch: Record<string, unknown>] }>()

function handleSectionUpdate(patch: Record<string, unknown>) {
  emit('update', patch)
}
</script>

<style scoped>
.cost-tab {
  padding: 4px 0;
}
</style>
