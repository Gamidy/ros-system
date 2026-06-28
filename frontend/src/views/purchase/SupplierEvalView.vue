<template>
  <div class="supplier-eval-page">
    <div class="page-header">
      <h2>📋 供应商评估</h2>
      <div class="header-actions">
        <el-input v-model="filterSupplier" placeholder="供应商名称" clearable size="small" style="width:160px" @input="fetchData" />
        <el-button size="small" type="primary" @click="openCreate">新建评估</el-button>
      </div>
    </div>

    <el-table :data="list" stripe border size="small" v-loading="loading">
      <el-table-column type="index" label="序号" width="60" />
      <el-table-column prop="supplier_name" label="供应商名称" min-width="130" />
      <el-table-column label="评估周期" width="100">
        <template #default="{ row }">{{ periodLabel(row.eval_period) }}</template>
      </el-table-column>
      <el-table-column prop="eval_date" label="评估日期" width="110" />
      <el-table-column prop="quality_score" label="质量分" width="70" />
      <el-table-column prop="delivery_score" label="交付分" width="70" />
      <el-table-column prop="price_score" label="价格分" width="70" />
      <el-table-column prop="service_score" label="服务分" width="70" />
      <el-table-column prop="total_score" label="综合分" width="80" />
      <el-table-column label="等级" width="75">
        <template #default="{ row }">
          <el-tag :type="gradeTag(row.grade)" size="small">{{ row.grade || '-' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="evaluator" label="评估人" width="90" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button text size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create / Edit Dialog -->
    <el-dialog v-model="showDialog" :title="isEdit ? '编辑评估' : '新建评估'" width="560px" destroy-on-close>
      <el-form label-position="top" size="small">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="供应商名称">
              <el-input v-model="form.supplier_name" placeholder="供应商名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="评估周期">
              <el-select v-model="form.eval_period" placeholder="请选择" style="width:100%">
                <el-option label="月度" value="monthly" />
                <el-option label="季度" value="quarterly" />
                <el-option label="年度" value="yearly" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="评估日期">
              <el-date-picker v-model="form.eval_date" type="date" style="width:100%" placeholder="选择日期" value-format="YYYY-MM-DD" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="评估人">
              <el-input v-model="form.evaluator" placeholder="评估人" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="6">
            <el-form-item label="质量分（0-100）">
              <el-input-number v-model="form.quality_score" :min="0" :max="100" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="交付分（0-100）">
              <el-input-number v-model="form.delivery_score" :min="0" :max="100" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="价格分（0-100）">
              <el-input-number v-model="form.price_score" :min="0" :max="100" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="服务分（0-100）">
              <el-input-number v-model="form.service_score" :min="0" :max="100" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="评估意见">
          <el-input v-model="form.comment" type="textarea" :rows="3" placeholder="评估意见（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog=false">取消</el-button>
        <el-button type="primary" @click="saveEval">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

const loading = ref(false)
const list = ref<any[]>([])
const showDialog = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)
const filterSupplier = ref('')

const form = reactive({
  supplier_name: '',
  eval_period: 'monthly',
  eval_date: '',
  quality_score: 0,
  delivery_score: 0,
  price_score: 0,
  service_score: 0,
  comment: '',
  evaluator: '',
})

function periodLabel(val: string) {
  return { monthly: '月度', quarterly: '季度', yearly: '年度' }[val] || val
}

function gradeTag(grade: string) {
  if (!grade) return 'info'
  if (grade === 'A') return 'success'
  if (grade === 'B') return 'primary'
  if (grade === 'C') return 'warning'
  if (grade === 'D') return 'danger'
  return 'info'
}

function resetForm() {
  form.supplier_name = ''
  form.eval_period = 'monthly'
  form.eval_date = ''
  form.quality_score = 0
  form.delivery_score = 0
  form.price_score = 0
  form.service_score = 0
  form.comment = ''
  form.evaluator = ''
}

async function fetchData() {
  loading.value = true
  try {
    const params: any = {}
    if (filterSupplier.value) params.supplier_name = filterSupplier.value
    const r = await api.get('/purchase/supplier-evaluations', { params })
    list.value = r.data || []
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  editId.value = null
  resetForm()
  showDialog.value = true
}

function openEdit(row: any) {
  isEdit.value = true
  editId.value = row.id
  form.supplier_name = row.supplier_name
  form.eval_period = row.eval_period
  form.eval_date = row.eval_date
  form.quality_score = row.quality_score
  form.delivery_score = row.delivery_score
  form.price_score = row.price_score
  form.service_score = row.service_score
  form.comment = row.comment || ''
  form.evaluator = row.evaluator || ''
  showDialog.value = true
}

async function saveEval() {
  try {
    const payload = {
      supplier_name: form.supplier_name,
      eval_period: form.eval_period,
      eval_date: form.eval_date,
      quality_score: form.quality_score,
      delivery_score: form.delivery_score,
      price_score: form.price_score,
      service_score: form.service_score,
      comment: form.comment,
      evaluator: form.evaluator,
    }
    if (isEdit.value && editId.value) {
      await api.put(`/purchase/supplier-evaluations/${editId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      await api.post('/purchase/supplier-evaluations', payload)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    await fetchData()
  } catch {
    ElMessage.error('保存失败')
  }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.supplier_name}」的评估记录？`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await api.delete(`/purchase/supplier-evaluations/${row.id}`)
    ElMessage.success('删除成功')
    await fetchData()
  } catch {
    // cancelled or error
  }
}

onMounted(fetchData)
</script>

<style scoped>
.supplier-eval-page { padding: 16px 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
.header-actions { display: flex; gap: 8px; }
</style>
