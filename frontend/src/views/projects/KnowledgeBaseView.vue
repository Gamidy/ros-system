<template>
  <div class="knowledge-page">
    <div class="page-header">
      <h2>📚 项目知识库</h2>
      <div class="header-actions">
        <el-select v-model="filterType" placeholder="复盘类型" clearable size="small" style="width:140px" @change="fetchLessons">
          <el-option label="结项复盘" value="final" />
          <el-option label="阶段复盘" value="phase" />
          <el-option label="里程碑复盘" value="milestone" />
        </el-select>
        <el-input v-model="searchKeyword" placeholder="搜索经验教训..." size="small" style="width:240px" clearable @keyup.enter="fetchLessons" />
        <el-button size="small" type="primary" @click="fetchLessons">搜索</el-button>
      </div>
    </div>

    <el-skeleton :loading="loading" animated :count="3">
      <template #default>
        <div v-if="lessons.length === 0 && !loading" class="empty-state">
          <el-empty description="知识库暂无内容 — 在项目详情页创建复盘并勾选'共享到知识库'" />
        </div>

        <div v-for="l in lessons" :key="l.id" class="lesson-card">
          <el-card shadow="hover">
            <div class="lesson-header">
              <div class="lesson-meta">
                <el-tag :type="typeTag(l.review_type)" size="small">{{ typeLabel(l.review_type) }}</el-tag>
                <span class="lesson-project">{{ l.project_code }} {{ l.project_name }}</span>
                <span class="lesson-phase" v-if="l.phase_name">{{ l.phase_name }}</span>
              </div>
              <div class="lesson-info">
                <span v-if="l.reviewer" class="lesson-reviewer">{{ l.reviewer }}</span>
                <span v-if="l.review_date" class="lesson-date">{{ l.review_date }}</span>
                <el-rate v-if="l.overall_rating" :model-value="l.overall_rating" disabled size="small" show-score score-template="{value}" />
              </div>
            </div>

            <div class="lesson-body">
              <div v-if="l.what_went_well" class="lesson-section">
                <div class="section-label" style="color:#67c23a">✅ 做得好</div>
                <div class="section-text">{{ l.what_went_well }}</div>
              </div>
              <div v-if="l.what_could_improve" class="lesson-section">
                <div class="section-label" style="color:#e6a23c">🔧 待改进</div>
                <div class="section-text">{{ l.what_could_improve }}</div>
              </div>
              <div v-if="l.key_lessons" class="lesson-section">
                <div class="section-label" style="color:#409eff">📖 经验教训</div>
                <div class="section-text">{{ l.key_lessons }}</div>
              </div>
            </div>

            <div class="lesson-footer">
              <el-button text size="small" type="primary" @click="$router.push('/projects/' + l.project_id)">查看项目 →</el-button>
            </div>
          </el-card>
        </div>
      </template>
    </el-skeleton>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const loading = ref(false)
const lessons = ref<any[]>([])
const filterType = ref('')
const searchKeyword = ref('')

function typeTag(t: string) {
  return { final: 'success', phase: 'primary', milestone: 'warning' }[t] || 'info'
}
function typeLabel(t: string) {
  return { final: '结项复盘', phase: '阶段复盘', milestone: '里程碑复盘' }[t] || t
}

async function fetchLessons() {
  loading.value = true
  try {
    const params: any = { limit: 50 }
    if (filterType.value) params.review_type = filterType.value
    if (searchKeyword.value) params.keyword = searchKeyword.value
    const r = await api.get('/knowledge-base/lessons', { params })
    lessons.value = r.data || []
  } catch (e: unknown) {
    ElMessage.error('加载知识库失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchLessons)
</script>

<style scoped>
.knowledge-page { padding: 16px 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
.header-actions { display: flex; gap: 8px; }
.lesson-card { margin-bottom: 12px; }
.lesson-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
.lesson-meta { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.lesson-project { font-weight: 600; color: #303133; }
.lesson-phase { color: #909399; font-style: italic; }
.lesson-info { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #909399; }
.lesson-body { display: flex; flex-direction: column; gap: 8px; }
.lesson-section { }
.section-label { font-weight: 600; margin-bottom: 4px; font-size: 13px; }
.section-text { white-space: pre-wrap; line-height: 1.6; color: #303133; font-size: 13px; }
.lesson-footer { margin-top: 8px; text-align: right; }
.empty-state { min-height: 300px; display: flex; align-items: center; justify-content: center; }
</style>
