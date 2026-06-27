<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>质量问题管理</span>
          <el-button type="primary" @click="openDialog()">新建问题</el-button>
        </div>
      </template>

      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="6">
          <el-select v-model="filterStatus" placeholder="状态筛选" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="未处理" value="open" />
            <el-option label="分析中" value="analyzing" />
            <el-option label="修复中" value="fixing" />
            <el-option label="已验证" value="verified" />
            <el-option label="已关闭" value="closed" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filterSeverity" placeholder="严重度" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="A级-致命" value="A" />
            <el-option label="B级-严重" value="B" />
            <el-option label="C级-轻微" value="C" />
          </el-select>
        </el-col>
      </el-row>

      <el-table :data="items" stripe border max-height="500" v-loading="loading">
        <el-table-column prop="issue_no" label="问题编号" width="140" />
        <el-table-column prop="title" label="问题标题" min-width="200" />
        <el-table-column prop="product_code" label="产品编码" width="120" />
        <el-table-column prop="project_code" label="整改项目" width="120" />
        <el-table-column prop="issue_source" label="来源" width="90" />
        <el-table-column prop="severity" label="严重度" width="80">
          <template #default="{ row }">
            <el-tag :type="severityType(row.severity)" size="small">{{ row.severity }}级</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="类别" width="90" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="assigned_to" label="负责人" width="90" />
        <el-table-column prop="target_date" label="目标日期" width="110" />
        <el-table-column prop="closed_date" label="关闭日期" width="110" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">处理</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '处理问题' : '新建问题'" width="600">
      <el-form :model="form" label-width="100">
        <el-form-item label="问题标题" required>
          <el-input v-model="form.title" placeholder="简要描述问题" />
        </el-form-item>
        <el-form-item label="产品编码">
          <el-input v-model="form.product_code" placeholder="关联产品" />
        </el-form-item>
        <el-form-item label="整改项目">
          <el-input v-model="form.project_code" placeholder="关联整改项目编码" />
        </el-form-item>
        <el-form-item label="问题来源">
          <el-select v-model="form.issue_source" style="width: 100%" clearable>
            <el-option label="客诉" value="客诉" />
            <el-option label="产线" value="产线" />
            <el-option label="测试" value="测试" />
            <el-option label="审核" value="审核" />
          </el-select>
        </el-form-item>
        <el-form-item label="严重度">
          <el-radio-group v-model="form.severity">
            <el-radio-button value="A">A级·致命</el-radio-button>
            <el-radio-button value="B">B级·严重</el-radio-button>
            <el-radio-button value="C">C级·轻微</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="类别">
          <el-select v-model="form.category" style="width: 100%" clearable>
            <el-option label="结构" value="结构" />
            <el-option label="系统" value="系统" />
            <el-option label="电控" value="电控" />
            <el-option label="工艺" value="工艺" />
            <el-option label="物料" value="物料" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="form.assigned_to" />
        </el-form-item>
        <el-form-item label="目标日期">
          <el-date-picker v-model="form.target_date" type="date" style="width: 100%" />
        </el-form-item>
        <template v-if="editingId">
          <el-form-item label="状态">
            <el-select v-model="form.status" style="width: 100%">
              <el-option label="未处理" value="open" />
              <el-option label="分析中" value="analyzing" />
              <el-option label="修复中" value="fixing" />
              <el-option label="已验证" value="verified" />
              <el-option label="已关闭" value="closed" />
            </el-select>
          </el-form-item>
          <el-form-item label="根本原因">
            <el-input v-model="form.root_cause" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="解决方案">
            <el-input v-model="form.solution" type="textarea" :rows="2" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const items = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const filterStatus = ref('')
const filterSeverity = ref('')

const form = ref<any>({
  title: '', product_code: '', project_code: '',
  issue_source: '', severity: 'B', category: '',
  assigned_to: '', target_date: null, status: '',
  root_cause: '', solution: ''
})

const statusMap: Record<string, string> = {
  open: '未处理', analyzing: '分析中', fixing: '修复中',
  verified: '已验证', closed: '已关闭'
}
const statusTypeMap: Record<string, string> = {
  open: 'danger', analyzing: 'warning', fixing: 'warning',
  verified: '', closed: 'success'
}
const severityTypeMap: Record<string, string> = { A: 'danger', B: 'warning', C: 'info' }

function statusLabel(s: string) { return statusMap[s] || s }
function statusType(s: string) { return statusTypeMap[s] || 'info' as any }
function severityType(s: string) { return severityTypeMap[s] || 'info' as any }

async function fetchData() {
  loading.value = true
  try {
    let url = '/certifications/quality-issues'
    const params: string[] = []
    if (filterStatus.value) params.push(`status=${filterStatus.value}`)
    if (filterSeverity.value) params.push(`severity=${filterSeverity.value}`)
    if (params.length) url += '?' + params.join('&')
    const r = await api.get(url)
    items.value = r.data
  } finally { loading.value = false }
}

function openDialog(row?: Record<string, unknown>) {
  if (row) {
    editingId.value = row.id
    form.value = { ...row }
  } else {
    editingId.value = null
    form.value = { title: '', product_code: '', project_code: '', issue_source: '', severity: 'B', category: '', assigned_to: '', target_date: null, status: '', root_cause: '', solution: '' }
  }
  dialogVisible.value = true
}

async function save() {
  saving.value = true
  try {
    const payload: Record<string, unknown> = { ...form.value }
    if (editingId.value) {
      await api.patch(`/certifications/quality-issues/${editingId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      delete payload.status; delete payload.root_cause; delete payload.solution
      await api.post('/certifications/quality-issues', payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally { saving.value = false }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
