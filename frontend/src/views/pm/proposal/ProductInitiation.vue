<template>
  <el-card shadow="never" class="col-card">
    <template #header>
      <div class="card-header"><span>📝 产品立项</span></div>
    </template>
    <div class="initiation-intro">
      <p>新建产品立项申请，填写以下四个模块信息：</p>
      <ul>
        <li>📋 <strong>项目概述与市场</strong> — 基本信息、背景目标、市场分析、交付物</li>
        <li>⚙️ <strong>技术要求</strong> — 核心性能参数、安全合规、配件功能选配</li>
        <li>💰 <strong>成本核算</strong> — 开发费用、经济指标、模具/样机/人工/测试费用</li>
        <li>👥 <strong>团队与职责</strong> — 14角色团队选择、职责分工</li>
      </ul>
    </div>
    <el-button type="primary" size="large" style="width:100%;margin-top:16px" @click="$emit('open')">
      📝 产品立项
    </el-button>
    <div v-if="draftId" class="draft-hint">
      <el-tag type="warning" effect="dark">草稿</el-tag>
      <span>点击按钮继续编辑草稿</span>
    </div>
  </el-card>
</template>

<script setup lang="ts">
defineProps<{ draftId: number | null }>()
defineEmits<{ open: [] }>()
</script>
