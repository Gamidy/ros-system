<template>
  <div class="page">
    <el-card shadow="never">
      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <el-tab-pane label="变更管理" name="changes" />
        <el-tab-pane label="ECR 变更申请" name="ecr" />
        <el-tab-pane label="ECO 变更指令" name="eco" />
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
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

// 静态导入映射 — Vite 可静态分析
const components: Record<string, ReturnType<typeof defineAsyncComponent>> = {
  changes: defineAsyncComponent(() => import('../../views/changes/ChangesView.vue')),
  ecr: defineAsyncComponent(() => import('../../views/changes/ECRListView.vue')),
  eco: defineAsyncComponent(() => import('../../views/changes/ECOListView.vue')),
}

// 从URL初始化tab
const tabFromPath: Record<string, string> = {
  '/changes': 'changes',
  '/ecr': 'ecr',
  '/eco': 'eco',
}
const activeTab = ref(tabFromPath[route.path] || 'changes')

const currentComp = shallowRef(markRaw(components[activeTab.value]))

function onTabChange(name: string) {
  currentComp.value = markRaw(components[name])
  router.replace('/' + name)
}
</script>

<style scoped>
.page { padding: 0; }
</style>
