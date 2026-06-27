<template>
  <div class="page">
    <el-card shadow="never">
      <el-tabs v-model="activeTab" @tab-change="onTabChange" type="border-card">
        <el-tab-pane label="📋 总览" name="overview" />
        <el-tab-pane label="需求" name="requirements" />
        <el-tab-pane label="项目" name="projects" />
        <el-tab-pane label="样机" name="samples" />
        <el-tab-pane label="执行" name="executions" />
        <el-tab-pane label="结果" name="results" />
        <el-tab-pane label="证书" name="certificates" />
        <el-tab-pane label="门禁规则" name="gate-rules" />
        <el-tab-pane label="影响分析" name="impact" />
        <el-tab-pane label="影响链" name="cert-impact" />
        <el-tab-pane label="影响规则" name="rules" />
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
  overview: defineAsyncComponent(() => import('../../views/certifications/CertificationsView.vue')),
  requirements: defineAsyncComponent(() => import('../../views/s2/S2RequirementView.vue')),
  projects: defineAsyncComponent(() => import('../../views/s2/S2CertProjectView.vue')),
  samples: defineAsyncComponent(() => import('../../views/s2/S2CertSampleView.vue')),
  executions: defineAsyncComponent(() => import('../../views/s2/S2CertExecutionView.vue')),
  results: defineAsyncComponent(() => import('../../views/s2/S2CertResultView.vue')),
  certificates: defineAsyncComponent(() => import('../../views/s2/S2CertificateView.vue')),
  'gate-rules': defineAsyncComponent(() => import('../../views/s2/S2GateRulesView.vue')),
  impact: defineAsyncComponent(() => import('../../views/s2/S2ImpactView.vue')),
  'cert-impact': defineAsyncComponent(() => import('../../views/cert/CertImpactView.vue')),
  rules: defineAsyncComponent(() => import('../../views/cert/CertRulesView.vue')),
}

const activeTab = ref('overview')
const currentComp = shallowRef(markRaw(components[activeTab.value]))

function onTabChange(name: string) {
  currentComp.value = markRaw(components[name])
}
</script>

<style scoped>
.page { padding: 0; }
</style>
