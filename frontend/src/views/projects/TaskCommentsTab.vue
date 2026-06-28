<template>
  <div class="comments-tab">
    <div class="comment-list">
      <div v-for="c in comments" :key="c.id" class="comment-item">
        <div class="comment-header">
          <span class="comment-author">{{ c.author || '匿名' }}</span>
          <span class="comment-time">{{ c.created_at }}</span>
        </div>
        <div class="comment-content">{{ c.content }}</div>
      </div>
      <el-empty v-if="comments.length === 0" description="暂无评论" />
    </div>
    <div class="comment-input">
      <el-input v-model="newComment" type="textarea" :rows="2" placeholder="输入评论..." />
      <el-button type="primary" size="small" style="margin-top:8px" @click="post">发送</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const props = defineProps<{ pid: number; taskId: number }>()
const comments = ref<any[]>([])
const newComment = ref('')

async function fetchComments() {
  try {
    const res = await api.get(`/projects/${props.pid}/tasks/${props.taskId}/comments`)
    comments.value = res.data || []
  } catch { comments.value = [] }
}

async function post() {
  if (!newComment.value.trim()) return
  try {
    await api.post(`/projects/${props.pid}/tasks/${props.taskId}/comments`, null, { params: { content: newComment.value } })
    newComment.value = ''
    await fetchComments()
  } catch { ElMessage.error('发表失败') }
}

onMounted(fetchComments)
</script>

<style scoped>
.comments-tab { width: 100%; }
.comment-list { margin-bottom: 12px; max-height: 400px; overflow-y: auto; }
.comment-item { padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
.comment-header { display: flex; gap: 12px; margin-bottom: 4px; }
.comment-author { font-weight: 600; font-size: 12px; color: #409eff; }
.comment-time { font-size: 11px; color: #c0c4cc; }
.comment-content { font-size: 13px; color: #303133; line-height: 1.5; white-space: pre-wrap; }
.comment-input { border-top: 1px solid #ebeef5; padding-top: 12px; }
</style>
