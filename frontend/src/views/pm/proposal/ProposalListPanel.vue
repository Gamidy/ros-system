<template>
  <div class="proposals-section" v-if="proposals.length > 0">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>📝 我的提案</span>
          <div class="proposals-filter">
            <el-radio-group :model-value="filter" size="small" @change="$emit('update:filter', $event)">
              <el-radio-button value="all">全部 ({{ counts.all }})</el-radio-button>
              <el-radio-button value="draft">草稿 ({{ counts.draft }})</el-radio-button>
              <el-radio-button value="submitted">已提交 ({{ counts.submitted }})</el-radio-button>
            </el-radio-group>
          </div>
        </div>
      </template>
      <div class="proposals-list">
        <div
          v-for="prop in proposals"
          :key="prop.id"
          class="proposal-item"
          @click="$emit('open', prop)"
        >
          <div class="proposal-item-left">
            <span class="proposal-name">{{ prop.name }}</span>
            <span class="proposal-date">{{ fmtDate(prop.updated_at || prop.created_at) }}</span>
          </div>
          <div class="proposal-item-right">
            <el-tag v-if="prop.is_draft" type="warning" size="small">草稿</el-tag>
            <el-tag v-else-if="prop.approval_status" :type="tagType(prop.approval_status)" size="small">
              {{ tagLabel(prop.approval_status) }}
            </el-tag>
            <el-tag :type="stTagType(prop.status)" size="small">{{ stLabel(prop.status) }}</el-tag>
            <el-button
              v-if="!prop.is_draft && prop.approval_status === 'pending'"
              type="warning" size="small" link style="margin-left:8px"
              @click.stop="$emit('withdraw', prop)"
            >↩️ 撤销</el-button>
          </div>
        </div>
      </div>
      <div v-if="proposals.length === 0" class="empty-state">
        <el-empty description="暂无提案" :image-size="40" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  proposals: any[]
  filter: string
  counts: { all: number; draft: number; submitted: number }
}>()
defineEmits<{
  'update:filter': [value: string]
  open: [proposal: any]
  withdraw: [proposal: any]
}>()

function fmtDate(d: string | null | undefined): string {
  if (!d) return '-'
  const dt = new Date(d)
  if (isNaN(dt.getTime())) return d
  return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`
}
const tagType = (s: string) => ({ pending: 'warning', approved: 'success', rejected: 'danger' } as Record<string, string>)[s] || 'info'
const tagLabel = (s: string) => ({ pending: '审批中', approved: '已通过', rejected: '已驳回' } as Record<string, string>)[s] || s
const stTagType = (s: string) => ({ planning: 'info', running: 'primary', completed: 'success', overdue: 'danger' } as Record<string, string>)[s] || 'info'
const stLabel = (s: string) => ({ planning: '规划', running: '进行中', completed: '已完成', overdue: '超期' } as Record<string, string>)[s] || s
</script>
