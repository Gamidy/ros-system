<template>
  <div class="standard-detail">
    <el-page-header title="标准详情" @back="$router.push('/standards')" />

    <el-card v-if="item" class="detail-card">
      <template #header>
        <div class="detail-header">
          <span class="std-number">{{ item.std_number }}</span>
          <el-tag :type="item.status === 'active' ? 'success' : 'danger'" size="small" effect="dark">
            {{ item.status === 'active' ? '已生效' :
               item.status === 'superseded' ? '已废止' :
               item.status === 'draft' ? '草案中' : '已撤销' }}
          </el-tag>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="标准编号">{{ item.std_number }}</el-descriptions-item>
        <el-descriptions-item label="发布机构">
          <el-tag size="small">{{ item.region_name || item.region_code }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="分类" :span="2">
          <el-tag v-if="item.category_name" type="info" size="small">{{ item.category_name }}</el-tag>
          <span v-else class="empty-tag">未分类</span>
        </el-descriptions-item>
        <el-descriptions-item label="版本">{{ item.version || '-' }}</el-descriptions-item>
        <el-descriptions-item label="修订信息">{{ item.amendment || '-' }}</el-descriptions-item>
        <el-descriptions-item label="生效日期">{{ item.effective_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="废止日期">{{ item.repeal_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="影响等级">
          <el-tag
            :type="item.impact_level === 'critical' ? 'danger' :
              item.impact_level === 'high' ? 'warning' : 'info'"
            size="small"
          >
            {{ item.impact_level === 'critical' ? '严重' :
               item.impact_level === 'high' ? '高' :
               item.impact_level === 'medium' ? '中' : '低' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="原文链接">
          <el-link v-if="item.source_url" :href="item.source_url" type="primary" target="_blank">
            查看原文 <el-icon><Link /></el-icon>
          </el-link>
          <span v-else>-</span>
        </el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">标题</el-divider>
      <p class="std-title">{{ item.title }}</p>

      <el-divider v-if="item.impact_scope" content-position="left">影响评估</el-divider>
      <p v-if="item.impact_scope" class="impact-text">{{ item.impact_scope }}</p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Link } from '@element-plus/icons-vue'
import type { StandardItem } from '@/api/standards'
import { getStandard } from '@/api/standards'

const route = useRoute()
const router = useRouter()
const item = ref<StandardItem | null>(null)

onMounted(async () => {
  const id = Number(route.params.id)
  if (!id) { router.push('/standards'); return }
  try {
    item.value = await getStandard(id)
  } catch {
    item.value = null
  }
})
</script>

<style scoped>
.standard-detail { padding: 16px; }
.detail-card { margin-top: 16px; }
.detail-header { display: flex; align-items: center; gap: 12px; }
.std-number { font-size: 18px; font-weight: bold; color: #303133; }
.std-title { font-size: 15px; line-height: 1.6; color: #606266; padding: 0 8px; }
.impact-text { font-size: 14px; line-height: 1.6; color: #e6a23c; padding: 0 8px; }
.empty-tag { color: #c0c4cc; font-size: 13px; }
</style>
