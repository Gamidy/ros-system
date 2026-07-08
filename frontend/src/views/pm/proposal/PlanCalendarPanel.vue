<template>
  <el-card shadow="never" class="col-card">
    <template #header>
      <div class="card-header">
        <span>📋 年度产品规划</span>
        <el-button type="primary" size="small" @click="$emit('new-plan')">新建规划项</el-button>
      </div>
    </template>
    <el-input :model-value="planRef" @update:model-value="emit('update:planRef', $event)" :prefix-icon="Link" placeholder="规划文档引用链接" size="small" class="plan-ref-input" />
    <div v-if="items.length === 0" class="empty-state">
      <el-empty description="暂无年度规划项" :image-size="60" />
    </div>
    <div
      v-for="item in items" :key="item.id"
      class="plan-item" :class="{ 'plan-item--active': selectedId === item.id }"
      @click="$emit('select', item)"
    >
      <div class="plan-item-name">{{ item.name }}</div>
      <div class="plan-item-meta">
        <el-tag size="small" type="warning">{{ item.year }}</el-tag>
        <span class="plan-item-desc">{{ item.description || '暂无描述' }}</span>
      </div>
      <div class="plan-item-count" v-if="item.project_count !== undefined">
        关联项目: {{ item.project_count }} 个
      </div>
      <div class="plan-item-actions">
        <el-button link circle :icon="Edit" size="small" @click.stop="$emit('edit', item)" title="编辑" />
        <el-button link circle :icon="Delete" size="small" @click.stop="$emit('delete', item)" title="删除" />
      </div>
    </div>
    <div v-if="linkedProjects.length > 0" class="linked-projects">
      <div class="linked-title">关联项目</div>
      <div v-for="proj in linkedProjects" :key="proj.id" class="linked-item">
        <span>{{ proj.name }}</span>
        <div class="linked-item-tags">
          <el-tag v-if="proj.approval_status" :type="tagType(proj.approval_status)" size="small">{{ tagLabel(proj.approval_status) }}</el-tag>
          <el-tag :type="stTagType(proj.status)" size="small">{{ stLabel(proj.status) }}</el-tag>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { Edit, Delete, Link } from '@element-plus/icons-vue'

const props = defineProps<{
  items: any[]
  selectedId: number | null
  linkedProjects: any[]
  planRef: string
}>()
const emit = defineEmits<{
  'update:planRef': [value: string]
  'new-plan': []
  select: [item: any]
  edit: [item: any]
  delete: [item: any]
}>()

const tagType = (s: string) => ({ pending: 'warning', approved: 'success', rejected: 'danger' } as Record<string, string>)[s] || 'info'
const tagLabel = (s: string) => ({ pending: '审批中', approved: '已通过', rejected: '已驳回' } as Record<string, string>)[s] || s
const stTagType = (s: string) => ({ planning: 'info', running: 'primary', completed: 'success', overdue: 'danger' } as Record<string, string>)[s] || 'info'
const stLabel = (s: string) => ({ planning: '规划', running: '进行中', completed: '已完成', overdue: '超期' } as Record<string, string>)[s] || s
</script>
