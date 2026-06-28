<template>
  <div class="review-tab">
    <div class="toolbar">
      <el-button type="primary" size="small" @click="showDialog = true">
        <el-icon style="margin-right:4px"><Plus /></el-icon>新建复盘
      </el-button>
    </div>

    <el-empty v-if="!loading && reviews.length === 0" description="暂无复盘记录" />

    <div v-for="r in reviews" :key="r.id" class="review-card">
      <el-card shadow="hover" class="review-item">
        <div class="review-header">
          <div class="review-meta">
            <el-tag :type="reviewTypeTag(r.review_type)" size="small">{{ reviewTypeLabel(r.review_type) }}</el-tag>
            <span class="review-phase" v-if="r.phase_name">{{ r.phase_name }}</span>
            <span class="review-date" v-if="r.review_date">{{ r.review_date }}</span>
            <span class="reviewer" v-if="r.reviewer">复盘人: {{ r.reviewer }}</span>
          </div>
          <div class="review-rating">
            <el-rate v-if="r.overall_rating" :model-value="r.overall_rating" disabled show-score score-template="{value}分" />
          </div>
        </div>

        <el-divider />

        <div class="review-sections">
          <div v-if="r.what_went_well" class="section">
            <div class="section-title" style="color:#67c23a">✅ 做得好</div>
            <div class="section-body">{{ r.what_went_well }}</div>
          </div>
          <div v-if="r.what_could_improve" class="section">
            <div class="section-title" style="color:#e6a23c">🔧 待改进</div>
            <div class="section-body">{{ r.what_could_improve }}</div>
          </div>
          <div v-if="r.key_lessons" class="section">
            <div class="section-title" style="color:#409eff">📖 经验教训</div>
            <div class="section-body">{{ r.key_lessons }}</div>
          </div>
        </div>

        <div class="review-actions">
          <el-tag v-if="r.is_shared" size="small" type="success">已共享到知识库</el-tag>
          <el-button text size="small" type="primary" @click="editReview(r)">编辑</el-button>
          <el-popconfirm title="确定删除?" @confirm="deleteReview(r.id)">
            <template #reference>
              <el-button text size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </el-card>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="showDialog" :title="editing ? '编辑复盘' : '新建复盘'" width="650px" destroy-on-close>
      <el-form label-position="top" size="small">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="复盘类型">
              <el-select v-model="form.review_type">
                <el-option label="结项复盘" value="final" />
                <el-option label="阶段复盘" value="phase" />
                <el-option label="里程碑复盘" value="milestone" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="复盘人">
              <el-input v-model="form.reviewer" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="复盘日期">
              <el-date-picker v-model="form.review_date" type="date" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="阶段名称" v-if="form.review_type === 'phase'">
          <el-input v-model="form.phase_name" placeholder="如：样机阶段复盘" />
        </el-form-item>
        <el-form-item label="总体评分">
          <el-rate v-model="form.overall_rating" show-score score-template="{value}分" />
        </el-form-item>
        <el-form-item label="✅ 做得好（亮点）">
          <el-input v-model="form.what_went_well" type="textarea" :rows="3" placeholder="项目中有哪些成功的做法？" />
        </el-form-item>
        <el-form-item label="🔧 待改进（不足）">
          <el-input v-model="form.what_could_improve" type="textarea" :rows="3" placeholder="哪些地方可以做得更好？" />
        </el-form-item>
        <el-form-item label="📖 关键经验教训">
          <el-input v-model="form.key_lessons" type="textarea" :rows="3" placeholder="从中总结出什么经验？" />
        </el-form-item>
        <el-form-item label="改进措施（JSON）">
          <el-input v-model="form.action_items" type="textarea" :rows="2" placeholder='[{"action":"加强前期评审","owner":"张三","deadline":"2026-08-01"}]' />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="form.is_shared">共享到知识库</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveReview">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../../api'

const props = defineProps<{ pid: number }>()

const loading = ref(false)
const reviews = ref<any[]>([])
const showDialog = ref(false)
const editing = ref(false)
const form = ref<any>({
  review_type: 'final', phase_name: '',
  what_went_well: '', what_could_improve: '',
  key_lessons: '', action_items: '',
  overall_rating: null, reviewer: '',
  review_date: null, is_shared: true,
})

function reviewTypeTag(t: string) {
  return { final: 'success', phase: 'primary', milestone: 'warning' }[t] || 'info'
}
function reviewTypeLabel(t: string) {
  return { final: '结项复盘', phase: '阶段复盘', milestone: '里程碑复盘' }[t] || t
}

async function fetchReviews() {
  loading.value = true
  try {
    const r = await api.get(`/projects/${props.pid}/reviews`)
    reviews.value = r.data || []
  } catch (e: unknown) {
    ElMessage.error('加载复盘记录失败')
  } finally {
    loading.value = false
  }
}

function editReview(r: any) {
  form.value = { ...r }
  editing.value = true
  showDialog.value = true
}

async function saveReview() {
  try {
    if (editing.value) {
      await api.put(`/projects/${props.pid}/reviews/${form.value.id}`, form.value)
      ElMessage.success('已更新')
    } else {
      await api.post(`/projects/${props.pid}/reviews`, form.value)
      ElMessage.success('已创建')
    }
    showDialog.value = false
    editing.value = false
    form.value = { review_type: 'final', phase_name: '', what_went_well: '', what_could_improve: '', key_lessons: '', action_items: '', overall_rating: null, reviewer: '', review_date: null, is_shared: true }
    await fetchReviews()
  } catch (e: unknown) {
    ElMessage.error('保存失败')
  }
}

async function deleteReview(id: number) {
  try {
    await api.delete(`/projects/${props.pid}/reviews/${id}`)
    ElMessage.success('已删除')
    await fetchReviews()
  } catch (e: unknown) {
    ElMessage.error('删除失败')
  }
}

onMounted(fetchReviews)
</script>

<style scoped>
.review-tab { padding: 4px 0; }
.toolbar { margin-bottom: 16px; }
.review-card { margin-bottom: 12px; }
.review-header { display: flex; justify-content: space-between; align-items: center; }
.review-meta { display: flex; align-items: center; gap: 12px; font-size: 13px; color: #909399; }
.review-sections { display: flex; flex-direction: column; gap: 12px; }
.section-title { font-weight: 600; margin-bottom: 4px; }
.section-body { white-space: pre-wrap; line-height: 1.6; color: #303133; }
.review-actions { display: flex; align-items: center; gap: 8px; margin-top: 12px; }
</style>
