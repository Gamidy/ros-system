<template>
  <div class="page">
    <!-- Deprecation 警告 Banner -->
    <el-alert
      title="⚠️ 此页面已废弃 — 请使用 ECR / ECO 独立入口"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 12px;"
    >
      <template #default>
        <span>
          Board 裁决: <code>ChangesView.vue</code> 已废弃，请使用
          <router-link to="/ecr" style="font-weight:bold;color:var(--el-color-primary)">ECR 变更申请</router-link>
          /
          <router-link to="/eco" style="font-weight:bold;color:var(--el-color-primary)">ECO 变更指令</router-link>
          独立入口
        </span>
      </template>
    </el-alert>

    <el-card shadow="never">
      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <el-tab-pane label="原变更管理 (已废弃)" name="changes" :disabled="true" />
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

// 从URL初始化tab（默认指向 ecr，废弃 changes）
const tabFromPath: Record<string, string> = {
  '/changes': 'ecr',  // 废弃，自动跳转 ecr
  '/ecr': 'ecr',
  '/eco': 'eco',
}
const activeTab = ref(tabFromPath[route.path] || 'ecr')

const currentComp = shallowRef(markRaw(components[activeTab.value]))

function onTabChange(name: string) {
  currentComp.value = markRaw(components[name])
  router.replace('/' + name)
}
</script>

<style scoped>
.page { padding: 0; }
</style>
