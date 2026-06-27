<template>
  <div class="page">
    <el-card shadow="never">
      <el-tabs v-model="activeTab" @tab-change="onTabChange" type="border-card">
        <el-tab-pane label="安全标准库" name="standards" />
        <el-tab-pane label="安规检测项" name="inspection" />
        <el-tab-pane label="供应商安规" name="supplier" />
        <el-tab-pane label="安规预警" name="alerts" />
      </el-tabs>
      <div style="margin-top:16px">
        <keep-alive>
          <component :is="currentComp" :key="activeTab" />
        </keep-alive>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, shallowRef, markRaw, defineAsyncComponent } from 'vue'

// 静态导入映射 — Vite 可静态分析
const components: Record<string, ReturnType<typeof defineAsyncComponent>> = {
  standards: defineAsyncComponent(() => import('../../views/safety/SafetyStandardTab.vue')),
  inspection: defineAsyncComponent(() => import('../../views/safety/SafetyInspectionTab.vue')),
  supplier: defineAsyncComponent(() => import('../../views/safety/SupplierSafetyTab.vue')),
  alerts: defineAsyncComponent(() => import('../../views/safety/SafetyAlertTab.vue')),
}

const activeTab = ref('standards')
const currentComp = shallowRef(markRaw(components[activeTab.value]))

function onTabChange(name: string) {
  currentComp.value = markRaw(components[name])
}
</script>

<style scoped>
.page { padding: 0; }
</style>
