<template>
  <div class="tech-spec-tab">
    <!-- 四步引导条 -->
    <el-steps :active="step" align-center style="margin-bottom:24px">
      <el-step title="性能指标" description="核心性能参数" />
      <el-step title="安全合规" description="安规与认证要求" />
      <el-step title="物料部件" description="物料与部件清单" />
      <el-step title="附件/功能" description="附件与功能配置" />
    </el-steps>

    <!-- Step 1: 性能指标 -->
    <div v-show="step === 0" class="step-content">
      <PerfStep :data="data" @update="handleStepUpdate" />
    </div>

    <!-- Step 2: 安全合规 -->
    <div v-show="step === 1" class="step-content">
      <SafetyStep :data="data" @update="handleStepUpdate" />
    </div>

    <!-- Step 3: 物料部件 -->
    <div v-show="step === 2" class="step-content">
      <MaterialStep :data="data" @update="handleStepUpdate" />
    </div>

    <!-- Step 4: 附件/功能 -->
    <div v-show="step === 3" class="step-content">
      <FeatureStep :data="data" @update="handleStepUpdate" />
    </div>

    <!-- 步骤导航按钮 -->
    <div class="step-nav">
      <el-button v-if="step > 0" @click="step--">← 上一步</el-button>
      <el-button v-if="step < 3" type="primary" @click="step++">下一步 →</el-button>
      <el-tag v-if="step === 3" type="success" size="large" effect="dark" style="font-size:14px">
        ✅ 四项信息填写完成
      </el-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import PerfStep from './PerfStep.vue'
import SafetyStep from './SafetyStep.vue'
import MaterialStep from './MaterialStep.vue'
import FeatureStep from './FeatureStep.vue'

const props = defineProps({
  data: { type: Object, required: true },
})
const emit = defineEmits<{ update: [patch: Record<string, unknown>] }>()

const step = ref(0)

function handleStepUpdate(patch: Record<string, unknown>) {
  emit('update', patch)
}
</script>

<style scoped>
.tech-spec-tab {
  padding: 8px 0;
}
.step-content {
  min-height: 300px;
}
.step-nav {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}
</style>
