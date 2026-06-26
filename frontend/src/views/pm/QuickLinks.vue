<template>
  <div class="quick-links">
    <el-card shadow="never" class="quick-link-card" @click="goTo('/competitor-bench')">
      <div class="quick-link-icon">📊</div>
      <div class="quick-link-info">
        <div class="quick-link-title">竞品对标</div>
        <div class="quick-link-desc">查看各品牌竞品参数与性能对比</div>
      </div>
      <el-icon class="quick-link-arrow"><ArrowRight /></el-icon>
    </el-card>
    <el-card shadow="never" class="quick-link-card" @click="goTo('/market-mgmt')">
      <div class="quick-link-icon">🏛️</div>
      <div class="quick-link-info">
        <div class="quick-link-title">市场管理</div>
        <div class="quick-link-desc">各国认证标准、能效要求、压缩机信息</div>
      </div>
      <el-icon class="quick-link-arrow"><ArrowRight /></el-icon>
    </el-card>
    <el-card shadow="never" class="quick-link-card" @click="goTo('/proposals')">
      <div class="quick-link-icon">📝</div>
      <div class="quick-link-info">
        <div class="quick-link-title">提案管理</div>
        <div class="quick-link-desc">查看和管理所有产品立项提案</div>
      </div>
      <el-icon class="quick-link-arrow"><ArrowRight /></el-icon>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()

function goTo(path: string) {
  router.push(path)
}
</script>

<style scoped>
.quick-links {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}
.quick-link-card {
  flex: 1;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid #e4e7ed;
}
.quick-link-card:hover {
  border-color: #409eff;
  background: #f0f6ff;
  transform: translateY(-1px);
}
.quick-link-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  padding: 16px 20px;
}
.quick-link-icon {
  font-size: 28px;
  margin-right: 16px;
  flex-shrink: 0;
}
.quick-link-info {
  flex: 1;
  min-width: 0;
}
.quick-link-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}
.quick-link-desc {
  font-size: 12px;
  color: #909399;
}
.quick-link-arrow {
  font-size: 16px;
  color: #c0c4cc;
  flex-shrink: 0;
  margin-left: 12px;
}
</style>
