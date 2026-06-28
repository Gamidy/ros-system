<template>
  <div>
    <div class="toolbar" style="margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <el-input v-model="searchKeyword" placeholder="搜索检测项编码/名称" clearable style="width:240px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-select v-model="filterCategory" placeholder="检测类别" clearable style="width:130px" @change="fetchData">
        <el-option label="电气安全" value="electrical" />
        <el-option label="机械安全" value="mechanical" />
        <el-option label="防火" value="fire" />
        <el-option label="EMC" value="emc" />
        <el-option label="化学/环保" value="chemical" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="状态" clearable style="width:80px" @change="fetchData">
        <el-option label="启用" value="active" />
        <el-option label="停用" value="inactive" />
      </el-select>
      <el-button type="primary" @click="showCreate">新建检测项</el-button>
    </div>

    <el-table :data="items" v-loading="loading" style="width:100%" stripe>
      <el-table-column prop="item_code" label="编码" width="120" />
      <el-table-column prop="item_name" label="检测项名称" min-width="200" show-overflow-tooltip />
      <el-table-column prop="standard_code" label="所属标准" width="150" />
      <el-table-column label="检测类别" width="100">
        <template #default="{row}">{{ catLabel(row.inspection_category) }}</template>
      </el-table-column>
      <el-table-column label="标准值" width="160">
        <template #default="{row}">
          <template v-if="row.standard_value_nominal">{{ row.standard_value_nominal }} {{ row.unit }}</template>
          <template v-else-if="row.standard_value_min != null && row.standard_value_max != null">{{ row.standard_value_min }} ~ {{ row.standard_value_max }} {{ row.unit }}</template>
          <template v-else-if="row.standard_value_max != null">≤ {{ row.standard_value_max }} {{ row.unit }}</template>
          <template v-else-if="row.standard_value_min != null">≥ {{ row.standard_value_min }} {{ row.unit }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="reference_clause" label="条款" width="80" />
      <el-table-column label="状态" width="60">
        <template #default="{row}">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status === 'active' ? '启用' : '停用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{row}">
          <el-button link type="primary" size="small" @click="showEdit(row)">编辑</el-button>
          <el-popconfirm title="确定删除?" @confirm="handleDelete(row)">
            <template #reference>
              <el-button link type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <div style="margin-top:12px;text-align:right">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50]" layout="total,sizes,prev,pager,next" @change="fetchData" />
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑安规检测项' : '新建安规检测项'" width="650px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="所属标准" prop="standard_id">
              <el-select v-model="form.standard_id" style="width:100%" filterable placeholder="选择安全标准">
                <el-option v-for="s in standardsList" :key="s.id" :label="s.standard_code + ' - ' + s.standard_name_cn" :value="s.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="检测类别">
              <el-select v-model="form.inspection_category" style="width:100%">
                <el-option label="电气安全" value="electrical" />
                <el-option label="机械安全" value="mechanical" />
                <el-option label="防火" value="fire" />
                <el-option label="EMC" value="emc" />
                <el-option label="化学/环保" value="chemical" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="检测编码" prop="item_code">
              <el-input v-model="form.item_code" placeholder="如 IEC-001" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="检测名称" prop="item_name">
              <el-input v-model="form.item_name" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="参数名称">
              <el-input v-model="form.param_name" placeholder="如 接地电阻值" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="标称值">
              <el-input v-model="form.standard_value_nominal" placeholder="如 220V±10%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="单位">
              <el-input v-model="form.unit" placeholder="如 Ω/mA/mm" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="下限值">
              <el-input-number v-model="form.standard_value_min" style="width:100%" :min="0" :precision="3" placeholder="≥" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="上限值">
              <el-input-number v-model="form.standard_value_max" style="width:100%" :min="0" :precision="3" placeholder="≤" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="排序">
              <el-input-number v-model="form.sort_order" style="width:100%" :min="0" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="检测方法">
          <el-input v-model="form.test_method" type="textarea" :rows="2" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="参考条款">
              <el-input v-model="form.reference_clause" placeholder="如 Clause 27.5" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="适用产品">
              <el-input v-model="form.applicable_product_type" placeholder="如 分体式空调" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listSafetyInspectionItems, createSafetyInspectionItem, updateSafetyInspectionItem, deleteSafetyInspectionItem } from '../../api/safety'
import { listSafetyStandards } from '../../api/safety'
import type { FormInstance } from 'element-plus'
import type { TableRow } from '@/types/common'

const items = ref<TableRow[]>([])
const standardsList = ref<TableRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const searchKeyword = ref('')
const filterCategory = ref('')
const filterStatus = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref<FormInstance>()

const form = ref<Record<string, unknown>>({
  standard_id: null, item_code: '', item_name: '', inspection_category: '',
  param_name: '', standard_value_min: null, standard_value_max: null,
  standard_value_nominal: '', unit: '', applicable_product_type: '',
  test_method: '', reference_clause: '', sort_order: 0, status: 'active',
})

const rules = {
  standard_id: [{ required: true, message: '请选择所属安全标准', trigger: 'change' }],
  item_code: [{ required: true, message: '请输入检测项编码', trigger: 'blur' }],
  item_name: [{ required: true, message: '请输入检测项名称', trigger: 'blur' }],
}

function catLabel(cat: string) {
  const m: Record<string, string> = { electrical: '电气安全', mechanical: '机械安全', fire: '防火', emc: 'EMC', chemical: '化学/环保', other: '其他' }
  return m[cat] || cat
}

async function fetchData() {
  loading.value = true
  try {
    const { data } = await listSafetyInspectionItems({
      page: page.value, page_size: pageSize.value,
      keyword: searchKeyword.value || undefined,
      inspection_category: filterCategory.value || undefined,
      status: filterStatus.value || undefined,
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch { /* */ } finally { loading.value = false }
}

async function loadStandards() {
  try {
    const { data } = await listSafetyStandards({ page: 1, page_size: 200 })
    standardsList.value = data.items || []
  } catch { /* */ }
}

function showCreate() {
  isEdit.value = false
  editingId.value = null
  form.value = {
    standard_id: null, item_code: '', item_name: '', inspection_category: '',
    param_name: '', standard_value_min: null, standard_value_max: null,
    standard_value_nominal: '', unit: '', applicable_product_type: '',
    test_method: '', reference_clause: '', sort_order: 0, status: 'active',
  }
  dialogVisible.value = true
}

function showEdit(row: TableRow) {
  isEdit.value = true
  editingId.value = row.id as number
  form.value = { ...row }
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit.value && editingId.value) {
      await updateSafetyInspectionItem(editingId.value, form.value)
    } else {
      await createSafetyInspectionItem(form.value)
    }
    dialogVisible.value = false
    fetchData()
  } catch { /* */ } finally { saving.value = false }
}

async function handleDelete(row: TableRow) {
  try {
    await deleteSafetyInspectionItem(row.id as number)
    fetchData()
  } catch { /* */ }
}

onMounted(() => { fetchData(); loadStandards() })
</script>
