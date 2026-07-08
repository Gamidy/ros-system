<template>
  <div class="safety-mgmt">
    <el-tabs v-model="activeTab" @tab-click="onTabChange">
      <el-tab-pane label="安全标准库" name="standards">
        <SafetyStandardTab ref="standardsRef" />
      </el-tab-pane>
      <el-tab-pane label="安规检测项" name="items">
        <SafetyInspectionTab ref="itemsRef" />
      </el-tab-pane>
      <el-tab-pane label="供应商安规" name="suppliers">
        <SupplierSafetyTab ref="suppliersRef" />
      </el-tab-pane>
      <el-tab-pane label="安规预警" name="alerts">
        <SafetyAlertTab ref="alertsRef" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SafetyStandardTab from './SafetyStandardTab.vue'
import SafetyInspectionTab from './SafetyInspectionTab.vue'
import SupplierSafetyTab from './SupplierSafetyTab.vue'
import SafetyAlertTab from './SafetyAlertTab.vue'

const route = useRoute()
const router = useRouter()
const activeTab = ref<string>('standards')

function onTabChange() {
  router.replace({ query: { ...route.query, tab: activeTab.value } })
}

// 从 URL query 恢复 tab
if (route.query.tab && typeof route.query.tab === 'string') {
  activeTab.value = route.query.tab
}
</script>

<style scoped>
.safety-mgmt {
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  min-height: calc(100vh - 120px);
}
</style>
