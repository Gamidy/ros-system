<template>
  <div class="tpl-page">
    <div class="page-header">
      <span class="page-title">📝 项目模板</span>
      <el-button type="primary" size="small" @click="showCreate = true">新建模板</el-button>
    </div>

    <div class="tpl-grid">
      <el-card v-for="t in templates" :key="t.id" shadow="hover" class="tpl-card">
        <div class="tpl-name">{{ t.name }}</div>
        <div class="tpl-class">
          <el-tag :type="classTag(t.project_class)" size="small">{{ t.project_class }}级</el-tag>
        </div>
        <div class="tpl-desc" v-if="t.description">{{ t.description }}</div>
        <div class="tpl-stats" v-if="t.template_data">
          <span>Gate {{ t.template_data.gates?.length || 0 }}个</span>
          <span>任务 {{ t.template_data.tasks?.length || 0 }}个</span>
          <span>里程碑 {{ t.template_data.milestones?.length || 0 }}个</span>
        </div>
        <div class="tpl-actions">
          <el-button size="small" @click="openApply(t)">快速立项</el-button>
          <el-button size="small" type="danger" text @click="deleteTpl(t)">删除</el-button>
        </div>
      </el-card>
      <el-empty v-if="templates.length === 0" description="暂无模板" />
    </div>

    <!-- Create Dialog -->
    <el-dialog v-model="showCreate" title="新建模板" width="500" destroy-on-close>
      <el-form label-width="100" size="small">
        <el-form-item label="模板名称"><el-input v-model="form.name" placeholder="如：新品开发T级" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="默认等级">
          <el-select v-model="form.project_class">
            <el-option label="T级(战略)" value="T" /><el-option label="A级(重要)" value="A" />
            <el-option label="B级(常规)" value="B" /><el-option label="C级(简化)" value="C" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源项目">
          <el-select v-model="form.source_project_id" filterable clearable placeholder="可选：从项目提取">
            <el-option v-for="p in allProjects" :key="p.id" :label="p.code + ' ' + p.name" :value="p.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="saveTpl">保存</el-button>
      </template>
    </el-dialog>

    <!-- Apply Dialog -->
    <el-dialog v-model="showApply" title="快速立项" width="450" destroy-on-close>
      <el-form label-width="100" size="small">
        <el-form-item label="项目名称"><el-input v-model="applyForm.name" placeholder="输入项目名称" /></el-form-item>
        <el-form-item label="负责人"><el-input v-model="applyForm.owner" placeholder="项目经理" /></el-form-item>
        <el-form-item label="开始日期"><el-date-picker v-model="applyForm.start_date" type="date" /></el-form-item>
        <el-form-item label="截止日期"><el-date-picker v-model="applyForm.target_end_date" type="date" /></el-form-item>
      </el-form>
      <div class="apply-summary">将创建 <b>{{ currentTpl?.project_class }}级</b> 项目，包含
        {{ currentTpl?.template_data?.gates?.length || 0 }}个Gate、
        {{ currentTpl?.template_data?.tasks?.length || 0 }}个任务、
        {{ currentTpl?.template_data?.milestones?.length || 0 }}个里程碑</div>
      <template #footer>
        <el-button @click="showApply = false">取消</el-button>
        <el-button type="primary" @click="confirmApply">确认创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

interface TemplateData {
  gates?: any[]; tasks?: any[]; milestones?: any[]
}
interface Template {
  id: number; name: string; description?: string
  project_class: string; template_data?: TemplateData
}

const templates = ref<Template[]>([])
const allProjects = ref<any[]>([])
const showCreate = ref(false)
const showApply = ref(false)
const currentTpl = ref<Template | null>(null)
const form = ref({ name: '', description: '', project_class: 'C', source_project_id: null })
const applyForm = ref({ name: '', owner: '', start_date: null, target_end_date: null })

function classTag(c: string): string { return { T: 'danger', A: 'warning', B: 'success', C: 'info' }[c] || 'info' }

async function fetchAll() {
  const [tplRes, projRes] = await Promise.all([
    api.get('/project-templates').catch(() => ({ data: [] })),
    api.get('/projects', { params: { limit: 200 } }).catch(() => ({ data: [] })),
  ])
  templates.value = tplRes.data || []
  allProjects.value = projRes.data || []
}

async function saveTpl() {
  if (!form.value.name) { ElMessage.warning('请输入模板名称'); return }
  try {
    await api.post('/project-templates', null, { params: form.value })
    ElMessage.success('模板创建成功')
    showCreate.value = false
    form.value = { name: '', description: '', project_class: 'C', source_project_id: null }
    await fetchAll()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '创建失败') }
}

function openApply(t: Template) {
  currentTpl.value = t
  applyForm.value = { name: '', owner: '', start_date: null, target_end_date: null }
  showApply.value = true
}

async function confirmApply() {
  if (!applyForm.value.name) { ElMessage.warning('请输入项目名称'); return }
  try {
    const res = await api.post(`/project-templates/${currentTpl.value!.id}/apply`, null, { params: applyForm.value })
    ElMessage.success(`项目「${res.data.name}」创建成功！`)
    showApply.value = false
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '创建失败') }
}

async function deleteTpl(t: Template) {
  try { await api.delete(`/project-templates/${t.id}`); ElMessage.success('已删除'); await fetchAll() }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '删除失败') }
}

onMounted(fetchAll)
</script>

<style scoped>
.tpl-page { padding: 16px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-title { font-size: 20px; font-weight: 700; color: #303133; }
.tpl-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.tpl-card { transition: transform 0.15s; }
.tpl-card:hover { transform: translateY(-2px); }
.tpl-name { font-size: 16px; font-weight: 700; color: #303133; margin-bottom: 4px; }
.tpl-class { margin-bottom: 6px; }
.tpl-desc { font-size: 12px; color: #909399; margin-bottom: 8px; }
.tpl-stats { display: flex; gap: 12px; font-size: 11px; color: #909399; margin-bottom: 8px; }
.tpl-actions { display: flex; gap: 8px; }
.apply-summary { font-size: 13px; color: #606266; padding: 8px 12px; background: #f5f7fa; border-radius: 6px; }
</style>
